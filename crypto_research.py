"""ARGUS crypto research run — Phase 1 of the ARGUS -> Crypto Trend Bot
cross-project job (2026-11-21).

Uses ARGUS's own machinery only:
  * SCOUT (argus.agents.scout.fetch_public_page) — polite public fetcher:
    robots.txt respected, >=1s delay, plain User-Agent, GET only, no auth,
    no bot-wall circumvention. A 403/451 is an answer: recorded, not fought.
  * The standard pipeline (argus.pipeline.run_pipeline): ingest -> chunk ->
    embed -> entities -> knowledge graph -> classify/risk.

Outputs:
  * CRYPTO_RESEARCH.md (this repo) — human report.
  * data/crypto_research.db — the corpus store (gitignored, regenerable).
  * ../crypto-trend-bot/data/argus_insights.json — machine-readable export
    consumed by the crypto bot's bot/argus_feed.py.

Run:  python3 crypto_research.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from argus.agents.scout import fetch_public_page          # noqa: E402
from argus.pipeline import run_pipeline                    # noqa: E402
from argus.store import Store                              # noqa: E402

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "data" / "crypto_inbox"
DB_PATH = ROOT / "data" / "crypto_research.db"
REPORT_MD = ROOT / "CRYPTO_RESEARCH.md"
INSIGHTS_JSON = ROOT.parent / "crypto-trend-bot" / "data" / "argus_insights.json"

# Known, public seed pages only — no discovery-by-guessing, no hidden URLs.
SEEDS = [
    ("Binance US API docs", "https://docs.binance.us/"),
    ("Binance Vision (public data)", "https://data.binance.vision/"),
    ("Binance futures docs — funding rate history",
     "https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Get-Funding-Rate-History"),
    ("alternative.me Fear & Greed", "https://alternative.me/crypto/fear-and-greed-index/"),
    ("mempool.space", "https://mempool.space/"),
    ("mempool.space API docs", "https://mempool.space/docs/api/rest"),
    ("CoinDesk", "https://www.coindesk.com/"),
    ("CoinTelegraph", "https://cointelegraph.com/"),
    ("TradingView features", "https://www.tradingview.com/features/"),
    ("3Commas", "https://3commas.io/"),
    ("SEC — crypto assets topic", "https://www.sec.gov/securities-topics/crypto-assets"),
    ("CFTC — virtual currency risks",
     "https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/understand_risks_of_virtual_currency.html"),
    ("Kraken API docs", "https://docs.kraken.com/"),
    ("Coinbase developer docs", "https://docs.cdp.coinbase.com/"),
]

# Public API / data endpoint shapes worth surfacing from the fetched pages.
_ENDPOINT_RES = [
    re.compile(r"https?://[a-zA-Z0-9.\-]*api[a-zA-Z0-9.\-]*/[^\s\"'<>\)\]]+"),
    re.compile(r"https?://mempool\.space/api/[^\s\"'<>\)\]]+"),
    re.compile(r"(?<![\w/])/(?:fapi|api|derivatives/api)/v\d/[A-Za-z0-9_\-/]+"),
]
_TOPIC_LEXICON = [
    "Bitcoin", "Ethereum", "Solana", "Binance", "Kraken", "Coinbase",
    "funding rate", "open interest", "perpetual", "futures", "mempool",
    "fees", "Fear & Greed", "ETF", "stablecoin", "SEC", "CFTC",
    "liquidation", "order book", "API",
]


class _TextExtractor(HTMLParser):
    """Visible-text extraction: drops script/style, keeps block spacing."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    text = " ".join("".join(p.parts).split())
    # restore some paragraph structure for the chunker
    return text


def find_endpoints(raw_html: str, text: str, source_url: str) -> list[dict]:
    found = {}
    for blob in (raw_html, text):
        for rx in _ENDPOINT_RES:
            for m in rx.finditer(blob):
                ep = m.group(0).rstrip(".,;").split("&quot")[0].split("&#")[0]
                if len(ep) < 12 or ep in found:
                    continue
                lo = max(0, m.start() - 60)
                ctx = " ".join(blob[lo:m.end() + 60].split())[:140]
                found[ep] = {"endpoint": ep, "source_url": source_url,
                             "context": ctx}
    return list(found.values())


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")


FETCH_CACHE = ROOT / "data" / "crypto_fetch_cache.json"


def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    # Fetch results are cached (the fetch phase takes minutes of polite
    # delays); delete data/crypto_fetch_cache.json to force a refetch.
    if FETCH_CACHE.exists():
        cache = json.loads(FETCH_CACHE.read_text(encoding="utf-8"))
        sources, endpoints = cache["sources"], cache["endpoints"]
        print(f"[scout] reusing cached fetch results for {len(sources)} seeds "
              f"(delete {FETCH_CACHE.name} to refetch)", flush=True)
        return _pipeline_and_report(sources, endpoints)

    for old in INBOX.iterdir():
        if old.is_file():
            old.unlink()
    sources, endpoints = [], []
    for label, url in SEEDS:
        res = fetch_public_page(url)
        rec = {"label": label, "url": url, "ok": bool(res.get("ok"))}
        if res.get("ok"):
            html = res["text"]
            text = html_to_text(html)
            rec.update({"status": 200, "bytes": len(html),
                        "text_chars": len(text)})
            endpoints.extend(find_endpoints(html, text, url))
            (INBOX / f"{slug(label)}.md").write_text(
                f"# {label}\nSource: {url}\n\n{text}\n", encoding="utf-8")
        else:
            err = str(res.get("error", "unknown error"))
            m = re.search(r"HTTP Error (\d+)", err)
            rec.update({"status": int(m.group(1)) if m else None, "error": err})
        sources.append(rec)
        if rec["ok"]:
            outcome = "OK " + str(rec.get("text_chars")) + " chars"
        else:
            outcome = ("FAIL " + str(rec.get("status")) + " "
                       + str(rec.get("error"))[:80])
        print(f"[scout] {label}: {outcome}", flush=True)

    FETCH_CACHE.write_text(json.dumps(
        {"sources": sources, "endpoints": endpoints}, indent=2),
        encoding="utf-8")
    return _pipeline_and_report(sources, endpoints)


