"""ORACLE — semantic search / Q&A over the corpus.

v0.4 answers by retrieval: it returns the best-matching chunks with
scores (extractive Q&A). Generative answers via a local LLM are the
ollama_integration roadmap item; the interface (ask -> answer dict)
already matches what that will return.
"""
from __future__ import annotations

from ..search import HybridSearch


class Oracle:
    def __init__(self, search: HybridSearch):
        self._search = search

    def ask(self, question: str, limit: int = 5) -> dict:
        hits = self._search.search(question, limit=limit)
        return {
            "question": question,
            "answer_chunks": hits,
            "mode": "extractive-retrieval (generative LLM = roadmap: ollama_integration)",
        }

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return self._search.search(query, limit=limit)
