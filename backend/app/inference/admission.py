"""Whether a model task runs now, tonight, or not at all (RF-203, RF-204, rule 17).

The decision has three inputs and no side effects: the alias, the server profile, and whether the
gateway is answering. It is pure so the one property that matters can be asserted directly —
**a person is never blocked by a model**. The acceptance criterion of RF-204 is that with the model
service stopped, a supervisor can still review and approve work orders, with a notice. A policy
buried inside a request path would be a policy nobody could test that way.

What the three answers mean:

* ``INTERACTIVE`` — run it now; somebody may be waiting.
* ``NIGHT_BATCH`` — queue it for the night window. Chosen when the answer is still useful
  tomorrow: a pre-review report read before the shift starts is a report that did its job.
* ``UNAVAILABLE`` — do not run it, and say so. Chosen when a late answer is worthless: a
  dictation proposal that arrives tomorrow morning helps nobody, because the technician typed
  the field and carried on.

`UNAVAILABLE` is never silent. Every caller receives the reason in Spanish and is expected to show
it, because the alternative — an agent report with a section quietly missing — is worse than no
report: it looks complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.inference.registry import (
    Degradation,
    InferenceRegistry,
    ModelAlias,
    load_registry,
)


class Placement(StrEnum):
    INTERACTIVE = "interactive"
    NIGHT_BATCH = "night_batch"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Admission:
    """Where a task goes, and why — in words a supervisor can read."""

    alias: str
    placement: Placement
    #: Always present, including for INTERACTIVE: the reason is what a notice shows, and a
    #: decision whose reason is only in the code is one nobody can question.
    reason: str

    @property
    def runs_now(self) -> bool:
        return self.placement is Placement.INTERACTIVE

    @property
    def blocks_a_person(self) -> bool:
        """Always False, and stated as a property so a test can assert it over every case.

        Rule 17 and RF-204 in one line: whatever this policy decides, human review continues.
        Nothing here returns a placement that means "wait for a model".
        """
        return False


def _degraded(alias: ModelAlias, reason: str, *, supported: bool) -> Admission:
    """Apply the alias's declared degradation for this kind of shortfall (RF-204).

    Two kinds, because the SRS treats them differently: hardware that cannot run the alias at all
    (profile A has no GPU, so the VLM is off) is not the same as hardware that can but is busy
    (profile B runs the VLM at night). One field for both would force the VLM to be either lost on
    B or queued forever on A.
    """
    behaviour = alias.when_busy if supported else alias.when_unsupported
    if behaviour is Degradation.NIGHT_BATCH:
        return Admission(alias.name, Placement.NIGHT_BATCH, f"{reason}; pasa al lote nocturno")
    return Admission(alias.name, Placement.UNAVAILABLE, f"{reason}; se omite con aviso")


def admit(
    alias_name: str,
    profile_name: str,
    *,
    gateway_reachable: bool = True,
    resident: frozenset[str] = frozenset(),
    registry: InferenceRegistry | None = None,
) -> Admission:
    """Decide where one task goes.

    :param resident: aliases already loaded on the GPU. Used for RF-203: in 16 GB the judge and
        the VLM do not coexist, so the second one asked for is queued rather than allowed to
        cause an out-of-memory during a supervisor's working day.
    """
    known = registry or load_registry()
    alias = known.alias(alias_name)
    profile = known.profile(profile_name)

    # The permanent fact decides before the temporary one. On profile A the VLM will never run,
    # gateway or no gateway, so answering "the model service is down; queued for tonight" would
    # promise a supervisor a report that is never coming.
    if not profile.has_gpu and not alias.runs_on_cpu:
        return _degraded(
            alias,
            f"'{alias.name}' necesita GPU y el perfil {profile.name} no tiene",
            supported=False,
        )

    if not gateway_reachable:
        # The whole reason this function is pure: with the model service down, everything degrades
        # and nothing waits on it. Treated as "busy" rather than "unsupported" — the hardware is
        # fine and the work is still worth doing later, which is what a night queue is for.
        return _degraded(alias, "el servicio de modelos no responde", supported=True)

    if alias_name not in profile.interactive_aliases:
        return _degraded(
            alias,
            f"el perfil {profile.name} no ejecuta '{alias.name}' de forma interactiva",
            supported=True,
        )

    if profile.has_gpu:
        headroom = profile.usable_vram_gb - used_vram(resident, known)
        if alias_name not in resident and alias.vram_gb > headroom:
            # RF-203: rather than load it and fail, the task waits. An out-of-memory in working
            # hours takes the interactive path down with it.
            return _degraded(
                alias,
                f"no cabe en la VRAM del perfil {profile.name}: necesita {alias.vram_gb} GB y "
                f"quedan {headroom:.1f} GB con {', '.join(sorted(resident)) or 'nada'} cargado",
                supported=True,
            )

    return Admission(
        alias.name, Placement.INTERACTIVE, f"el perfil {profile.name} lo ejecuta en línea"
    )


def used_vram(resident: frozenset[str], registry: InferenceRegistry | None = None) -> float:
    """VRAM the given aliases occupy together."""
    known = registry or load_registry()
    return sum(known.alias(name).vram_gb for name in resident)


def may_coexist(
    first: str, second: str, profile_name: str, registry: InferenceRegistry | None = None
) -> bool:
    """Whether two aliases fit in a profile's VRAM at the same time (RF-203).

    The question the 16 GB profile exists to answer: the judge and the VLM together are 15.5 GB of
    a 16 GB card, which leaves nothing for context or activations. Declaring the numbers and doing
    the arithmetic beats a hand-kept list of forbidden pairs, which would go stale the first time
    a model is swapped behind its alias.
    """
    known = registry or load_registry()
    profile = known.profile(profile_name)
    if not profile.has_gpu:
        return False
    return used_vram(frozenset({first, second}), known) <= profile.usable_vram_gb


def fits_alone(
    alias_name: str, profile_name: str, registry: InferenceRegistry | None = None
) -> bool:
    known = registry or load_registry()
    profile = known.profile(profile_name)
    if not profile.has_gpu:
        return known.alias(alias_name).runs_on_cpu
    return known.alias(alias_name).vram_gb <= profile.usable_vram_gb
