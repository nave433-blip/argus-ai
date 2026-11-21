# Storage adapters

- **SQLite (working)**: `argus/store.py` — documents, chunks, embeddings
  (float32 blobs), entities, relations. Zero setup, single file.
- **Qdrant (adapter-to-wire)**: `argus/adapters.py::QdrantAdapter` defines
  `upsert/search`. To wire: run Qdrant (Docker, port 6333), create the
  `argus_chunks` collection at the embedder's dimension (256 default),
  and swap `HybridSearch`'s chunk source. Interface only in v0.4.
- **Neo4j (adapter-to-wire)**: `argus/adapters.py::Neo4jAdapter` defines
  `add_entity/add_relation` for the graph_rag roadmap item. The SQLite
  relations table exports the same graph as JSON today
  (`python -m argus.cli graph`).
