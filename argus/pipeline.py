"""End-to-end pipeline: inbox -> documents -> chunks -> embeddings ->
SQLite -> entities/graph -> classification + risk, in one call."""
from __future__ import annotations

from pathlib import Path

from .chunking import chunk_text
from .classify import classify, risk_score
from .embeddings import Embedder, HashingEmbedder
from .entities import cooccurrence_relations, extract_entities
from .ingest import ingest_inbox
from .keywords import KeywordEngine
from .store import Store

_engine: KeywordEngine | None = None


def _keyword_engine() -> KeywordEngine:
    global _engine
    if _engine is None:
        _engine = KeywordEngine()
    return _engine


def run_pipeline(inbox: str | Path, store: Store,
                 embedder: Embedder | None = None,
                 keyword_engine: KeywordEngine | None = None) -> list[dict]:
    embedder = embedder or HashingEmbedder()
    keyword_engine = keyword_engine or _keyword_engine()
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
        # HOT KEYWORDS: matches become HOT_KEYWORD entities in the graph
        # and hot metadata on the stored document. A relevance signal —
        # GUARDIAN does NOT treat hot hits as risk.
        kw = keyword_engine.score_text(doc.text) if doc.text else {
            "score": 0.0, "hot": False, "matches": []}
        for keyword in sorted({m["keyword"] for m in kw["matches"]}):
            store.add_entity(doc.doc_id, "HOT_KEYWORD", keyword)
        if kw["matches"]:
            doc.metadata["hot_keywords"] = kw["matches"]
            doc.metadata["keyword_score"] = kw["score"]
            doc.metadata["hot"] = kw["hot"]
            store.add_document(doc)  # re-store with hot metadata merged
        cls = classify(doc.text)
        risk = risk_score(doc.text)
        store.add_assessment(doc.doc_id, cls, risk)
        report.append({
            "doc_id": doc.doc_id, "kind": doc.kind, "chunks": len(chunks),
            "entities": entities, "classification": cls, "risk": risk,
            "hot": kw["hot"], "keyword_score": kw["score"],
            "keyword_matches": kw["matches"],
        })
    return report
