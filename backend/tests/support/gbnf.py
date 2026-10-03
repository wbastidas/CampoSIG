"""A minimal GBNF matcher, so the generated grammar is tested for what it means.

Asserting that :func:`build_grammar` returns a particular string tests the string. What
matters is what the grammar *accepts*: llama.cpp will constrain a model with it, and a
grammar that happily accepts an invalid enum value is a bug no string comparison finds.

So this parses the subset of GBNF the generator emits — literals, character classes, rule
references, groups, alternation and the ``*`` ``?`` ``+`` postfixes — and matches text
against it with full backtracking. It is test support, not production code: small inputs,
no performance concerns, and it fails loudly on anything outside that subset rather than
guessing.
"""

from __future__ import annotations

import re
from typing import Any

_WS = re.compile(r"[ \t]*")


class GbnfError(Exception):
    """Raised on grammar text this matcher does not understand."""


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def _skip(self) -> None:
        self.pos = _WS.match(self.text, self.pos).end()  # type: ignore[union-attr]

    def at_end(self) -> bool:
        self._skip()
        return self.pos >= len(self.text)

    def parse_alternation(self) -> Any:
        options = [self.parse_sequence()]
        while True:
            self._skip()
            if self.pos < len(self.text) and self.text[self.pos] == "|":
                self.pos += 1
                options.append(self.parse_sequence())
            else:
                break
        return ("alt", options) if len(options) > 1 else options[0]

    def parse_sequence(self) -> Any:
        items: list[Any] = []
        while True:
            self._skip()
            if self.pos >= len(self.text) or self.text[self.pos] in "|)":
                break
            items.append(self.parse_postfix())
        return ("seq", items)

    def parse_postfix(self) -> Any:
        item = self.parse_atom()
        while self.pos < len(self.text) and self.text[self.pos] in "*?+":
            symbol = self.text[self.pos]
            self.pos += 1
            bounds = {"*": (0, None), "?": (0, 1), "+": (1, None)}[symbol]
            item = ("rep", item, bounds[0], bounds[1])
        return item

    def parse_atom(self) -> Any:
        self._skip()
        if self.pos >= len(self.text):
            raise GbnfError("regla incompleta")
        char = self.text[self.pos]
        if char == '"':
            return ("lit", self._parse_literal())
        if char == "[":
            return self._parse_class()
        if char == "(":
            self.pos += 1
            inner = self.parse_alternation()
            self._skip()
            if self.pos >= len(self.text) or self.text[self.pos] != ")":
                raise GbnfError("falta ')'")
            self.pos += 1
            return inner
        match = re.compile(r"[A-Za-z][A-Za-z0-9_-]*").match(self.text, self.pos)
        if match is None:
            raise GbnfError(
                f"token inesperado en la posición {self.pos}: {self.text[self.pos :][:20]!r}"
            )
        self.pos = match.end()
        return ("ref", match.group(0))

    def _parse_literal(self) -> str:
        self.pos += 1  # opening quote
        out: list[str] = []
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "\\":
                self.pos += 1
                out.append(_unescape(self.text[self.pos]))
            elif char == '"':
                self.pos += 1
                return "".join(out)
            else:
                out.append(char)
            self.pos += 1
        raise GbnfError("literal sin cerrar")

    def _parse_class(self) -> Any:
        self.pos += 1  # '['
        negated = False
        if self.pos < len(self.text) and self.text[self.pos] == "^":
            negated = True
            self.pos += 1
        ranges: list[tuple[str, str]] = []
        while self.pos < len(self.text) and self.text[self.pos] != "]":
            char = self.text[self.pos]
            if char == "\\":
                self.pos += 1
                char = _unescape(self.text[self.pos])
            self.pos += 1
            if (
                self.pos + 1 < len(self.text)
                and self.text[self.pos] == "-"
                and self.text[self.pos + 1] != "]"
            ):
                self.pos += 1
                upper = self.text[self.pos]
                if upper == "\\":
                    self.pos += 1
                    upper = _unescape(self.text[self.pos])
                self.pos += 1
                ranges.append((char, upper))
            else:
                ranges.append((char, char))
        if self.pos >= len(self.text):
            raise GbnfError("clase de caracteres sin cerrar")
        self.pos += 1  # ']'
        return ("class", negated, ranges)


def _unescape(char: str) -> str:
    return {"n": "\n", "t": "\t", "r": "\r"}.get(char, char)


def parse_grammar(text: str) -> dict[str, Any]:
    """Parse a GBNF grammar into rules. Raises on anything outside the supported subset."""
    rules: dict[str, Any] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "::=" not in stripped:
            raise GbnfError(f"línea sin '::=': {stripped!r}")
        name, body = stripped.split("::=", 1)
        parser = _Parser(body)
        expression = parser.parse_alternation()
        if not parser.at_end():
            raise GbnfError(f"texto sobrante en la regla '{name.strip()}'")
        rules[name.strip()] = expression
    if "root" not in rules:
        raise GbnfError("la gramática no define 'root'")
    return rules


def _match(expression: Any, rules: dict[str, Any], text: str, index: int) -> set[int]:
    """Every position the expression could end at, starting from ``index``."""
    kind = expression[0]
    if kind == "lit":
        literal = expression[1]
        return {index + len(literal)} if text.startswith(literal, index) else set()
    if kind == "class":
        _, negated, ranges = expression
        if index >= len(text):
            return set()
        char = text[index]
        inside = any(low <= char <= high for low, high in ranges)
        return {index + 1} if inside != negated else set()
    if kind == "ref":
        target = rules.get(expression[1])
        if target is None:
            raise GbnfError(f"regla no definida: {expression[1]}")
        return _match(target, rules, text, index)
    if kind == "alt":
        results: set[int] = set()
        for option in expression[1]:
            results |= _match(option, rules, text, index)
        return results
    if kind == "seq":
        positions = {index}
        for item in expression[1]:
            nxt: set[int] = set()
            for position in positions:
                nxt |= _match(item, rules, text, position)
            if not nxt:
                return set()
            positions = nxt
        return positions
    if kind == "rep":
        _, item, minimum, maximum = expression
        positions = {index}
        results: set[int] = {index} if minimum == 0 else set()
        count = 0
        while positions and (maximum is None or count < maximum):
            nxt = set()
            for position in positions:
                # A zero-width repetition would loop forever and means nothing.
                nxt |= {end for end in _match(item, rules, text, position) if end > position}
            if not nxt:
                break
            count += 1
            positions = nxt
            if count >= minimum:
                results |= positions
        return results
    raise GbnfError(f"nodo desconocido: {kind}")


def accepts(grammar: str, text: str) -> bool:
    """True when the grammar matches the whole text."""
    rules = parse_grammar(grammar)
    return len(text) in _match(rules["root"], rules, text, 0)
