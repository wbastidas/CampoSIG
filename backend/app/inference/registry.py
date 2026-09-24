"""The model gateway's alias registry (M19, RF-200, RF-203).

Rule 13 says the server consumes LLMs and VLMs **only through aliases**. This module is why that
is true rather than merely intended: `infra/inference/aliases.yaml` says which model is behind
`llm-judge`, and no agent mentions a model name. A model name written into code would turn
changing runtime — llama.cpp to vLLM, or back — into a refactor instead of an edit.

The registry is also where the hardware profiles live (SRS 7.9), because admission is a property
of the pair: the same alias is interactive on a 24 GB GPU, queued for the night on CPU, and
switched off entirely where there is no GPU at all.
"""

from __future__ import annotations

from datetime import time
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator


class Priority(StrEnum):
    """The priority classes of RF-202, most urgent first."""

    INTERACTIVE = "interactive"
    PRE_REVIEW = "pre_review"
    RETRANSCRIPTION = "retranscription"
    PRE_LABELLING = "pre_labelling"
    TRAINING = "training"


class Degradation(StrEnum):
    """What happens to a task the profile cannot run now (RF-204)."""

    #: Wait for the night window. For work whose answer is still useful tomorrow.
    NIGHT_BATCH = "night_batch"
    #: Drop it and say so. For work that is worthless late — a dictation proposal that
    #: arrives tomorrow morning helps nobody; the technician typed the field and moved on.
    SKIP = "skip"


class ModelAlias(BaseModel):
    """One logical alias. The model behind it is configuration, never code."""

    name: str
    purpose: str
    model: str
    runtime: str
    priority: Priority
    #: Resident VRAM, not file size: it is what decides whether two aliases can coexist.
    vram_gb: float = Field(ge=0)
    runs_on_cpu: bool
    supports_grammar: bool
    #: The hardware cannot run this alias at all — profile A has no GPU, so the VLM is switched
    #: off rather than queued (SRS 7.9).
    when_unsupported: Degradation
    #: It does run here, but not right now: no headroom, or not an interactive alias of this
    #: profile. In profile B the VLM waits for the night rather than being lost (RNF-026).
    when_busy: Degradation


class ServerProfile(BaseModel):
    """One of the hardware profiles of SRS 7.9. ``vram_gb: 0`` means there is no GPU."""

    name: str
    label: str
    vram_gb: float = Field(ge=0)
    #: Reserved for context, activations and fragmentation. It is what makes RF-203 true by
    #: arithmetic: without it, 6.5 + 9 GB "fits" in a 16 GB card and the judge and the VLM would
    #: be allowed to coexist, which is exactly what that requirement forbids.
    vram_headroom_gb: float = Field(default=0, ge=0)
    interactive_aliases: list[str] = Field(default_factory=list)

    @property
    def has_gpu(self) -> bool:
        return self.vram_gb > 0

    @property
    def usable_vram_gb(self) -> float:
        """VRAM available to models, after the reserve."""
        return max(self.vram_gb - self.vram_headroom_gb, 0.0)


class Windows(BaseModel):
    """The scheduler's day and night windows (RF-202), in the server's local time."""

    day_starts_at: time
    day_ends_at: time
    weekend_is_night: bool = True

    @field_validator("day_ends_at")
    @classmethod
    def day_must_have_length(cls, value: time, info: object) -> time:
        data = getattr(info, "data", {})
        start = data.get("day_starts_at")
        if start is not None and value <= start:
            # A day window that ends before it starts would make every hour a night window,
            # which is how training quietly takes the GPU at ten in the morning.
            raise ValueError("la ventana de día termina antes de empezar")
        return value


class InferenceRegistry(BaseModel):
    version: int
    windows: Windows
    priorities: list[Priority]
    aliases: dict[str, ModelAlias]
    profiles: dict[str, ServerProfile]

    def alias(self, name: str) -> ModelAlias:
        found = self.aliases.get(name)
        if found is None:
            known = ", ".join(sorted(self.aliases))
            raise KeyError(f"alias de modelo desconocido '{name}'; conocidos: {known}")
        return found

    def profile(self, name: str) -> ServerProfile:
        found = self.profiles.get(name)
        if found is None:
            known = ", ".join(sorted(self.profiles))
            raise KeyError(f"perfil de servidor desconocido '{name}'; conocidos: {known}")
        return found

    def rank(self, priority: Priority) -> int:
        """Position in the priority order. Lower runs first.

        Read from the file's own list rather than from the enum's declaration order, so
        reordering the list in configuration reorders the scheduler — which is the point of
        having it in configuration.
        """
        return self.priorities.index(priority)


class RegistryError(Exception):
    """Raised when the registry does not describe a workable gateway."""


def _validate(registry: InferenceRegistry) -> None:
    """Refuse a registry that would fail at runtime instead of at load."""
    problems: list[str] = []

    for name, alias in registry.aliases.items():
        if alias.priority not in registry.priorities:
            problems.append(f"el alias '{name}' usa una prioridad que no está en la lista")

    for name, profile in registry.profiles.items():
        for alias_name in profile.interactive_aliases:
            declared = registry.aliases.get(alias_name)
            if declared is None:
                problems.append(f"el perfil '{name}' declara el alias inexistente '{alias_name}'")
                continue
            if not profile.has_gpu and not declared.runs_on_cpu:
                problems.append(
                    f"el perfil '{name}' no tiene GPU y declara '{alias_name}' como interactivo, "
                    "pero ese alias no corre en CPU"
                )
            if profile.has_gpu and declared.vram_gb > profile.usable_vram_gb:
                problems.append(
                    f"'{alias_name}' necesita {declared.vram_gb} GB y el perfil '{name}' "
                    f"tiene {profile.usable_vram_gb} GB utilizables"
                )

    if problems:
        raise RegistryError("; ".join(problems))


@lru_cache
def load_registry(path: str | None = None) -> InferenceRegistry:
    """Load and validate the alias registry."""
    default = Path(__file__).resolve().parents[3] / "infra" / "inference" / "aliases.yaml"
    location = Path(path) if path else default
    data = yaml.safe_load(location.read_text(encoding="utf-8"))

    # The file keys aliases and profiles by name; the models carry the name so nothing has to
    # pass the key around beside the object.
    for name, alias in (data.get("aliases") or {}).items():
        alias["name"] = name
    for name, profile in (data.get("profiles") or {}).items():
        profile["name"] = name

    registry = InferenceRegistry.model_validate(data)
    _validate(registry)
    return registry
