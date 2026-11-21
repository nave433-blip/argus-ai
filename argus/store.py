"""Storage: SQLite is the working store. Qdrant/Neo4j are adapter
interfaces (see argus/adapters.py) — not wired in v0.4.

Tables: documents, chunks (embedding stored as a float32 blob), entities,
relations (knowledge graph edges).
"""
from __future__ import annotations

import array
import json
import sqlite3
from pathlib import Path

from .chunking import Chunk
from .ingest import Document


def _blob(vec: list[float]) -> bytes:
    return array.array("f", vec).tobytes()


def _unblob(b: bytes) -> list[float]:
    a = array.array("f")
    a.frombytes(b)
    return list(a)


class Store:
    def __init__(self, path: str | Path = "argus.db"):
        self.path = str(path)
        # check_same_thread=False: the FastAPI layer serves requests from
        # a threadpool; SQLite's serialized mode handles concurrency.
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS documents(
            doc_id TEXT PRIMARY KEY, source TEXT, kind TEXT,
            text TEXT, metadata TEXT);
        CREATE TABLE IF NOT EXISTS chunks(
            chunk_id TEXT PRIMARY KEY, doc_id TEXT, idx INTEGER,
            text TEXT, start_word INTEGER, end_word INTEGER,
            embedding BLOB, metadata TEXT);
        CREATE TABLE IF NOT EXISTS entities(
            doc_id TEXT, type TEXT, value TEXT,
            PRIMARY KEY(doc_id, type, value));
        CREATE TABLE IF NOT EXISTS relations(
            src TEXT, dst TEXT, relation TEXT, doc_id TEXT,
            weight INTEGER DEFAULT 1,
            PRIMARY KEY(src, dst, relation, doc_id));
        """)
        self.db.commit()

    # -- documents & chunks -------------------------------------------------
    def add_document(self, doc: Document) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?)",
            (doc.doc_id, doc.source, doc.kind, doc.text,
             json.dumps(doc.metadata)))
        self.db.commit()

    def add_chunk(self, chunk: Chunk, embedding: list[float]) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO chunks VALUES (?,?,?,?,?,?,?,?)",
            (chunk.chunk_id, chunk.doc_id, chunk.index, chunk.text,
             chunk.start_word, chunk.end_word, _blob(embedding),
             json.dumps(chunk.metadata)))
        self.db.commit()

    def documents(self) -> list[dict]:
        return [dict(r) for r in self.db.execute(
            "SELECT doc_id, source, kind, text, metadata FROM documents")]

    def chunks(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT chunk_id, doc_id, idx, text, embedding FROM chunks").fetchall()
        return [{"chunk_id": r["chunk_id"], "doc_id": r["doc_id"],
                 "index": r["idx"], "text": r["text"],
                 "embedding": _unblob(r["embedding"])} for r in rows]

    # -- knowledge graph ------------------------------------------------------
    def add_entity(self, doc_id: str, etype: str, value: str) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO entities VALUES (?,?,?)",
            (doc_id, etype, value))
        self.db.commit()

    def add_relation(self, src: str, dst: str, relation: str, doc_id: str) -> None:
        self.db.execute(
            "INSERT INTO relations VALUES (?,?,?,?,1) "
            "ON CONFLICT(src,dst,relation,doc_id) DO UPDATE SET weight=weight+1",
            (src, dst, relation, doc_id))
        self.db.commit()

    def entities(self, doc_id: str | None = None) -> list[dict]:
        if doc_id:
            rows = self.db.execute(
                "SELECT * FROM entities WHERE doc_id=?", (doc_id,))
        else:
            rows = self.db.execute("SELECT * FROM entities")
        return [dict(r) for r in rows]

    def relations(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM relations")]

    def export_graph(self) -> dict:
        nodes = sorted({e["value"] for e in self.entities()} |
                       {r["src"] for r in self.relations()} |
                       {r["dst"] for r in self.relations()})
        return {"nodes": nodes, "entities": self.entities(),
                "relations": self.relations()}

    def close(self) -> None:
        self.db.close()
