"""NEXUS — orchestrator: routes tasks to the other four agents.

Task types:
  ingest   -> SCOUT (discover) + pipeline + ATLAS (graph) + GUARDIAN (assess)
  search   -> ORACLE
  ask      -> ORACLE
  graph    -> ATLAS (export or neighbors)
  assess   -> GUARDIAN
"""
from __future__ import annotations

from pathlib import Path

from ..embeddings import HashingEmbedder
from ..pipeline import run_pipeline
from ..search import HybridSearch
from ..store import Store
from .atlas import Atlas
from .guardian import Guardian
from .oracle import Oracle
from .scout import discover_inbox


class Nexus:
    def __init__(self, store: Store, embedder=None, generator=None):
        self.store = store
        self.embedder = embedder or HashingEmbedder()
        self.atlas = Atlas(store)
        self.guardian = Guardian()
        self._generator = generator  # None -> ORACLE builds OllamaGenerator
        self._oracle: Oracle | None = None

    def _get_oracle(self) -> Oracle:
        if self._oracle is None:
            self._oracle = Oracle(HybridSearch(self.store, self.embedder),
                                  store=self.store, generator=self._generator)
        return self._oracle

    def route(self, task: dict) -> dict:
        ttype = task.get("type", "")
        if ttype == "ingest":
            inbox = task["inbox"]
            files = discover_inbox(inbox)
            report = run_pipeline(Path(inbox), self.store, self.embedder)
            self._oracle = None  # corpus changed; rebuild search lazily
            return {"agent": "SCOUT+ATLAS+GUARDIAN", "discovered": files,
                    "ingested": report}
        if ttype == "search":
            return {"agent": "ORACLE",
                    "results": self._get_oracle().search(task["query"], task.get("limit", 5))}
        if ttype == "ask":
            return {"agent": "ORACLE",
                    "result": self._get_oracle().ask(task["question"], task.get("limit", 5))}
        if ttype == "graph":
            if task.get("entity"):
                return {"agent": "ATLAS", "neighbors": self.atlas.neighbors(task["entity"])}
            return {"agent": "ATLAS", "graph": self.atlas.export()}
        if ttype == "assess":
            return {"agent": "GUARDIAN",
                    "assessment": self.guardian.assess(task.get("text", ""), task.get("kind", "text"))}
        return {"agent": "NEXUS", "error": f"unknown task type: {ttype!r}",
                "known": ["ingest", "search", "ask", "graph", "assess"]}
