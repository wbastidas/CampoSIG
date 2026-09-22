"""How an exchange actually leaves the process (RF-120, RF-124).

One narrow interface, two implementations, and the reason is the same as everywhere else in
this codebase: the part that can be tested exhaustively should not be entangled with the part
that needs a network.

:class:`HttpTransport` uses the standard library. No HTTP client library appears in the
backend's dependencies for this, because the corporate APIs are two endpoints each and a
dependency bought for that is a dependency to keep patched forever.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol


class TransportError(Exception):
    """A delivery that did not happen. Carries whether retrying could help."""

    def __init__(self, message: str, *, retryable: bool = True, status: int | None = None) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.status = status


@dataclass(frozen=True)
class Response:
    status: int
    body: dict[str, Any]


class Transport(Protocol):
    def get(self, url: str, *, timeout: float = 10.0) -> Response: ...

    def post(self, url: str, payload: dict[str, Any], *, timeout: float = 10.0) -> Response: ...


class HttpTransport:
    """Plain JSON over HTTP, standard library only."""

    def __init__(self, *, headers: dict[str, str] | None = None) -> None:
        self._headers = {"Content-Type": "application/json", "Accept": "application/json"}
        self._headers.update(headers or {})

    def get(self, url: str, *, timeout: float = 10.0) -> Response:
        return self._send(urllib.request.Request(url, headers=self._headers), timeout)

    def post(self, url: str, payload: dict[str, Any], *, timeout: float = 10.0) -> Response:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=self._headers, method="POST")
        return self._send(request, timeout)

    @staticmethod
    def _send(request: urllib.request.Request, timeout: float) -> Response:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as raw:
                text = raw.read().decode("utf-8") or "{}"
                return Response(status=raw.status, body=_parse(text))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            # 4xx means the request was wrong, so retrying it unchanged is pointless and
            # hammering the corporate system for it is worse than pointless. 5xx is theirs
            # to recover from, so it is worth another attempt.
            raise TransportError(
                f"{exc.code} {exc.reason}: {detail}",
                retryable=exc.code >= 500 or exc.code == 429,
                status=exc.code,
            ) from exc
        except urllib.error.URLError as exc:
            raise TransportError(f"no se pudo conectar: {exc.reason}", retryable=True) from exc
        except TimeoutError as exc:
            raise TransportError("la llamada expiró", retryable=True) from exc


def _parse(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        # A body that is not JSON is not retryable: the other side is not speaking the
        # contract, and the same request will get the same answer.
        raise TransportError(f"la respuesta no es JSON: {text[:200]!r}", retryable=False) from exc
    return parsed if isinstance(parsed, dict) else {"items": parsed}


@dataclass
class RecordingTransport:
    """A transport that records calls and returns scripted answers. For tests only.

    Scripted per (method, url) so a test can make one endpoint fail while another works —
    which is the case that matters when one connector is down and the other is not.
    """

    responses: dict[tuple[str, str], Response | TransportError] = field(default_factory=dict)
    calls: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)
    default: Response | None = None

    def script(self, method: str, url: str, answer: Response | TransportError) -> None:
        self.responses[(method.upper(), url)] = answer

    def get(self, url: str, *, timeout: float = 10.0) -> Response:
        return self._answer("GET", url, None)

    def post(self, url: str, payload: dict[str, Any], *, timeout: float = 10.0) -> Response:
        return self._answer("POST", url, payload)

    def _answer(self, method: str, url: str, payload: dict[str, Any] | None) -> Response:
        self.calls.append((method, url, payload))
        answer = self.responses.get((method, url), self.default)
        if answer is None:
            raise TransportError(f"el test no guionó {method} {url}", retryable=False)
        if isinstance(answer, TransportError):
            raise answer
        return answer
