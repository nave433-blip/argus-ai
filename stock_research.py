"""ARGUS stock research run — Phase 2 of the stocks-section job
(2026-11-21): web TRAINING CONTEXT for the crypto-trend-bot stocks
engine.

Uses ARGUS's own machinery only:
  * SCOUT (argus.agents.scout.fetch_public_page) — polite public
    fetcher: robots.txt respected, >=1s delay, plain User-Agent, GET
    only, no auth, no bot-wall circumvention. A 403/robots refusal is
    an answer: recorded in the table, not fought.
  * The standard pipeline (argus.pipeline.run_pipeline): ingest ->
    chunk -> embed -> entities -> knowledge graph -> classify/risk.
  * The stock hot-keyword engine (data/hot_keywords_stocks.json) —
    same fuzzy matching as the crypto list (misspellings, phonetic,
    encoded variants).

Per-ticker context: for every ticker on the crypto bot's wild
watchlist (data/wild_stocks.json in the stocks worktree), the corpus
is searched by ticker symbol (incl. $ cashtags) and company name;
documents mentioning a ticker are scored with the stock keyword
engine, and entities co-occurring in those documents are collected
from the knowledge-graph store.

Outputs:
  * STOCK_RESEARCH.md (this repo) — human report incl. the scrape
    table (fetched / refused, honestly).
  * data/stock_research.db — the corpus store (regenerable).
  * ../crypto-trend-bot-stocks/data/stock_insights.json — the export
    the stocks engine consumes as training context.

Run:  python3 stock_research.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from argus.agents.scout import fetch_public_page          # noqa: E402
from argus.keywords import KeywordEngine                   # noqa: E402
from argus.pipeline import run_pipeline                    # noqa: E402
from argus.store import Store                              # noqa: E402
from crypto_research import html_to_text, slug             # noqa: E402

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "data" / "stock_inbox"
DB_PATH = ROOT / "data" / "stock_research.db"
REPORT_MD = ROOT / "STOCK_RESEARCH.md"
STOCKS_REPO = ROOT.parent / "crypto-trend-bot-stocks"
UNIVERSE_CSV = STOCKS_REPO / "data" / "stock_universe.csv"
WATCHLIST_JSON = STOCKS_REPO / "data" / "wild_stocks.json"
INSIGHTS_JSON = STOCKS_REPO / "data" / "stock_insights.json"
FETCH_CACHE = ROOT / "data" / "stock_fetch_cache.json"

# Known, public seed pages only — no discovery-by-guessing.
SEEDS = [
    ("CNBC markets", "https://www.cnbc.com/markets/"),
    ("MarketWatch", "https://www.marketwatch.com/"),
    ("Nasdaq articles", "https://www.nasdaq.com/articles"),
    ("Nasdaq earnings calendar",
     "https://www.nasdaq.com/market-activity/earnings"),
    ("Investing.com news", "https://www.investing.com/news/"),
    ("Seeking Alpha market news", "https://seekingalpha.com/market-news"),
    ("SEC EDGAR full-text search", "https://www.sec.gov/edgar/search/"),
    ("SEC EDGAR company filings browse",
     "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K"),
    ("Stooq news", "https://stooq.com/news/"),
    ("Yahoo Finance news", "https://finance.yahoo.com/news/"),
]


def _fetch_bounded(url: str, seconds: int = 45) -> dict:
    """fetch_public_page with a hard wall-clock bound (SIGALRM). Some
    hosts tarpit plain clients inside the robots or page read where
    SCOUT has no socket timeout; a bounded failure is recorded honestly
    instead of hanging the run."""
    import signal

    def _boom(signum, frame):
        raise TimeoutError(f"fetch exceeded {seconds}s")

    old = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fetch_public_page(url)
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "ok": False,
                "error": f"bounded fetch failed: {exc}"}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _robots_reachable(url: str) -> bool:
    """Timed pre-flight for a seed's robots.txt. SCOUT's RobotFileParser
    read has no socket timeout, and some hosts (nasdaq.com, observed
    2026-11-21) hang the robots request indefinitely. SCOUT's own
    policy is 'robots unreadable -> skip', so a timed-out robots fetch
    is recorded as a skip here instead of hanging the whole run. An
    HTTP error status still counts as reachable: the server answered,
    and SCOUT applies its normal robots rules to it."""
    import urllib.error
    import urllib.parse
    import urllib.request
    robots = urllib.parse.urljoin(url, "/robots.txt")
    try:
        req = urllib.request.Request(robots,
                                     headers={"User-Agent": "ARGUS"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read(512)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


def load_universe():
    import csv
    with open(UNIVERSE_CSV, newline="") as f:
        return {r["Symbol"].strip(): r["Security"].strip()
                for r in csv.DictReader(f)}


def main() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    if FETCH_CACHE.exists():
        cache = json.loads(FETCH_CACHE.read_text(encoding="utf-8"))
        sources = cache["sources"]
        print(f"[scout] reusing cached fetch results for {len(sources)} "
              f"seeds (delete {FETCH_CACHE.name} to refetch)", flush=True)
    else:
        for old in INBOX.iterdir():
            if old.is_file():
                old.unlink()
        sources = []
        for label, url in SEEDS:
            if not _robots_reachable(url):
                rec = {"label": label, "url": url, "ok": False,
                       "status": None,
                       "error": "robots.txt fetch timed out — skipped "
                                "(SCOUT policy: unreadable robots = skip)"}
                sources.append(rec)
                print(f"[scout] {label}: FAIL robots timeout", flush=True)
                continue
            res = _fetch_bounded(url)
            rec = {"label": label, "url": url, "ok": bool(res.get("ok"))}
            if res.get("ok"):
                text = html_to_text(res["text"])
                rec.update({"status": 200, "bytes": len(res["text"]),
                            "text_chars": len(text)})
                (INBOX / f"{slug(label)}.md").write_text(
                    f"# {label}\nSource: {url}\n\n{text}\n",
                    encoding="utf-8")
            else:
                err = str(res.get("error", "unknown error"))
                m = re.search(r"HTTP Error (\d+)", err)
                rec.update({"status": int(m.group(1)) if m else None,
                            "error": err})
            sources.append(rec)
            print(f"[scout] {label}: "
                  + (f"OK {rec.get('text_chars')} chars" if rec["ok"]
                     else f"FAIL {rec.get('status')} "
                          f"{str(rec.get('error'))[:80]}"), flush=True)
        # Phase B: per-ticker public news pages on the one host family
        # that allowed the seed fetch (Yahoo Finance) — one page per
        # wild-watchlist ticker, same SCOUT rules.
        if WATCHLIST_JSON.exists():
            tickers = [r["ticker"] for r in
                       json.loads(WATCHLIST_JSON.read_text())["watchlist"]]
            for ticker in tickers:
                url = f"https://finance.yahoo.com/quote/{ticker}/news/"
                label = f"Yahoo Finance — {ticker} news"
                if not _robots_reachable(url):
                    sources.append({"label": label, "url": url, "ok": False,
                                    "status": None,
                                    "error": "robots.txt fetch timed out — "
                                             "skipped"})
                    continue
                res = _fetch_bounded(url)
                rec = {"label": label, "url": url, "ok": bool(res.get("ok"))}
                if res.get("ok"):
                    text = html_to_text(res["text"])
                    rec.update({"status": 200, "bytes": len(res["text"]),
                                "text_chars": len(text)})
                    (INBOX / f"yahoo-{ticker.lower()}.md").write_text(
                        f"# {label}\nSource: {url}\n\n{text}\n",
                        encoding="utf-8")
                else:
                    err = str(res.get("error", "unknown error"))
                    m = re.search(r"HTTP Error (\d+)", err)
                    rec.update({"status": int(m.group(1)) if m else None,
                                "error": err})
                sources.append(rec)
                print(f"[scout] {label}: "
                      + (f"OK {rec.get('text_chars')} chars" if rec["ok"]
                         else f"FAIL {str(rec.get('error'))[:70]}"),
                      flush=True)
        FETCH_CACHE.write_text(json.dumps({"sources": sources}, indent=2),
                               encoding="utf-8")
    return _pipeline_and_export(sources)


def _pipeline_and_export(sources) -> int:
    store = Store(DB_PATH)
    store.db.execute("PRAGMA synchronous=NORMAL")
    run_pipeline(INBOX, store)
    stats = store.stats()
    docs = store.documents()
    doc_text = {d["doc_id"]: (d["text"] or "") for d in docs}
    doc_source = {d["doc_id"]: d["source"] for d in docs}
    entities_by_doc: dict[str, list[dict]] = {}
    for e in store.entities():
        entities_by_doc.setdefault(e["doc_id"], []).append(e)

    engine = KeywordEngine(path=ROOT / "data" / "hot_keywords_stocks.json")
    universe = load_universe()
    watchlist = []
    if WATCHLIST_JSON.exists():
        watchlist = [r["ticker"] for r in
                     json.loads(WATCHLIST_JSON.read_text())["watchlist"]]
    targets = watchlist or sorted(universe)[:50]

    tickers_out = {}
    for ticker in targets:
        name = universe.get(ticker, "")
        sym_rx = re.compile(rf"(?<![A-Z0-9])\$?{re.escape(ticker)}"
                            rf"(?![A-Z0-9])")
        name_rx = re.compile(re.escape(name.split(",")[0].strip()),
                             re.I) if name else None
        mention_count = 0
        source_docs = set()
        kw_counter: Counter = Counter()
        hot_score = 0.0
        related: Counter = Counter()
        for doc_id, text in doc_text.items():
            hits = len(sym_rx.findall(text))
            if name_rx:
                hits += len(name_rx.findall(text))
            if not hits:
                continue
            mention_count += hits
            source_docs.add(doc_source[doc_id])
            scored = engine.score_text(text)
            hot_score += scored["score"]
            for m in scored["matches"]:
                kw_counter[m["keyword"]] += 1
            for e in entities_by_doc.get(doc_id, []):
                if e["value"].upper() != ticker.upper() \
                        and e["value"] != name:
                    related[e["value"]] += 1
        tickers_out[ticker] = {
            "company": name,
            "mention_count": mention_count,
            "hot_keyword_score": round(hot_score, 2),
            "top_keywords": [k for k, _ in kw_counter.most_common(5)],
            "top_related_entities": [v for v, _ in related.most_common(8)],
            "source_count": len(source_docs),
            "sources": sorted(source_docs),
        }
    covered = sum(1 for v in tickers_out.values() if v["mention_count"] > 0)
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "as_of": time.strftime("%Y-%m-%d"),
        "generator": "ARGUS-AI stock_research.py (SCOUT + pipeline + "
                     "stock hot-keyword engine)",
        "sources": sources,
        "corpus": {"documents": stats["documents"],
                   "entities": stats["entities"],
                   "relations": stats["relations"]},
        "watchlist_size": len(targets),
        "tickers_with_context": covered,
        "tickers": tickers_out,
    }
    INSIGHTS_JSON.write_text(json.dumps(payload, indent=2),
                             encoding="utf-8")

    lines = ["# ARGUS Stock Research — web training context for the "
             "stocks engine", "",
             f"Generated: {payload['generated_at']}", "",
             "## Scrape table (SCOUT: robots respected, >=1s delays, "
             "no circumvention)", "",
             "| Source | URL | Result | Detail |",
             "|--------|-----|--------|--------|"]
    for s in sources:
        if s["ok"]:
            lines.append(f"| {s['label']} | {s['url']} | OK | "
                         f"{s.get('text_chars', 0)} chars of text |")
        else:
            lines.append(f"| {s['label']} | {s['url']} | REFUSED/FAILED | "
                         f"{s.get('status') or ''} "
                         f"{str(s.get('error', ''))[:90]} |")
    lines += ["", f"Corpus: {stats['documents']} documents, "
              f"{stats['entities']} entities, {stats['relations']} "
              f"relations.", "",
              f"## Ticker context coverage: {covered}/{len(targets)} "
              f"watchlist tickers have web context", "",
              "| Ticker | Mentions | Hot score | Top keywords | Sources |",
              "|--------|---------:|----------:|--------------|--------:|"]
    for t in targets:
        v = tickers_out[t]
        lines.append(f"| {t} | {v['mention_count']} | "
                     f"{v['hot_keyword_score']} | "
                     f"{', '.join(v['top_keywords'])} | "
                     f"{v['source_count']} |")
    lines += ["", "_Context is a weak, unproven signal: in the stocks "
              "engine it may only break ranking ties (<=5% bonus) and "
              "annotate signals. It never overrides price, regime, or "
              "guard logic._"]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[export] {covered}/{len(targets)} watchlist tickers with "
          f"context -> {INSIGHTS_JSON}")
    print(f"[report] {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
