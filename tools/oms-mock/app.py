"""Minimal stand-in for the corporate OMS/ADMS (RF-123).

Pins the two halves of the contract:

* **A fault event becomes one work order, keyed by the OMS event id.** A network that keeps
  reporting the same trip while a crew is on the way is normal, and it must not produce a second
  crew. `/events` therefore serves the same event ids on every call, deliberately.
* **What came back is readable.** `/outages` returns what the platform reported, so a test can
  assert «se reflejó en el OMS» rather than assuming it.

Standard library only.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PORT = 8185

#: Open fault events. `event_id` is the OMS's, and it is the idempotency key.
EVENTS = [
    {
        "event_id": "OMS-2026-004411",
        "feeder_code": "04BH070T11",
        "asset_code": "SEC-00231",
        "asset_type_key": "fuse_switch",
        "priority": "critica",
        "description": "Apertura de seccionador fusible, alimentador sur",
        "clients_affected": 412,
    },
    {
        "event_id": "OMS-2026-004412",
        "feeder_code": "04BH070T12",
        "priority": "alta",
        "description": "Baja tensión reportada por SCADA",
        "clients_affected": 37,
    },
]

#: Interruption records the platform reported back.
OUTAGES: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send({"status": "ok"})
        elif path == "/events":
            self._send({"items": EVENTS, "total": len(EVENTS)})
        elif path == "/outages":
            self._send({"items": OUTAGES})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        if urlparse(self.path).path != "/outages":
            self._send({"error": "not found"}, 404)
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send({"error": "invalid json"}, 400)
            return
        OUTAGES.append(payload)
        # El OMS acusa recibo con su propio identificador de registro, que es lo que una
        # distribuidora pide para poder auditar después que la interrupción quedó reflejada.
        self._send({"accepted": True, "outage_record_id": f"OR-{len(OUTAGES):06d}"})

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    print(f"oms-mock listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
