"""Minimal stand-in for the call-centre / claims system (RF-124).

Lets I8 be built and tested without the real system, and pins the two halves of the contract
that matter: a claim becomes a work order exactly once, and approving that work order closes
the claim. The second half is the one that is easy to get wrong in a way nobody notices —
the crew fixed the lamp, the platform approved the work, and the customer's claim stayed open.

Standard library only.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

PORT = 8183

# Open claims the platform can turn into work orders. `claim_id` belongs to the call centre.
CLAIMS: list[dict] = [
    {
        "claim_id": "REC-2026-004411",
        "kind": "luminaria_apagada",
        "priority": "alta",
        "reported_at": "2026-06-01T20:15:00Z",
        "address": "Av. Principal y 5ta, Durán",
        "asset_code": "L-010233",
        "customer_phone": "099-000-0000",
        "status": "open",
    },
    {
        "claim_id": "REC-2026-004412",
        "kind": "sin_servicio",
        "priority": "critica",
        "reported_at": "2026-06-02T06:40:00Z",
        "address": "Cdla. Los Ceibos mz 4",
        "asset_code": "P-000452",
        "customer_phone": "099-111-1111",
        "status": "open",
    },
]

# Closures the platform has pushed, so a contract test can assert the round trip.
CLOSURES: list[dict] = []


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
        elif path == "/claims":
            open_claims = [c for c in CLAIMS if c["status"] == "open"]
            self._send({"items": open_claims, "total": len(open_claims)})
        elif path == "/closures":
            self._send({"items": CLOSURES})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        path = urlparse(self.path).path

        if path == "/claims/close":
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._send({"error": "invalid json"}, 400)
                return
            claim_id = payload.get("claim_id")
            claim = next((c for c in CLAIMS if c["claim_id"] == claim_id), None)
            if claim is None:
                # A closure for an unknown claim is the caller's mistake, so 404 and not a
                # retryable error: sending it again will not make the claim exist.
                self._send({"error": f"unknown claim {claim_id}"}, 404)
                return
            claim["status"] = "closed"
            CLOSURES.append(payload)
            self._send({"accepted": True, "claim_id": claim_id, "status": "closed"})
            return

        self._send({"error": "not found"}, 404)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    print(f"call-centre-mock listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
