"""Hybrid search: BM25 keyword score fused with cosine semantic score."""
from __future__ import annotations

import math
from collections import Counter

from .embeddings import Embedder, cosine, tokenize
from .store import Store


class BM25:
    def __init__(self, docs_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = docs_tokens
        self.n = len(docs_tokens) or 1
        self.avgdl = (sum(len(d) for d in docs_tokens) / self.n) if docs_tokens else 1.0
        self.df: Counter = Counter()
        for d in docs_tokens:
            for t in set(d):
                self.df[t] += 1

    def _idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        if not doc_tokens:
            return 0.0
        tf = Counter(doc_tokens)
        dl = len(doc_tokens)
        s = 0.0
        for t in query_tokens:
            f = tf.get(t, 0)
            if not f:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += self._idf(t) * (f * (self.k1 + 1) / denom)
        return s


class HybridSearch:
    """Fuse BM25 and semantic cosine with fixed weights (0.5/0.5 default).

    Scores are min-max normalized per query before fusion so neither side
    dominates purely because of scale.
    """

    def __init__(self, store: Store, embedder: Embedder,
                 w_keyword: float = 0.5, w_semantic: float = 0.5):
        self.store, self.embedder = store, embedder
        self.w_keyword, self.w_semantic = w_keyword, w_semantic
        self._chunks = store.chunks()
        self._bm25 = BM25([tokenize(c["text"]) for c in self._chunks])

    def refresh(self) -> None:
        self._chunks = self.store.chunks()
        self._bm25 = BM25([tokenize(c["text"]) for c in self._chunks])

    def search(self, query: str, limit: int = 5) -> list[dict]:
        if not self._chunks:
            return []
        q_tokens = tokenize(query)
        q_vec = self.embedder.embed(query)
        raw = []
        for c in self._chunks:
            kw = self._bm25.score(q_tokens, tokenize(c["text"]))
            sem = cosine(q_vec, c["embedding"])
            raw.append((c, kw, sem))
        kw_max = max((r[1] for r in raw), default=0.0) or 1.0
        sem_min = min((r[2] for r in raw), default=0.0)
        sem_max = max((r[2] for r in raw), default=0.0)
        sem_rng = (sem_max - sem_min) or 1.0
        results = []
        for c, kw, sem in raw:
            fused = (self.w_keyword * (kw / kw_max)
                     + self.w_semantic * ((sem - sem_min) / sem_rng))
            results.append({
                "chunk_id": c["chunk_id"], "doc_id": c["doc_id"],
                "text": c["text"], "score": round(fused, 4),
                "keyword_score": round(kw, 4), "semantic_score": round(sem, 4),
            })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]
