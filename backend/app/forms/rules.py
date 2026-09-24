"""Conditional requirements, evaluated identically on three platforms (I5, SRS 7.2).

The blocks declare their rules in JSON Logic so the backend, the web and the phone agree. Writing
the same algorithm three times does not produce agreement; it produces three algorithms that
happen to match on the cases somebody thought of. What produces agreement is
``forms/contract/validation-cases.json``: one corpus, run by all three test suites, that fails
when an implementation drifts.

The failure that corpus prevents is expensive in the field, in both directions. If the phone
accepts a capture the server later rejects, the crew's work comes back the next day and nobody
knows why. If the phone demands a field the server does not, the crew cannot close the work order
with the network down — which is the situation the whole product exists for.

The evaluator is a **subset** of JSON Logic on purpose: only the operators the block library
uses. A full library would be more general, and would also accept expressions the mobile renderer
cannot evaluate. An unknown operator is False rather than an error, because a badly written rule
must not stop a technician from sending a day's work; it is caught by catalogue validation,
before the form ever reaches a phone.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MissingRequirement:
    """One field a rule demanded and the answers do not supply."""

    field: str
    #: The rule's own message, when it has one. Presentation: the contract is the field.
    message: str | None = None


def is_answered(value: Any) -> bool:
    """Whether a value counts as an answer.

    Three cases worth naming, because each is a way all three implementations get it wrong at
    once:

    * **Zero is an answer.** A measured 0 Ω is a result, and one of the ones that matter.
    * **False is an answer.** "Was it sign-posted? No" is a reply, not a blank.
    * **Whitespace is not.** A field holding a space reads as empty on the screen and on paper.
    """
    if value is None:
        return False
    if isinstance(value, bool | int | float):
        return True
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence):
        return bool(value)
    return True


def resolve(token: Any, answers: Mapping[str, Any]) -> Any:
    """Resolve an operand: ``{"var": "x"}`` reads an answer, anything else is a literal."""
    if isinstance(token, Mapping) and "var" in token:
        return answers.get(token["var"])
    return token


def _same(left: Any, right: Any) -> bool:
    """Equality that does not coerce across types.

    ``11`` and ``"11"`` are different values. Without this, a platform with loose comparison
    would fire rules the others do not — and booleans would compare equal to 0 and 1, which is
    how "was it sign-posted?" ends up matching a count.
    """
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    if isinstance(left, str) != isinstance(right, str):
        return False
    return bool(left == right)


def evaluate_condition(condition: Any, answers: Mapping[str, Any]) -> bool:
    """Evaluate one JSON Logic condition. Anything unrecognised is False."""
    if not isinstance(condition, Mapping) or not condition:
        return False

    if "==" in condition:
        operands = condition["=="]
        if not isinstance(operands, Sequence) or len(operands) != 2:
            return False
        return _same(resolve(operands[0], answers), resolve(operands[1], answers))

    if "!=" in condition:
        operands = condition["!="]
        if not isinstance(operands, Sequence) or len(operands) != 2:
            return False
        return not _same(resolve(operands[0], answers), resolve(operands[1], answers))

    if "in" in condition:
        operands = condition["in"]
        if not isinstance(operands, Sequence) or len(operands) != 2:
            return False
        needle = resolve(operands[0], answers)
        haystack = resolve(operands[1], answers)
        if isinstance(haystack, str):
            # JSON Logic defines `in` over a string as substring containment.
            return isinstance(needle, str) and needle in haystack
        if isinstance(haystack, Sequence) and not isinstance(haystack, str | bytes):
            return any(_same(needle, item) for item in haystack)
        # Neither a list nor a string: False, not an exception.
        return False

    # «Está contestado» y su complemento. Escritos con `is_answered`, la misma función que decide
    # el otro lado de la regla: si un 0 cuenta como respuesta para `require`, tiene que contar
    # igual para la condición, o una regla diría una cosa y su exigencia otra.
    if "!!" in condition:
        return is_answered(resolve(condition["!!"], answers))

    if "!" in condition:
        return not is_answered(resolve(condition["!"], answers))

    if "and" in condition:
        parts = condition["and"]
        if not isinstance(parts, Sequence) or not parts:
            return False
        return all(evaluate_condition(part, answers) for part in parts)

    if "or" in condition:
        parts = condition["or"]
        if not isinstance(parts, Sequence) or not parts:
            return False
        return any(evaluate_condition(part, answers) for part in parts)

    return False


def missing_requirements(
    rules: Sequence[Mapping[str, Any]], answers: Mapping[str, Any]
) -> list[MissingRequirement]:
    """Fields the rules demand and the answers do not supply, in the rules' own order.

    In order, and deduplicated: two rules may demand the same field, and telling the crew twice
    about one empty box is a defect of the platform rather than a fact about their work. The
    order is the rules' order so the list a technician reads does not shuffle between platforms.
    """
    found: list[MissingRequirement] = []
    seen: set[str] = set()
    for rule in rules:
        if not isinstance(rule, Mapping):
            continue
        required = rule.get("require") or []
        if not required or not isinstance(required, Sequence) or isinstance(required, str):
            continue
        if not evaluate_condition(rule.get("when"), answers):
            continue
        message = rule.get("message")
        for field in required:
            key = str(field)
            if key in seen or is_answered(answers.get(key)):
                continue
            seen.add(key)
            found.append(MissingRequirement(field=key, message=str(message) if message else None))
    return found
