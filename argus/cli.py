"""CLI: python -m argus.cli <command>

Commands: ingest, search, ask, graph, assess, demo, serve, keygen,
          enqueue-ingest, worker, queue-stats
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .agents.nexus import Nexus
from .store import Store


def _nexus(db: str) -> Nexus:
    return Nexus(Store(db))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="argus")
    ap.add_argument("--db", default="argus.db")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest"); p.add_argument("--inbox", default="data/inbox")
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("--limit", type=int, default=5)
    p = sub.add_parser("ask"); p.add_argument("question"); p.add_argument("--limit", type=int, default=5)
    sub.add_parser("graph")
    p = sub.add_parser("assess"); p.add_argument("text")
    sub.add_parser("demo")
    sub.add_parser("keygen")
    p = sub.add_parser("serve"); p.add_argument("--port", type=int, default=8077)
    p = sub.add_parser("enqueue-ingest")
    p.add_argument("--inbox", default="data/inbox")
    p.add_argument("--queue", default="argus_jobs.db")
    p = sub.add_parser("worker")
    p.add_argument("--id", default="w1")
    p.add_argument("--queue", default="argus_jobs.db")
    p.add_argument("--once", action="store_true")
    p.add_argument("--max-jobs", type=int, default=None)
    p = sub.add_parser("queue-stats"); p.add_argument("--queue", default="argus_jobs.db")
    args = ap.parse_args(argv)

    if args.cmd == "keygen":
        from .config_crypto import generate_key
        print(generate_key())
        return 0
    if args.cmd == "serve":
        from .api import serve
        serve(port=args.port)
        return 0
    if args.cmd in ("enqueue-ingest", "worker", "queue-stats"):
        from .jobs import JobQueue, run_worker
        queue = JobQueue(args.queue)
        try:
            if args.cmd == "enqueue-ingest":
                job_id = queue.enqueue("ingest", {"inbox": args.inbox, "db": args.db})
                print(json.dumps({"enqueued": job_id, "queue": args.queue}))
            elif args.cmd == "worker":
                n = run_worker(queue, args.id, once=args.once, max_jobs=args.max_jobs)
                print(json.dumps({"worker": args.id, "processed": n,
                                  "stats": queue.stats()}))
            else:
                print(json.dumps(queue.stats()))
        finally:
            queue.close()
        return 0

    nexus = _nexus(args.db)
    if args.cmd == "ingest":
        out = nexus.route({"type": "ingest", "inbox": args.inbox})
    elif args.cmd == "search":
        out = nexus.route({"type": "search", "query": args.query, "limit": args.limit})
    elif args.cmd == "ask":
        out = nexus.route({"type": "ask", "question": args.question, "limit": args.limit})
    elif args.cmd == "graph":
        out = nexus.route({"type": "graph"})
    elif args.cmd == "assess":
        out = nexus.route({"type": "assess", "text": args.text})
    elif args.cmd == "demo":
        return run_demo(nexus)
    else:  # pragma: no cover
        return 2
    print(json.dumps(out, indent=2))
    return 0


def run_demo(nexus: Nexus) -> int:
    inbox = Path("data/inbox")
    lines = ["# ARGUS-AI Demo Output", ""]
    report = nexus.route({"type": "ingest", "inbox": str(inbox)})
    lines.append("## Ingest (SCOUT -> pipeline -> ATLAS + GUARDIAN)")
    for r in report["ingested"]:
        lines.append(f"- **{r['doc_id']}** ({r['kind']}): {r['chunks']} chunks, "
                     f"category={r['classification']['category']}, "
                     f"risk={r['risk']['score']} ({r['risk']['level']})")
        for e in r["entities"]:
            lines.append(f"  - entity: {e['type']}: {e['value']}")
    for query in ("bitcoin treasury policy", "court custody hearing documents"):
        res = nexus.route({"type": "search", "query": query, "limit": 3})
        lines.append(f"\n## Search: \"{query}\" (ORACLE, hybrid BM25 + semantic)")
        for hit in res["results"]:
            lines.append(f"- [{hit['score']}] {hit['doc_id']} :: {hit['text'][:110]}...")
    graph = nexus.route({"type": "graph"})["graph"]
    lines.append(f"\n## Knowledge graph (ATLAS): {len(graph['nodes'])} nodes, "
                 f"{len(graph['relations'])} relations")
    asked = nexus.route({"type": "ask",
                         "question": "who met about the bitcoin treasury policy and what was the budget?",
                         "limit": 3})["result"]
    lines.append("\n## Graph RAG ask (ORACLE: hybrid retrieval + 1-hop graph expansion)")
    lines.append(f"- mode: {asked['mode']}")
    lines.append(f"- answer: {asked['answer']}")
    lines.append(f"- citations: {', '.join(asked['citations'])}")
    lines.append(f"- graph entities in context: "
                 f"{', '.join(asked['graph_context']['entities'][:10])}")
    lines.append(f"- 1-hop neighbors: "
                 f"{', '.join(sorted({n['entity'] for n in asked['graph_context']['neighbors']})[:10])}")
    text = "\n".join(lines)
    Path("DEMO_OUTPUT.md").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
