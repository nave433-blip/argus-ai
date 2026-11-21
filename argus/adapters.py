"""External storage adapters — REAL clients (v0.5), optional by config.

SQLite (argus/store.py) stays the default working store. These adapters
are full client implementations that activate only when configured:

  QdrantAdapter     Qdrant REST API          ARGUS_QDRANT_URL
  Neo4jAdapter      Neo4j transactional HTTP ARGUS_NEO4J_URL (+USER/PASSWORD)
  OpenSearchAdapter OpenSearch REST API      ARGUS_OPENSEARCH_URL

Factories (get_vector_store / get_graph_store / get_search_index) return
a live adapter only if the env var is set AND the server answers a ping;
otherwise they return None and callers fall back to the SQLite built-ins.
Honest status: code-complete and unit-tested with a mocked HTTP layer;
no Qdrant/Neo4j/OpenSearch server runs in the dev environment, so no
live-server verification is claimed. Run them via docker-compose.yml.

Only stdlib HTTP is used (urllib) — no optional packages required. The
transport (`opener`) is injectable for testing.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from typing import Callable, Optional

# opener(url, data|None, headers, timeout) -> (status, body_bytes)
Opener = Callable[[str, Optional[bytes], dict, float], tuple[int, bytes]]


def _default_opener(url: str, data: Optional[bytes], headers: dict,
                    timeout: float) -> tuple[int, bytes]:
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class _RestClient:
    def __init__(self, base_url: str, opener: Opener | None = None,
                 timeout: float = 10.0, extra_headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self._open = opener or _default_opener
        self.timeout = timeout
        self._headers = {"Content-Type": "application/json", **(extra_headers or {})}

    def request(self, method: str, path: str, payload: dict | None = None,
                ok: tuple[int, ...] = (200,)) -> dict:
        data = json.dumps(payload).encode() if payload is not None else None
        if method in ("PUT", "DELETE"):
            # urllib opener shim: encode method via a marker header path —
            # the default opener uses data presence; for PUT/DELETE we use
            # a direct Request here instead of the injectable shim.
            if self._open is _default_opener:
                return self._request_direct(method, path, data, ok)
        status, body = self._open(self.base_url + path, data,
                                  dict(self._headers), self.timeout)
        if status not in ok:
            raise RuntimeError(f"{method} {path} -> HTTP {status}: {body[:200]!r}")
        return json.loads(body.decode("utf-8")) if body else {}

    def _request_direct(self, method: str, path: str, data: bytes | None,
                        ok: tuple[int, ...]) -> dict:
        req = urllib.request.Request(self.base_url + path, data=data,
                                     headers=self._headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body, status = resp.read(), resp.status
        except urllib.error.HTTPError as exc:
            body, status = exc.read(), exc.code
        if status not in ok:
            raise RuntimeError(f"{method} {path} -> HTTP {status}: {body[:200]!r}")
        return json.loads(body.decode("utf-8")) if body else {}

    def ping(self) -> bool:
        try:
            self.request("GET", "/")
            return True
        except Exception:  # noqa: BLE001
            return False


class QdrantAdapter(_RestClient):
    """Vector store via the Qdrant REST API."""

    def __init__(self, url: str = "http://localhost:6333",
                 collection: str = "argus_chunks", opener: Opener | None = None):
        super().__init__(url, opener=opener)
        self.collection = collection

    def ensure_collection(self, dim: int) -> None:
        self.request("PUT", f"/collections/{self.collection}",
                     {"vectors": {"size": dim, "distance": "Cosine"}},
                     ok=(200, 409))  # 409 = already exists on some versions

    def upsert(self, chunk_id: str, vector: list[float], payload: dict) -> None:
        self.request("PUT", f"/collections/{self.collection}/points", {
            "points": [{"id": abs(hash(chunk_id)) % (2 ** 63), "vector": vector,
                        "payload": {"chunk_id": chunk_id, **payload}}]})

    def search(self, vector: list[float], limit: int = 5) -> list[dict]:
        out = self.request("POST", f"/collections/{self.collection}/points/search",
                           {"vector": vector, "limit": limit, "with_payload": True})
        return [{"chunk_id": r.get("payload", {}).get("chunk_id"),
                 "score": r.get("score"),
                 "payload": r.get("payload", {})} for r in out.get("result", [])]


class Neo4jAdapter:
    """Knowledge graph via Neo4j's transactional HTTP endpoint.

    (Bolt needs a third-party driver; the HTTP transactional API is a
    first-class Neo4j interface and keeps ARGUS stdlib-only.)
    """

    def __init__(self, url: str = "http://localhost:7474", user: str = "neo4j",
                 password: str = "", database: str = "neo4j",
                 opener: Opener | None = None):
        self._client = _RestClient(url, opener=opener, extra_headers={
            "Authorization": "Basic " + base64.b64encode(
                f"{user}:{password}".encode()).decode()})
        self.database = database

    def _run(self, statement: str, parameters: dict | None = None) -> list[dict]:
        out = self._client.request(
            "POST", f"/db/{self.database}/tx/commit",
            {"statements": [{"statement": statement,
                             "parameters": parameters or {}}]})
        if out.get("errors"):
            raise RuntimeError(f"Neo4j error: {out['errors']}")
        rows = []
        for result in out.get("results", []):
            cols = result.get("columns", [])
            for row in result.get("data", []):
                rows.append(dict(zip(cols, row.get("row", []))))
        return rows

    def ping(self) -> bool:
        try:
            self._run("RETURN 1 AS ok")
            return True
        except Exception:  # noqa: BLE001
            return False

    def add_entity(self, etype: str, value: str) -> None:
        self._run("MERGE (e:Entity {value: $value}) SET e.type = $type",
                  {"value": value, "type": etype})

    def add_relation(self, src: str, dst: str, relation: str) -> None:
        rel = "".join(c if c.isalnum() else "_" for c in relation).upper() or "RELATED"
        self._run(
            f"MERGE (a:Entity {{value: $src}}) MERGE (b:Entity {{value: $dst}}) "
            f"MERGE (a)-[:{rel}]->(b)", {"src": src, "dst": dst})

    def neighbors(self, value: str) -> list[dict]:
        return self._run(
            "MATCH (e:Entity {value: $value})-[r]-(n:Entity) "
            "RETURN n.value AS neighbor, type(r) AS relation", {"value": value})


class OpenSearchAdapter(_RestClient):
    """Full-text index via the OpenSearch REST API."""

    def __init__(self, url: str = "http://localhost:9200", index: str = "argus_chunks",
                 opener: Opener | None = None):
        super().__init__(url, opener=opener)
        self.index = index

    def ensure_index(self) -> None:
        self.request("PUT", f"/{self.index}", {
            "mappings": {"properties": {
                "chunk_id": {"type": "keyword"}, "doc_id": {"type": "keyword"},
                "text": {"type": "text"}}}}, ok=(200, 400))

    def index_chunk(self, chunk_id: str, doc_id: str, text: str) -> None:
        self.request("PUT", f"/{self.index}/_doc/{abs(hash(chunk_id)) % (2 ** 63)}",
                     {"chunk_id": chunk_id, "doc_id": doc_id, "text": text})

    def search(self, query: str, limit: int = 5) -> list[dict]:
        out = self.request("POST", f"/{self.index}/_search", {
            "size": limit, "query": {"match": {"text": query}}})
        return [{"chunk_id": h["_source"].get("chunk_id"),
                 "doc_id": h["_source"].get("doc_id"),
                 "text": h["_source"].get("text"), "score": h.get("_score")}
                for h in out.get("hits", {}).get("hits", [])]


# -- factories: configured + reachable, else None (SQLite fallback) ------

def get_vector_store(opener: Opener | None = None) -> QdrantAdapter | None:
    url = os.environ.get("ARGUS_QDRANT_URL")
    if not url:
        return None
    adapter = QdrantAdapter(url, opener=opener)
    return adapter if adapter.ping() else None


def get_graph_store(opener: Opener | None = None) -> Neo4jAdapter | None:
    url = os.environ.get("ARGUS_NEO4J_URL")
    if not url:
        return None
    adapter = Neo4jAdapter(url, user=os.environ.get("ARGUS_NEO4J_USER", "neo4j"),
                           password=os.environ.get("ARGUS_NEO4J_PASSWORD", ""),
                           opener=opener)
    return adapter if adapter.ping() else None


def get_search_index(opener: Opener | None = None) -> OpenSearchAdapter | None:
    url = os.environ.get("ARGUS_OPENSEARCH_URL")
    if not url:
        return None
    adapter = OpenSearchAdapter(url, opener=opener)
    return adapter if adapter.ping() else None