def _pipeline_and_report(sources, endpoints) -> int:
    store = Store(DB_PATH)
    # Batch-run performance knob: the pipeline commits per row; NORMAL
    # synchronous is the standard WAL pairing and far faster than FULL.
    # The corpus is regenerable research data, so this is safe here.
    store.db.execute("PRAGMA synchronous=NORMAL")
    report = run_pipeline(INBOX, store)
    stats = store.stats()
    graph = store.export_graph()

    # entity frequency across documents
    ent_counter: Counter = Counter()
    ent_types: dict[str, str] = {}
    for e in store.entities():
        ent_counter[e["value"]] += 1
        ent_types[e["value"]] = e["type"]
    top_entities = [{"value": v, "type": ent_types[v], "documents": n}
                    for v, n in ent_counter.most_common(40)]

    # topic mentions across the corpus text
    corpus = "\n".join(d["text"] or "" for d in store.documents())
    topics = [{"topic": t, "mentions": len(re.findall(re.escape(t), corpus, re.I))}
              for t in _TOPIC_LEXICON]
    topics = sorted([t for t in topics if t["mentions"] > 0],
                    key=lambda t: -t["mentions"])

    dedup_endpoints = list({e["endpoint"]: e for e in endpoints}.values())
    insights = {
        "generated_by": "ARGUS-AI crypto_research.py (SCOUT + pipeline)",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "sources": sources,
        "corpus": {"documents": stats["documents"], "chunks": stats["chunks"],
                   "entities": stats["entities"], "relations": stats["relations"],
                   "graph_nodes": len(graph["nodes"])},
        "top_entities": top_entities,
        "topics": topics,
        "endpoints": sorted(dedup_endpoints, key=lambda e: e["endpoint"]),
        "documents_detail": [
            {"doc_id": r["doc_id"], "chunks": r["chunks"],
             "entities": len(r["entities"]),
             "category": r["classification"]["category"],
             "risk_score": r["risk"]["score"], "risk_level": r["risk"]["level"]}
            for r in report],
    }
    INSIGHTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    INSIGHTS_JSON.write_text(json.dumps(insights, indent=2), encoding="utf-8")

    ok = [s for s in sources if s["ok"]]
    lines = [
        "# ARGUS Crypto Research — corpus for the Crypto Trend Bot", "",
        f"Generated: {insights['generated_at']}  ",
        "Method: ARGUS SCOUT (robots.txt respected, >=1s delay, plain client, "
        "GET only) fetched the known public seed pages below; the standard "
        "ARGUS pipeline (ingest -> chunk -> embed -> entities -> knowledge "
        "graph -> classify/risk) processed whatever was reachable. Failures "
        "(403/451/robots) are recorded as-is — no circumvention attempted.", "",
        "## Fetch results", "",
        "| Seed | URL | Result | Detail |",
        "|------|-----|--------|--------|",
    ]
    for s in sources:
        if s["ok"]:
            lines.append(f"| {s['label']} | {s['url']} | 200 OK | "
                         f"{s['text_chars']} chars of text |")
        else:
            lines.append(f"| {s['label']} | {s['url']} | FAILED "
                         f"({s.get('status') or 'n/a'}) | "
                         f"{str(s.get('error', ''))[:100]} |")
    lines += [
        "", "## Corpus stats", "",
        f"- Documents ingested: {stats['documents']} of {len(sources)} seeds",
        f"- Chunks: {stats['chunks']}",
        f"- Distinct entities: {stats['entities']}",
        f"- Knowledge graph: {len(graph['nodes'])} nodes, "
        f"{stats['relations']} relations", "",
        "## Top entities (by document frequency)", "",
    ]
    for e in top_entities[:20]:
        lines.append(f"- {e['value']} ({e['type']}) — {e['documents']} docs")
    lines += ["", "## Topic mentions", ""]
    for t in topics:
        lines.append(f"- {t['topic']}: {t['mentions']}")
    lines += ["", "## Public API / data endpoints mentioned in the pages", ""]
    if dedup_endpoints:
        for e in sorted(dedup_endpoints, key=lambda x: x["endpoint"]):
            lines.append(f"- `{e['endpoint']}` — from {e['source_url']}")
    else:
        lines.append("- None extracted.")
    lines += ["", "## Per-document classification / risk", ""]
    for d in insights["documents_detail"]:
        lines.append(f"- {d['doc_id']}: {d['chunks']} chunks, "
                     f"{d['entities']} entities, category={d['category']}, "
                     f"risk={d['risk_score']} ({d['risk_level']})")
    lines += ["",
              "Machine-readable export: `crypto-trend-bot/data/argus_insights.json` "
              "(consumed by bot/argus_feed.py).", ""]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[argus] corpus: {stats['documents']} docs, {stats['chunks']} chunks, "
          f"{stats['entities']} entities, {stats['relations']} relations")
    print(f"[argus] endpoints found: {len(dedup_endpoints)}")
    print(f"[argus] wrote {REPORT_MD} and {INSIGHTS_JSON}")
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
