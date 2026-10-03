"""Minimal stand-in for the corporate work-order platform (RF-120, satellite mode).

Lets I3 and I8 be built and tested without the real system being available, and pins the
contract that matters most: the external system owns the work-order number, so importing
the same one twice must not create two work orders (idempotency by external_ref).

Standard library only.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PORT = 8182

# Seed work orders the platform can import. external_ref is the key: it belongs to the
# corporate system, mirroring Workforce's workOrderId (addendum 1.1).
WORK_ORDERS = [
    {
        "external_ref": "OT-2026-000101",
        "type": "inspeccion_preventiva",
        "area": "mantenimiento",
        "priority": "media",
        "asset_code": "P-000452",
        "description": "Inspección preventiva de estructura",
        "status": "open",
    },
    {
        "external_ref": "OT-2026-000102",
        "type": "luminaria_falla",
        "area": "apg",
        "priority": "alta",
        "asset_code": "L-010233",
        "description": "Luminaria apagada reportada por cliente",
        "status": "open",
    },
]

# Statuses the platform has pushed back, so tests can assert the round trip.
RECEIVED_STATUSES: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            self._send({"status": "ok"})
        elif path == "/work-orders":
            self._send({"items": WORK_ORDERS, "total": len(WORK_ORDERS)})
        elif path == "/received-statuses":
            self._send({"items": RECEIVED_STATUSES})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        path = urlparse(self.path).path
        if path == "/work-orders/status":
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._send({"error": "invalid json"}, 400)
                return
            RECEIVED_STATUSES.append(payload)
            self._send({"accepted": True, "external_ref": payload.get("external_ref")})
            return
        self._send({"error": "not found"}, 404)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    print(f"legacy-ot-mock listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
