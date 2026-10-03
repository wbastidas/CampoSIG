"""Input and output validation for the agent layer (RF-182).

The golden sets of RNF-060 already **measure** whether a report leaks personal data, and the measure
has been zero from the day it was written. That is not the same as preventing it: the deterministic
nodes quote little free text, so the measure was zero because of what the nodes happen to do, not
because anything stopped them. The moment an LLM node writes a summary from a technician's dictation
— I12 — the first customer phone number will walk into a report, and the golden set will report it
after the fact, on a corpus, not on the report a supervisor is reading.

So this module is the runtime half of RF-182, and the shape follows from what each defect deserves:

* **Personal data is redacted, not dropped.** An observation that says «el cliente reportó al
  0991234567 que la luminaria falla» is a *useful* observation; the number is incidental. Deleting
  the observation would cost the finding, and refusing the whole report would cost every finding.
* **A non-neutral sentence is dropped, not rewritten.** RF-174 asks for a report that marks for
  verification and does not accuse. A deterministic rule cannot rewrite an accusation into a
  neutral statement — a reworded accusation is still an accusation — so the honest action is to
  refuse the observation and count it, exactly as the evidence guardrail does.
* **Nothing is silent.** Every redaction and every refusal comes back, so a node that starts
  producing them is visible on the next run rather than in six months.

The input half is narrow on purpose: a cap on how much free text goes into a node, because a
20 000-character «observation» pasted into a capture is how a prompt budget disappears and how an
injection gets room to work. The content of the input is not judged here — RNF-060's injection cases
are what prove the nodes ignore instructions, and a keyword blocklist would give false confidence
about a problem it cannot solve.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from app.agents.report import AgentReport, Discard, Observation

#: What replaces a redacted value. Says what was removed, so a reader is not left wondering whether
#: a sentence was mangled.
REDACTION = "[dato personal removido]"

#: Longest free-text field a node may receive. Generous for a real dictation (a long capture runs to
#: a couple of thousand characters) and far below what a pasted document would be.
MAX_INPUT_CHARS = 4000

#: Longest observation message and summary a report may carry. A message that needs more than this
#: is not an observation, it is an essay, and a supervisor will not read it.
MAX_MESSAGE_CHARS = 600
MAX_SUMMARY_CHARS = 2000

#: How many times a producer is asked again after a failed validation (RF-182's «re-ask»). Three,
#: because a model that cannot satisfy a format rule in three attempts will not satisfy it in ten,
#: and the run has a budget.
MAX_REASKS = 3

#: Words that turn a finding into an accusation. RF-174: «marca para verificación, no acusa». Kept
#: short and specific: a list long enough to catch ordinary Spanish would refuse real observations,
#: and a guardrail that refuses real work gets switched off.
ACCUSATORY_TERMS = (
    "mintió",
    "mintio",
    "miente",
    "engañó",
    "engano",
    "falsificó",
    "falsifico",
    "falseó",
    "falseo",
    "fraude",
    "fraudulento",
    "negligente",
    "negligencia",
    "irresponsable",
    "incompetente",
    "mentira",
    "estafa",
    "dolo",
)

#: Ecuadorian mobile and landline numbers, and the international form. Deliberately anchored on the
#: shapes the country uses rather than «any nine digits»: an asset code and a kVA reading are digits
#: too, and a guard that redacted those would be turned off within a week.
#: One optional separator between the groups a dictated number comes out in: some ASR renders
#: «cero nueve nueve, uno dos tres, cuatro cinco seis siete» with spaces, and a guard that only saw
#: the contiguous form would miss the dictated one, which is the form this platform produces most.
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+593[\s-]?|00593[\s-]?|0)"
    r"(?:9(?:[\s-]?\d){8}|[2-7](?:[\s-]?\d){7})(?!\d)",
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

#: Ten consecutive digits: a *candidate* cédula. Whether it is one is decided by the check digit,
#: below — which is the difference between a guard people keep and a guard people disable.
_TEN_DIGITS_RE = re.compile(r"(?<!\d)\d{10}(?!\d)")


def is_ecuadorian_id(value: str) -> bool:
    """Whether ten digits are a valid Ecuadorian cédula.

    The real algorithm, not a length check: the first two digits are a province (01 to 24, plus 30
    for citizens registered abroad), the third is below 6 for a natural person, and the tenth is a
    modulus-10 check over the first nine with weights 2,1,2,1 and so on.

    Implemented because the alternative — redacting every ten-digit run — would eat asset codes,
    meter numbers and account references, and a guardrail that mangles real data is a guardrail
    somebody removes.
    """
    if len(value) != 10 or not value.isdigit():
        return False
    province = int(value[:2])
    if not (1 <= province <= 24 or province == 30):
        return False
    if int(value[2]) >= 6:
        return False
    total = 0
    for index, digit in enumerate(value[:9]):
        weight = 2 if index % 2 == 0 else 1
        product = int(digit) * weight
        total += product - 9 if product > 9 else product
    expected = (10 - total % 10) % 10
    return expected == int(value[9])


@dataclass
class Redaction:
    """One value removed from a text, and what kind it was."""

    kind: str
    where: str

    def describe(self) -> str:
        return f"{self.kind} en {self.where}"


def redact(text: str) -> tuple[str, list[str]]:
    """Remove personal data from a text. Returns the text and what kinds were removed.

    Order matters twice.

    The **e-mail goes first**, because its local part can contain a digit run that the phone pattern
    would otherwise cut in half, leaving half an address behind.

    The **cédula goes before the phone**, because in Ecuador the two shapes overlap: a Guayas cédula
    starts «09» and so does every mobile number. The identifier check resolves almost all of it — a
    mobile's third digit is an operator prefix of 6 or more, which the natural-person rule rejects —
    but a «093» mobile can pass the check digit by coincidence and be reported as a cédula. Both are
    personal data and both are removed either way, so the ambiguity costs a label and never the
    protection. Said here rather than left for somebody to rediscover.
    """
    kinds: list[str] = []
    cleaned = text

    if _EMAIL_RE.search(cleaned):
        cleaned = _EMAIL_RE.sub(REDACTION, cleaned)
        kinds.append("correo")

    def _maybe_id(match: re.Match[str]) -> str:
        return REDACTION if is_ecuadorian_id(match.group()) else match.group()

    after_ids = _TEN_DIGITS_RE.sub(_maybe_id, cleaned)
    if after_ids != cleaned:
        kinds.append("cédula")
        cleaned = after_ids

    if _PHONE_RE.search(cleaned):
        cleaned = _PHONE_RE.sub(REDACTION, cleaned)
        kinds.append("teléfono")

    return cleaned, kinds


def is_neutral(text: str) -> bool:
    """Whether a sentence marks for verification rather than accusing (RF-174)."""
    folded = text.lower()
    return not any(term in folded for term in ACCUSATORY_TERMS)


def clamp_input(text: str | None, *, limit: int = MAX_INPUT_CHARS) -> tuple[str, bool]:
    """Cut free text down to what a node may receive. Returns the text and whether it was cut.

    The cut is reported rather than silent: a node that produced nothing useful because its input
    was truncated is a different problem from a node that produced nothing useful.
    """
    if not text:
        return "", False
    if len(text) <= limit:
        return text, False
    return text[:limit], True


@dataclass
class Validation:
    """What the output guardrail did to a report."""

    kept: list[Observation] = field(default_factory=list)
    dropped: list[Discard] = field(default_factory=list)
    #: Human-readable descriptions of every redaction, for the run's trace.
    redactions: list[str] = field(default_factory=list)
    summary: str = ""
    summary_redacted: bool = False
    summary_truncated: bool = False

    @property
    def ok(self) -> bool:
        """True when nothing had to be changed or refused.

        What the re-ask loop reads: a producer whose output needed no intervention is one whose
        next output probably will not either.
        """
        return not (self.dropped or self.redactions or self.summary_truncated)

    def as_dict(self) -> dict[str, object]:
        return {
            "kept": len(self.kept),
            "dropped": [
                {"observation_id": item.observation_id, "node": item.node, "reason": item.reason}
                for item in self.dropped
            ],
            "redactions": self.redactions,
            "summary_redacted": self.summary_redacted,
            "summary_truncated": self.summary_truncated,
        }


def validate_report(report: AgentReport) -> Validation:
    """Apply the output guardrail to a report, without mutating it.

    Returns what should be kept and what was changed; :func:`enforce` is what applies it. Split so a
    caller can inspect a report — a test, a review screen — without rewriting it.
    """
    result = Validation()

    summary, summary_kinds = redact(report.summary)
    if summary_kinds:
        result.summary_redacted = True
        result.redactions.extend(f"{kind} en el resumen" for kind in summary_kinds)
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[:MAX_SUMMARY_CHARS]
        result.summary_truncated = True
    result.summary = summary

    for observation in report.observations:
        if not is_neutral(observation.message):
            # Dropped rather than reworded: a reworded accusation is still an accusation, and a
            # deterministic rule has no way to say the same thing neutrally (RF-174).
            result.dropped.append(
                Discard(
                    observation.id,
                    observation.node,
                    "lenguaje no neutral: una observación marca para verificación, no acusa",
                )
            )
            continue

        message, kinds = redact(observation.message)
        if kinds:
            result.redactions.extend(f"{kind} en {observation.id}" for kind in kinds)
        truncated = len(message) > MAX_MESSAGE_CHARS
        if truncated:
            message = message[:MAX_MESSAGE_CHARS]
            result.redactions.append(f"mensaje recortado en {observation.id}")

        action = observation.suggested_action
        if action:
            action, action_kinds = redact(action)
            if action_kinds:
                result.redactions.extend(
                    f"{kind} en la acción sugerida de {observation.id}" for kind in action_kinds
                )

        result.kept.append(
            observation.model_copy(update={"message": message, "suggested_action": action})
        )

    return result


def enforce(report: AgentReport) -> tuple[AgentReport, Validation]:
    """The validated report and what had to be done to it.

    The refusals are added to the report's own `discarded` counter rather than kept apart: a
    supervisor comparing «12 observaciones» with «14 descartadas» is reading one number for one
    idea, and two counters for «the guardrail refused something» would be two places to look.
    """
    result = validate_report(report)
    validated = report.model_copy(
        update={
            "summary": result.summary,
            "observations": result.kept,
            "discarded": report.discarded + len(result.dropped),
        }
    )
    return validated, result


def with_reask(
    produce: Callable[[int], AgentReport],
    *,
    attempts: int = MAX_REASKS,
) -> tuple[AgentReport, Validation, int]:
    """Ask a producer again when its output fails validation (RF-182's «re-ask»).

    :param produce: called with the attempt number, starting at 1. The number is passed so a future
        LLM node can put the previous failure in its prompt — «no personal data» works better as a
        correction than as a standing instruction.
    :returns: the enforced report, its validation, and how many attempts were made.

    Two things keep this from burning a run's budget:

    * **It stops as soon as an output validates.** A first attempt that needs no intervention is the
      normal case.
    * **It stops when an output repeats.** The deterministic graph of I12's first half is a pure
      function of its facts, so asking it again returns the same report; retrying identical output
      would spend the budget to receive the same refusals. Written this way rather than «only retry
      LLM nodes» because the loop should not have to know which kind of node it is driving.
    """
    seen: set[str] = set()
    report = produce(1)
    validated, result = enforce(report)
    made = 1
    while not result.ok and made < attempts:
        fingerprint = report.model_dump_json()
        if fingerprint in seen:
            # The producer is deterministic on these facts: another attempt returns this again.
            break
        seen.add(fingerprint)
        made += 1
        report = produce(made)
        validated, result = enforce(report)
    return validated, result, made
