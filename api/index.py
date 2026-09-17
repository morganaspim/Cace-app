"""Minimal Vercel entrypoint for CACE Studio.

The desktop application remains in ``cace_studio.app``.  This module is
intentionally dependency-light so deploying the repository to Vercel does not
attempt to start the PySide6 desktop GUI or the formal qualification runner.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Small health/landing endpoint using only the Python standard library."""

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.rstrip("/") in {"", "/api", "/api/health"}:
            payload = {
                "service": "CACE Studio",
                "status": "ok",
                "surface": "vercel",
            }
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = json.dumps({"error": "not_found"}, indent=2).encode("utf-8")
        self.send_response(404)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
