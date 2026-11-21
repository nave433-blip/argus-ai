# ARGUS-AI v0.4

A document/research intelligence platform for Evan's own documents and
public sources: ingest → chunk → embed → hybrid search, entity
extraction into a knowledge graph, transparent classification + risk
scoring, orchestrated by five agents. Manifest: `argus_manifest.json`.

## Architecture

```
data/inbox ──> SCOUT (discovery) ──> pipeline ──> SQLite store
                                   ├─ chunks + hashing embeddings
                                   ├─ ATLAS  -> entities + co-occurrence graph
                                   └─ GUARDIAN -> classification + risk + policy flags
ORACLE  -> hybrid search (BM25 + cosine, fused) / extractive Q&A
NEXUS   -> routes tasks {ingest, search, ask, graph, assess} to agents
Go crawler (go/) -> polite concurrent fetcher -> queue.jsonl -> Python ingest
API -> FastAPI app, or stdlib http.server fallback with the same routes
```

## Agents

| Agent | Role |
|---|---|
| SCOUT | Discovery: inbox scan + polite public-web fetch (robots respected, ≥1s delay, clearnet public pages only) |
| ORACLE | Semantic/hybrid search + extractive Q&A over the corpus |
| ATLAS | Knowledge-graph builder: entities, relations, neighbors, JSON export |
| GUARDIAN | Risk scoring (explained signals) + ingestion policy flags |
| NEXUS | Orchestrator: routes every task to the right agent(s) |

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m argus.cli demo            # end-to-end demo -> DEMO_OUTPUT.md
.venv/bin/python -m argus.cli ingest          # ingest data/inbox into argus.db
.venv/bin/python -m argus.cli search "bitcoin treasury policy"
.venv/bin/python -m argus.cli ask "what happened at the custody hearing?"
.venv/bin/python -m argus.cli graph           # knowledge graph JSON
.venv/bin/python -m argus.cli serve --port 8077   # API (FastAPI or stdlib fallback)
.venv/bin/python -m pytest tests/ -q          # test suite
```

Go crawler:

```bash
cd go && ~/go-dist/go/bin/go build ./...      # compiles the module
./go-crawler -input urls.txt -output ../queue.jsonl
```

## Features — honest status

**Working now:** document ingestion (.txt/.md, PDF text-layer via a
pluggable extractor), media registration (metadata only), overlapping
chunking, deterministic local embeddings (hashing/TF, behind an
`Embedder` interface), SQLite storage, hybrid keyword+semantic search,
knowledge graph (entities + co-occurrence, queryable, JSON export),
rule-based entity extraction (people, orgs, places, dates, money, crypto
addresses, emails, URLs), classification + explained risk scoring,
AES-128-GCM encrypted config for ARGUS's own settings
(`argus/config_crypto.py`), all five agents, CLI + API, Go
crawler/scheduler/worker-pool.

**Adapters-to-wire (interfaces only, clearly marked):** Qdrant vector
store and Neo4j graph store — see `docs/ADAPTERS.md`.

**Roadmap (from the manifest):** ollama_integration (generative Q&A in
ORACLE), graph_rag, dashboard, distributed_workers.

## Scope

ARGUS works on Evan's own documents and public sources. SCOUT and the Go
crawler fetch public clearnet pages politely with robots.txt respect.
No dark-web/Tor, no login/paywall bypass, no access-control evasion —
by design, not by omission.
