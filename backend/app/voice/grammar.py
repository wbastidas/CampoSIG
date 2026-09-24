"""GBNF grammar for the extraction sub-schema (I7, plan §I7).

The extractor is a 1.5B model running on a phone. Asked politely for JSON it will mostly
produce JSON; constrained by a grammar it cannot produce anything else. llama.cpp enforces
the grammar during sampling, so "100 % JSON validity" stops being a metric to measure and
becomes a property of the decoder.

Three shape decisions, each with a reason:

* **Every field is present, and "not dictated" is ``null``.** A grammar over a
  variable-length set of members in arbitrary order is either wrong about commas or
  enormous. Requiring all of them, in a fixed order, keeps the grammar small and makes the
  parse trivial — and it gives the model a way to say nothing about a field instead of
  inventing a value, which is the failure this whole increment exists to avoid.
* **Enums are literal alternatives of the canonical values.** The model cannot emit a code
  the profile has never heard of, so there is no unmappable value to reject downstream.
* **Arrays and nested objects are excluded.** A repeatable table (activities, materials) is
  filled one entry at a time, each entry its own dictation with its own sub-schema; a
  grammar covering the whole table would let one long utterance restructure the form.
"""

from __future__ import annotations

import re
from typing import Any

#: JSON scalar types the extractor may fill by voice.
_SCALAR_TYPES = frozenset({"string", "number", "integer", "boolean"})

_RULE_NAME_RE = re.compile(r"[^a-zA-Z0-9-]")

#: Primitives shared by every generated grammar. `ws` is permissive on purpose: the model
#: may or may not pretty-print, and rejecting a space is not a useful thing to enforce.
_PREAMBLE = """ws ::= [ \\t\\n]*
string ::= "\\"" char* "\\""
char ::= [^"\\\\] | "\\\\" ["\\\\/bfnrt]
number ::= "-"? [0-9]+ ("." [0-9]+)?
integer ::= "-"? [0-9]+
boolean ::= "true" | "false"
date ::= "\\"" [0-9] [0-9] [0-9] [0-9] "-" [0-9] [0-9] "-" [0-9] [0-9] "\\""
null ::= "null\""""


class GrammarError(Exception):
    """Raised when a schema cannot be expressed as a grammar."""


def _rule_name(field_key: str) -> str:
    """A GBNF-safe rule name derived from a field key."""
    safe = _RULE_NAME_RE.sub("-", field_key).strip("-").lower()
    return f"v-{safe or 'field'}"


def extractable_fields(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The fields of a composed form that a dictation may fill, in schema order.

    Excluded: anything the form marks ``x-voice: false`` (evidence URIs, coordinates read
    from the GPS), arrays, objects, and read-only fields injected from the work order.
    """
    properties: dict[str, Any] = schema.get("properties", {})
    selected: dict[str, dict[str, Any]] = {}
    for key, prop in properties.items():
        if not isinstance(prop, dict):
            continue
        if prop.get("x-voice") is False or prop.get("readOnly") is True:
            continue
        declared = prop.get("type")
        if declared not in _SCALAR_TYPES:
            continue
        selected[key] = prop
    return selected


def _escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _value_rule(field_key: str, prop: dict[str, Any]) -> str:
    """The right-hand side for one field's value."""
    enum_values = prop.get("enum")
    if isinstance(enum_values, list) and enum_values:
        alternatives = " | ".join(f'"\\"{_escape_literal(str(v))}\\""' for v in enum_values)
        return alternatives
    declared = prop.get("type")
    if declared == "string":
        return "date" if prop.get("format") == "date" else "string"
    if declared == "number":
        return "number"
    if declared == "integer":
        return "integer"
    if declared == "boolean":
        return "boolean"
    raise GrammarError(f"el campo '{field_key}' tiene un tipo que no se puede dictar: {declared}")


def build_grammar(schema: dict[str, Any], *, fields: list[str] | None = None) -> str:
    """Build a GBNF grammar for a composed form's dictation sub-schema.

    :param fields: restrict the grammar to these field keys, in this order. Used when the
        technician dictates one section at a time, which is how a long form is actually
        filled: a grammar over forty fields wastes the model's context on fields nobody
        is talking about.
    :raises GrammarError: if no field of the form can be dictated.
    """
    candidates = extractable_fields(schema)
    if fields is not None:
        missing = [key for key in fields if key not in candidates]
        if missing:
            raise GrammarError(
                "estos campos no son dictables en este formulario: " + ", ".join(sorted(missing))
            )
        candidates = {key: candidates[key] for key in fields}
    if not candidates:
        raise GrammarError("el formulario no tiene ningún campo que se pueda llenar por voz")

    members: list[str] = []
    rules: list[str] = []
    for field_key, prop in candidates.items():
        rule = _rule_name(field_key)
        members.append(f'"\\"{_escape_literal(field_key)}\\"" ws ":" ws {rule}')
        rules.append(f"{rule} ::= ({_value_rule(field_key, prop)}) | null")

    body = ' ws "," ws '.join(members)
    lines = [f'root ::= "{{" ws {body} ws "}}"', "", *rules, "", _PREAMBLE]
    return "\n".join(lines) + "\n"


def grammar_fingerprint(grammar: str) -> str:
    """Stable identity of a grammar, for the provenance record of an extraction."""
    import hashlib

    return hashlib.sha256(grammar.encode("utf-8")).hexdigest()[:16]
