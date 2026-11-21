"""API layer: FastAPI app when fastapi is installed; otherwise a stdlib
http.server fallback exposing the same routes. Import-safe either way.

Routes: GET /health, GET /dashboard (static HTML), GET /stats,
POST /ingest {inbox}, GET /search?q=, GET /ask?q=, GET /graph,
POST /assess {text}.
"""
from __future__ import annotations

import json
from pathlib import Path

from .agents.nexus import Nexus
from .dashboard import DASHBOARD_HTML
from .store import Store

DB_PATH = "argus.db"
INBOX = "data/inbox"
VERSION = "0.5"


def make_nexus() -> Nexus:
    return Nexus(Store(DB_PATH))


def stats_payload(nexus: Nexus) -> dict:
    stats = nexus.store.stats()
    stats["version"] = VERSION
    return stats


try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel

    app = FastAPI(title="ARGUS-AI", version=VERSION)
    _nexus = make_nexus()

    class IngestBody(BaseModel):
        inbox: str = INBOX

    class AssessBody(BaseModel):
        text: str

    @app.get("/health")
    def health():
        return {"ok": True, "version": VERSION, "engine": "fastapi"}

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        return DASHBOARD_HTML

    @app.get("/stats")
    def stats():
        return stats_payload(_nexus)

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

            def _send_html(self, html: str):
                body = html.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                u = urlparse(self.path)
                qs = parse_qs(u.query)
                if u.path == "/health":
                    self._send({"ok": True, "version": VERSION, "engine": "stdlib"})
                elif u.path == "/dashboard":
                    self._send_html(DASHBOARD_HTML)
                elif u.path == "/stats":
                    self._send(stats_payload(nexus))
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
