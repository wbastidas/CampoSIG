"""Minimal stand-in for an ArcGIS 10.8.1 feature service (I0, tools).

Enough for the backend's contract tests to run without the corporate GIS, and — more
importantly — it reproduces the rejections the real service performs, so a bug in the
platform's write safety fails here rather than against production (ADR-001).

Standard library only: this is a fixture, not a product.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

PORT = 8181

# Fields the real geodatabase maintains itself. Writing them is refused here exactly as
# the platform's own guards refuse them, so the mock cannot mask a regression.
CONNECTIVITY_FIELDS = {
    "ANCILLARYROLE",
    "ENABLED",
    "ELECTRICTRACEWEIGHT",
    "CIRCUITSOURCEGUID",
    "PARENTCIRCUITSOURCEGUID",
}

SERVICE_INFO = {
    "currentVersion": 10.81,
    "serviceDescription": "Mock Electric feature service",
    "hasVersionedData": True,
    "supportsDisconnectedEditing": False,
    "syncEnabled": False,
    "layers": [
        {"id": 0, "name": "support_structure_mock", "geometryType": "esriGeometryPoint"},
        {"id": 1, "name": "network_class_mock", "geometryType": "esriGeometryPoint"},
    ],
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path.rstrip("/").endswith("FeatureServer"):
            self._send(SERVICE_INFO)
        elif path == "/health":
            self._send({"status": "ok"})
        else:
            self._send({"error": {"code": 404, "message": "not found"}}, 404)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        form = parse_qs(raw)
        path = urlparse(self.path).path

        if path.endswith("applyEdits"):
            try:
                adds = json.loads(form.get("adds", ["[]"])[0])
            except json.JSONDecodeError:
                self._send({"error": {"code": 400, "message": "invalid adds payload"}}, 400)
                return
            for feature in adds:
                attributes = feature.get("attributes", {})
                offending = sorted(
                    k for k in attributes if k.upper() in CONNECTIVITY_FIELDS
                )
                if offending:
                    self._send(
                        {
                            "error": {
                                "code": 400,
                                "message": (
                                    "Connectivity fields are maintained by the geometric "
                                    "network and cannot be set: " + ", ".join(offending)
                                ),
                            }
                        },
                        400,
                    )
                    return
            self._send({"addResults": [{"success": True} for _ in adds]})
            return

        if path.endswith("createReplica"):
            # The real service refuses sync unless the data is prepared for it. Saying so
            # keeps the platform honest about which route is actually available (H1, H3).
            self._send(
                {
                    "error": {
                        "code": 400,
                        "message": (
                            "Sync is not enabled on this service. Global IDs and archiving "
                            "are required (finding H3)."
                        ),
                    }
                },
                400,
            )
            return

        self._send({"error": {"code": 404, "message": "not found"}}, 404)

    def log_message(self, fmt: str, *args: object) -> None:
        return  # quiet by default


if __name__ == "__main__":
    print(f"arcgis-mock listening on :{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
