"""Storage adapters-to-wire (NOT functional in v0.4 — honest stubs).

SQLite (argus/store.py) is the working store. These classes define the
interfaces a Qdrant vector store and a Neo4j graph store must satisfy so
they can be dropped in later without changing the pipeline. Every method
raises NotImplementedError on purpose: nothing here pretends to work.
"""
from __future__ import annotations


class QdrantAdapter:
    """Adapter-to-wire: vector search in Qdrant (roadmap)."""

    def __init__(self, url: str = "http://localhost:6333", collection: str = "argus_chunks"):
        self.url, self.collection = url, collection

    def upsert(self, chunk_id: str, vector: list[float], payload: dict) -> None:
        raise NotImplementedError("Qdrant adapter not wired in v0.4 — see docs/ADAPTERS.md")

    def search(self, vector: list[float], limit: int = 5) -> list[dict]:
        raise NotImplementedError("Qdrant adapter not wired in v0.4 — see docs/ADAPTERS.md")


class Neo4jAdapter:
    """Adapter-to-wire: knowledge graph in Neo4j (roadmap: graph_rag)."""

    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j"):
        self.uri, self.user = uri, user

    def add_entity(self, etype: str, value: str) -> None:
        raise NotImplementedError("Neo4j adapter not wired in v0.4 — see docs/ADAPTERS.md")

    def add_relation(self, src: str, dst: str, relation: str) -> None:
        raise NotImplementedError("Neo4j adapter not wired in v0.4 — see docs/ADAPTERS.md")
