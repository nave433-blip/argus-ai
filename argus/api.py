"""API layer: FastAPI app when fastapi is installed; otherwise a stdlib
http.server fallback exposing the same routes. Import-safe either way.

Routes: GET /health, POST /ingest {inbox}, GET /search?q=, GET /ask?q=,
GET /graph, POST /assess {text}.
"""
from __future__ import annotations

import json
from pathlib import Path

from .agents.nexus import Nexus
from .store import Store

DB_PATH = "argus.db"
INBOX = "data/inbox"


def make_nexus() -> Nexus:
    return Nexus(Store(DB_PATH))


try:
    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI(title="ARGUS-AI", version="0.4")
    _nexus = make_nexus()

    class IngestBody(BaseModel):
        inbox: str = INBOX

    class AssessBody(BaseModel):
        text: str

    @app.get("/health")
    def health():
        return {"ok": True, "version": "0.4", "engine": "fastapi"}

    @app.post("/ingest")
    def ingest(body: IngestBody):
        return _nexus.route({"type": "ingest", "inbox": body.inbox})

    @app.get("/search")
    def search(q: str, limit: int = 5):
        return _nexus.route({"type": "search", "query": q, "limit": limit})

    @app.get("/ask")
    def ask(q: str, limit: int = 5):
        return _nexus.route({"type": "ask", "question": q, "limit": limit})

    @app.get("/graph")
    def graph():
        return _nexus.route({"type": "graph"})

    @app.post("/assess")
    def assess(body: AssessBody):
        return _nexus.route({"type": "assess", "text": body.text})

    def serve(host: str = "127.0.0.1", port: int = 8077) -> None:
        import uvicorn
        uvicorn.run(app, host=host, port=port)

except ImportError:  # stdlib fallback — same routes, no dependencies
    app = None

    def serve(host: str = "127.0.0.1", port: int = 8077) -> None:
        from http.server import BaseHTTPRequestHandler, HTTPServer
        from urllib.parse import parse_qs, urlparse

        nexus = make_nexus()

        class Handler(BaseHTTPRequestHandler):
            def _send(self, obj, code=200):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                u = urlparse(self.path)
                qs = parse_qs(u.query)
                if u.path == "/health":
                    self._send({"ok": True, "version": "0.4", "engine": "stdlib"})
                elif u.path == "/search":
                    self._send(nexus.route({"type": "search", "query": qs.get("q", [""])[0]}))
                elif u.path == "/ask":
                    self._send(nexus.route({"type": "ask", "question": qs.get("q", [""])[0]}))
                elif u.path == "/graph":
                    self._send(nexus.route({"type": "graph"}))
                else:
                    self._send({"error": "not found"}, 404)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/ingest":
                    self._send(nexus.route({"type": "ingest", "inbox": body.get("inbox", INBOX)}))
                elif self.path == "/assess":
                    self._send(nexus.route({"type": "assess", "text": body.get("text", "")}))
                else:
                    self._send({"error": "not found"}, 404)

            def log_message(self, *a):  # quiet
                pass

        HTTPServer((host, port), Handler).serve_forever()
