"""End-to-end pipeline: inbox -> documents -> chunks -> embeddings ->
SQLite -> entities/graph -> classification + risk, in one call."""
from __future__ import annotations

from pathlib import Path

from .chunking import chunk_text
from .classify import classify, risk_score
from .embeddings import Embedder, HashingEmbedder
from .entities import cooccurrence_relations, extract_entities
from .ingest import ingest_inbox
from .store import Store


def run_pipeline(inbox: str | Path, store: Store,
                 embedder: Embedder | None = None) -> list[dict]:
    embedder = embedder or HashingEmbedder()
    report = []
    for doc in ingest_inbox(Path(inbox)):
        store.add_document(doc)
        chunks = chunk_text(doc.doc_id, doc.text) if doc.text else []
        for ch in chunks:
            store.add_chunk(ch, embedder.embed(ch.text))
        entities = extract_entities(doc.text) if doc.text else []
        for e in entities:
            store.add_entity(doc.doc_id, e["type"], e["value"])
        for src, dst, rel in cooccurrence_relations(entities):
            store.add_relation(src, dst, rel, doc.doc_id)
        cls = classify(doc.text)
        risk = risk_score(doc.text)
        report.append({
            "doc_id": doc.doc_id, "kind": doc.kind, "chunks": len(chunks),
            "entities": entities, "classification": cls, "risk": risk,
        })
    return report
