"""Minimal stand-in for the corporate ERP (RF-122).

Lets the material catalogue, the stock and the movements be built and tested without the real ERP,
and pins the two parts of the contract that are easy to get wrong:

* **`complete`.** A batch that does not declare itself complete must not be able to retire codes.
  This mock can serve either kind, so the platform's refusal to withdraw on a partial pull is
  exercised rather than assumed. `/materials?partial=1` returns the batch without the flag.
* **Two movement endpoints, not one.** Consumption and return land in different places in a real
  ERP —the warehouse and scrap— so they are two endpoints here, and what arrived at each is
  readable, which is what lets a test assert the round trip.

Standard library only.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

PORT = 8184

#: The material list the ERP owns. Codes and descriptions in the shape a real ERP sends: a code, a
#: description, a unit of measure, and the construction unit it belongs to when it has one.
MATERIALS = [
    {
        "code": "MT-CRUCETA-2M",
        "label": "Cruceta de madera 2 m",
        "unit": "u",
        "uc_code": "ES-CR-02",
        "family": "estructuras",
        "synonyms": ["cruceta 2 metros"],
    },
    {
        "code": "MT-AISLADOR-PIN",
        "label": "Aislador tipo pin 15 kV",
        "unit": "u",
        "family": "aisladores",
    },
    {
        "code": "MT-LUM-LED-100",
        "label": "Luminaria LED 100 W",
        "unit": "u",
        "family": "alumbrado",
        "serialised": True,
    },
    {
        "code": "MT-CABLE-ACSR-2",
        "label": "Conductor ACSR 2 AWG",
        "unit": "m",
        "family": "conductores",
    },
    {
        "code": "MT-FUSIBLE-10K",
        "label": "Tirafusible 10K",
        "unit": "u",
        "family": "protecciones",
    },
]

#: Stock by warehouse and by vehicle. The vehicle matters most in the field: it decides whether
#: today's job can be done at all.
LOCATIONS = [
    {
        "kind": "bodega",
        "code": "BOD-GYE-01",
        "name": "Bodega central Guayaquil",
        "as_of": "2026-09-24T04:00:00+00:00",
        "lines": [
            {"material_code": "MT-CRUCETA-2M", "quantity": 42, "unit": "u"},
            {"material_code": "MT-AISLADOR-PIN", "quantity": 180, "unit": "u"},
            {"material_code": "MT-LUM-LED-100", "quantity": 26, "unit": "u"},
            {"material_code": "MT-CABLE-ACSR-2", "quantity": 1250.5, "unit": "m"},
        ],
    },
    {
        "kind": "vehiculo",
        "code": "VEH-0142",
        "name": "Canasta 0142",
        "as_of": "2026-09-24T04:00:00+00:00",
        "lines": [
            {"material_code": "MT-AISLADOR-PIN", "quantity": 6, "unit": "u"},
            {"material_code": "MT-FUSIBLE-10K", "quantity": 12, "unit": "u"},
        ],
    },
]

#: What the platform booked, so a test can assert the round trip.
CONSUMPTION: list[dict] = []
RETURNS: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        if parsed.path == "/health":
            self._send({"status": "ok"})
        elif parsed.path == "/materials":
            # `complete` says the batch is the whole list. Without it the platform must not retire
            # anything, and `?partial=1` is how that gets exercised.
            partial = query.get("partial", ["0"])[0] == "1"
            self._send(
                {
                    "items": MATERIALS[:2] if partial else MATERIALS,
                    "complete": not partial,
                    "generated_at": datetime.now(UTC).isoformat(),
                }
            )
        elif parsed.path == "/stock":
            self._send({"locations": LOCATIONS})
        elif parsed.path == "/movements":
            self._send({"consumption": CONSUMPTION, "returns": RETURNS})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        path = urlparse(self.path).path
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send({"error": "invalid json"}, 400)
            return
        if path == "/movements/consumption":
            CONSUMPTION.append(payload)
            self._send({"accepted": True, "lines": len(payload.get("lines") or [])})
            return
        if path == "/movements/return":
            RETURNS.append(payload)
            self._send({"accepted": True, "lines": len(payload.get("lines") or [])})
            return
        self._send({"error": "not found"}, 404)

    def log_message(self, fmt: str, *args: object) -> None:
        return


if __name__ == "__main__":
    print(f"erp-mock listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
