"""ATLAS — knowledge graph builder: entities + co-occurrence relations
into the store, graph queries, and JSON export."""
from __future__ import annotations

from ..entities import cooccurrence_relations, extract_entities
from ..store import Store


class Atlas:
    def __init__(self, store: Store):
        self.store = store

    def build_for_document(self, doc_id: str, text: str) -> list[dict]:
        entities = extract_entities(text)
        for e in entities:
            self.store.add_entity(doc_id, e["type"], e["value"])
        for src, dst, rel in cooccurrence_relations(entities):
            self.store.add_relation(src, dst, rel, doc_id)
        return entities

    def neighbors(self, entity_value: str) -> list[dict]:
        return [r for r in self.store.relations()
                if r["src"] == entity_value or r["dst"] == entity_value]

    def export(self) -> dict:
        return self.store.export_graph()
