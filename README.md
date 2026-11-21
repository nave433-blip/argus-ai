# ARGUS-AI v0.5

A document/research intelligence platform for Evan's own documents and
public sources: ingest → chunk → embed → hybrid search, entity
extraction into a knowledge graph, transparent classification + risk
scoring, Graph RAG question answering, orchestrated by five agents.
Manifest: `argus_manifest.json`.

## Architecture

```
data/inbox ──> SCOUT (discovery) ──> pipeline ──> SQLite store (default)
                                   ├─ chunks + embeddings (hashing, or Ollama)
                                   ├─ ATLAS  -> entities + co-occurrence graph
                                   └─ GUARDIAN -> classification + risk + policy flags
ORACLE  -> hybrid search (BM25 + cosine, fused)
        -> Graph RAG ask(): chunks + 1-hop graph neighbors -> answer
           (Ollama generative when a server is up, extractive otherwise)
NEXUS   -> routes tasks {ingest, search, ask, graph, assess} to agents
Workers -> SQLite job queue (argus/jobs.py): `argus worker` processes
           ingest jobs; multiple workers claim jobs atomically
Go crawler (go/) -> polite concurrent fetcher -> queue.jsonl -> Python ingest
API -> FastAPI app, or stdlib http.server fallback with the same routes
Dashboard -> static page at /dashboard (stats, search, ask, risk list)
Adapters -> Qdrant / Neo4j / OpenSearch real clients, on when configured
```

## Agents

| Agent | Role |
|---|---|
| SCOUT | Discovery: inbox scan + polite public-web fetch (robots respected, ≥1s delay, clearnet public pages only) |
| ORACLE | Hybrid search + Graph RAG Q&A (Ollama generative w/ extractive fallback) |
| ATLAS | Knowledge-graph builder: entities, relations, neighbors, JSON export |
| GUARDIAN | Risk scoring (explained signals) + ingestion policy flags |
| NEXUS | Orchestrator: routes every task to the right agent(s) |

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m argus.cli demo            # end-to-end demo -> DEMO_OUTPUT.md
.venv/bin/python -m argus.cli ingest          # ingest data/inbox into argus.db
.venv/bin/python -m argus.cli search "bitcoin treasury policy"
.venv/bin/python -m argus.cli ask "who met about the bitcoin treasury policy?"
.venv/bin/python -m argus.cli graph           # knowledge graph JSON
.venv/bin/python -m argus.cli serve --port 8077   # API + dashboard at /dashboard
.venv/bin/python -m pytest tests/ -q          # test suite (29 tests)
```

Workers (distributed, local form):

```bash
.venv/bin/python -m argus.cli enqueue-ingest --inbox data/inbox
.venv/bin/python -m argus.cli worker --id w1 --max-jobs 5   # run several in parallel
.venv/bin/python -m argus.cli queue-stats
```

The Go crawler fits upstream of the workers: it fetches known seed URLs
politely into `queue.jsonl`; fetched pages land in an inbox, and an
ingest job (above) processes them into the store.

```bash
cd go && ~/go-dist/go/bin/go build ./...      # compiles the module
./go-crawler -input urls.txt -output ../queue.jsonl
```

Docker (config provided; not executed in the dev env — no Docker there):

```bash
docker compose up -d        # app + qdrant + neo4j + opensearch
```

## Configuration (environment)

| Variable | Purpose |
|---|---|
| `ARGUS_OLLAMA_URL` / `ARGUS_OLLAMA_MODEL` / `ARGUS_OLLAMA_EMBED_MODEL` | Local LLM + embeddings for ORACLE (default http://localhost:11434, llama3.1, nomic-embed-text) |
| `ARGUS_QDRANT_URL` | Activate the Qdrant vector adapter |
| `ARGUS_NEO4J_URL` / `ARGUS_NEO4J_USER` / `ARGUS_NEO4J_PASSWORD` | Activate the Neo4j graph adapter |
| `ARGUS_OPENSEARCH_URL` | Activate the OpenSearch index adapter |
| `ARGUS_CONFIG_KEY` | AES-128-GCM key for ARGUS's own encrypted config (`argus/config_crypto.py`) |

## Features — honest status

**Working now (verified by 29 passing tests + live demo):** document
ingestion (.txt/.md, PDF text-layer via a pluggable extractor), media
ingestion with real stdlib metadata (PNG/JPEG/GIF dimensions, WAV
duration/channels, size + SHA-256 for all media), overlapping chunking,
deterministic local embeddings behind an `Embedder` interface, Ollama
embeddings + generation clients (mock-tested; extractive fallback when
no server), SQLite storage, hybrid keyword+semantic search, Graph RAG
(retrieval + 1-hop graph expansion + cited extractive synthesis),
knowledge graph, rule-based entity extraction, classification +
explained risk scoring, AES-128-GCM encrypted config, all five agents,
CLI + API, dashboard at /dashboard, SQLite job queue + worker CLI,
Go crawler/scheduler/worker-pool, Dockerfile + docker-compose + CI.

**Code-complete, NOT live-verified (no servers in the dev env):**
Qdrant / Neo4j / OpenSearch adapters — full clients, unit-tested with a
mocked HTTP layer, activated by env config with SQLite fallback. The
docker-compose stack that would run them is validated as config only;
Docker is not installed in the dev environment. Ollama likewise: no
Ollama server runs in the dev environment (checked: connection refused,
no binary), so generative answers are mock-tested and the extractive
Graph RAG path is what the demo exercises.

**Still genuinely open:** media transcription/OCR and scanned-PDF OCR
(extractor slots, labeled as such), a neural embedding model drop-in
(sentence-transformers behind the same interface), multi-host worker
deployment (the queue is single-host SQLite by design in v0.5). See
PLACEHOLDERS.md.

## Scope

ARGUS works on Evan's own documents and public sources. SCOUT and the Go
crawler fetch public clearnet pages politely with robots.txt respect,
from known seeds, following links. There is no URL-generation /
enumeration-for-unknown-targets component, no dark-web/Tor, no
login/paywall bypass, no access-control evasion — by design.
