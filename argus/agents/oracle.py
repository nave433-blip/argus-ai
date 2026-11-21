"""ORACLE — search + Graph RAG Q&A over the corpus.

ask() is Graph RAG (v0.5):
  1. Hybrid search retrieves the top chunks for the question.
  2. Entities from those chunks' documents are expanded 1 hop through
     the knowledge graph (ATLAS relations) — connected entities and the
     documents they came from become extra grounded context.
  3. Answer composition:
     * If an Ollama server is reachable (argus.ollama.OllamaGenerator),
       the LLM gets a prompt assembled ONLY from the retrieved chunks +
       graph context, with chunk-id citations required.
     * Otherwise, an extractive synthesis: the answer is built from the
       top chunks' text with [chunk_id] citations inline, plus the
       graph-neighbor entities that connect them. No text is invented.
"""
from __future__ import annotations

from ..ollama import OllamaGenerator
from ..search import HybridSearch
from ..store import Store


class Oracle:
    def __init__(self, search: HybridSearch, store: Store | None = None,
                 generator: OllamaGenerator | None = None):
        self._search = search
        self._store = store
        self._generator = generator if generator is not None else OllamaGenerator()

    # -- graph context ----------------------------------------------------
    def _graph_context(self, hits: list[dict]) -> dict:
        """1-hop entity-graph expansion around the retrieved chunks."""
        if self._store is None or not hits:
            return {"entities": [], "neighbors": [], "related_docs": []}
        seed_entities: set[str] = set()
        for hit in hits:
            for e in self._store.entities(hit["doc_id"]):
                seed_entities.add(e["value"])
        # 1-hop adjacency: every entity sharing a relation with a seed
        # entity is a graph neighbor. `in_seed` marks neighbors that were
        # already in the retrieved documents vs genuinely new context.
        neighbors: list[dict] = []
        seen_pairs: set[tuple[str, str]] = set()
        for rel in self._store.relations():
            for seed, other in ((rel["src"], rel["dst"]), (rel["dst"], rel["src"])):
                if seed in seed_entities and other != seed:
                    key = (other, rel["doc_id"])
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        neighbors.append({"entity": other,
                                          "relation": rel["relation"],
                                          "via_doc": rel["doc_id"],
                                          "in_seed": other in seed_entities})
        related_docs = sorted({n["via_doc"] for n in neighbors})
        return {"entities": sorted(seed_entities),
                "neighbors": neighbors,
                "related_docs": related_docs}

    # -- answer composition -------------------------------------------------
    @staticmethod
    def _extractive_answer(question: str, hits: list[dict], graph: dict) -> str:
        if not hits:
            return "No relevant passages were found in the corpus for that question."
        parts = []
        for hit in hits[:3]:
            parts.append(f"{hit['text']} [{hit['chunk_id']}]")
        answer = " ".join(parts)
        if graph["neighbors"]:
            names = sorted({n["entity"] for n in graph["neighbors"]})[:8]
            answer += (" Connected entities from the knowledge graph: "
                       + ", ".join(names) + ".")
        return answer

    def _llm_answer(self, question: str, hits: list[dict], graph: dict) -> str | None:
        context = "\n".join(f"[{h['chunk_id']}] {h['text']}" for h in hits)
        graph_bits = ", ".join(sorted({n["entity"] for n in graph["neighbors"]})[:12])
        prompt = (
            "Answer the question using ONLY the context below. Cite the "
            "chunk ids (like [doc#c0]) that support each claim. If the "
            "context does not contain the answer, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Related entities from the knowledge graph: {graph_bits}\n\n"
            f"Question: {question}\nAnswer:")
        return self._generator.generate(prompt)

    # -- public API -----------------------------------------------------------
    def ask(self, question: str, limit: int = 5) -> dict:
        hits = self._search.search(question, limit=limit)
        graph = self._graph_context(hits)
        llm = self._llm_answer(question, hits, graph) if hits else None
        if llm:
            answer, mode = llm, "graph-rag+ollama (generative, grounded)"
        else:
            answer = self._extractive_answer(question, hits, graph)
            mode = "graph-rag (extractive synthesis, citations inline)"
        return {
            "question": question,
            "answer": answer,
            "mode": mode,
            "citations": [h["chunk_id"] for h in hits],
            "answer_chunks": hits,
            "graph_context": graph,
        }

    def search(self, query: str, limit: int = 5) -> list[dict]:
        return self._search.search(query, limit=limit)
