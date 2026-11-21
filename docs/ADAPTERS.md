# Storage adapters

- **SQLite (default, always working)**: `argus/store.py` — documents,
  chunks, embeddings (float32 blobs), entities, relations, assessments.
  Zero setup, single file, WAL mode for concurrent workers. This is the
  fallback and system of record.
- **Qdrant (real client, v0.5)**: `argus/adapters.py::QdrantAdapter` —
  full REST implementation: `ensure_collection`, `upsert`, `search`.
  Activates when `ARGUS_QDRANT_URL` is set AND the server answers a
  ping (`adapters.get_vector_store()`); otherwise the factory returns
  None and hybrid search stays on SQLite.
- **Neo4j (real client, v0.5)**: `argus/adapters.py::Neo4jAdapter` —
  Cypher over Neo4j's transactional HTTP endpoint (stdlib-only, no Bolt
  driver needed): `add_entity`, `add_relation`, `neighbors`. Activates
  via `ARGUS_NEO4J_URL` (+ `ARGUS_NEO4J_USER` / `ARGUS_NEO4J_PASSWORD`)
  through `adapters.get_graph_store()`; SQLite graph is the fallback.
- **OpenSearch (real client, v0.5)**: `argus/adapters.py::OpenSearchAdapter`
  — REST `ensure_index`, `index_chunk`, `search` (match query).
  Activates via `ARGUS_OPENSEARCH_URL` through
  `adapters.get_search_index()`; SQLite + BM25 is the fallback.

## Honest status

All three adapters are **code-complete and unit-tested against a mocked
HTTP layer** (tests/test_v05.py). **No Qdrant, Neo4j, or OpenSearch
server runs in the current dev environment, so no live-server
verification is claimed.** To run them for real:

```bash
docker compose up -d qdrant neo4j opensearch
# then uncomment the ARGUS_*_URL lines in docker-compose.yml's app
# service (or export them) and restart the app
```

Docker itself is not installed in the dev environment either, so the
compose stack has been validated as YAML/config only — not executed.
