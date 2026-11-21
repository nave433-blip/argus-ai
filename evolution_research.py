"""ARGUS evolution research run — crypto-trend-bot improvement cycle (2026-11-21).

Uses ARGUS SCOUT only (argus.agents.scout.fetch_public_page):
robots.txt respected, >=1s delay, plain User-Agent, GET only, no auth,
no circumvention. 403/robots refusals are recorded honestly.

Targets PUBLIC clearnet quant/strategy material:
 - Exchange academies (Binance Academy, Kraken Learn, Coinbase Learn)
 - arXiv (export API + abstract pages): momentum crashes, regime switching,
   ATR/chandelier exits, volatility targeting
 - SSRN public abstract pages (if reachable)
 - Public GitHub READMEs: freqtrade, jesse, backtrader, vectorbt
 - Quant blogs/studies found via EVOLUTION keywords

Outputs:
 - EVOLUTION_RESEARCH.md (this repo) — scrape table + concrete ideas
 - data/evolution_inbox/*.md — fetched texts
 - ../crypto-trend-bot/data/evolution_ideas.json — {idea, source_url, prediction, category}

Run: python3 evolution_research.py
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from argus.agents.scout import fetch_public_page
from crypto_research import html_to_text, slug

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "data" / "evolution_inbox"
REPORT_MD = ROOT / "EVOLUTION_RESEARCH.md"
IDEAS_JSON = ROOT.parent / "crypto-trend-bot" / "data" / "evolution_ideas.json"
CACHE = ROOT / "data" / "evolution_fetch_cache.json"

SEEDS = [
    ("Binance Academy - Moving Averages", "https://academy.binance.com/en/articles/what-are-moving-averages"),
    ("Binance Academy - RSI", "https://academy.binance.com/en/articles/relative-strength-index-explained"),
    ("Binance Academy - Risk Management", "https://academy.binance.com/en/articles/risk-management-in-crypto-trading"),
    ("Kraken Learn - Technical Analysis", "https://www.kraken.com/learn/trading/technical-analysis-crypto-trading"),
    ("Kraken Learn - Dollar Cost Averaging", "https://www.kraken.com/learn/dollar-cost-averaging"),
    ("Coinbase Learn - Crypto Trading Basics", "https://www.coinbase.com/learn/crypto-trading"),
    ("Coinbase Learn - What is volatility", "https://www.coinbase.com/learn/crypto-basics/what-is-volatility"),
    ("arXiv API - momentum crash", "https://export.arxiv.org/api/query?search_query=all:%22momentum+crash%22&start=0&max_results=5"),
    ("arXiv API - regime switching trend following", "https://export.arxiv.org/api/query?search_query=all:%22regime+switching%22+AND+all:%22trend+following%22&start=0&max_results=5"),
    ("arXiv API - volatility targeting", "https://export.arxiv.org/api/query?search_query=all:%22volatility+targeting%22&start=0&max_results=5"),
    ("arXiv API - ATR trailing stop chandelier", "https://export.arxiv.org/api/query?search_query=all:%22average+true+range%22+AND+all:%22trailing+stop%22&start=0&max_results=5"),
    ("arXiv API - trend following momentum", "https://export.arxiv.org/api/query?search_query=all:%22time+series+momentum%22&start=0&max_results=5"),
    ("SSRN - Momentum Crashes abstract", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2486270"),
    ("GitHub README - freqtrade", "https://raw.githubusercontent.com/freqtrade/freqtrade/develop/README.md"),
    ("GitHub README - jesse", "https://raw.githubusercontent.com/jesse-ai/jesse/master/README.md"),
    ("GitHub README - backtrader", "https://raw.githubusercontent.com/mementum/backtrader/master/README.rst"),
    ("GitHub README - vectorbt", "https://raw.githubusercontent.com/polakowo/vectorbt/master/README.md"),
    ("Freqtrade docs - strategy customization", "https://www.freqtrade.io/en/stable/strategy-customization/"),
    ("Freqtrade docs - stoploss / trailing", "https://www.freqtrade.io/en/stable/stoploss/"),
    ("Jesse docs - strategies", "https://docs.jesse.trade/docs/strategies/"),
    ("Quantpedia - Trend Following", "https://quantpedia.com/strategies/trend-following-effect-in-stocks/"),
    # Phase 2 (added after Phase 1 refusals were recorded): arXiv ABSTRACT
    # pages (not the export API, which robots-disallowed) and raw GitHub
    # docs (same raw host that allowed the READMEs) + public quant blogs.
    ("arXiv abstract - Momentum-Gated / momentum crashes (2604.09060)", "https://arxiv.org/abs/2604.09060"),
    ("arXiv HTML - Regime-Switching Jump Model (2402.05272)", "https://arxiv.org/html/2402.05272v2"),
    ("AlgoGP - Chandelier Exit guide", "https://www.algogp.com/library/technical-indicators/chandelier-exit-guide"),
    ("JournalPlus - ATR Trailing Stop strategy", "https://journalplus.co/strategies/atr-trailing-stop-strategy/"),
    ("Freqtrade raw docs - stoploss", "https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/stoploss.md"),
    ("Freqtrade raw docs - strategy customization", "https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/strategy-customization.md"),
    ("Freqtrade raw docs - protections", "https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/includes/protections.md"),
    ("VectorBT raw docs - portfolio", "https://raw.githubusercontent.com/polakowo/vectorbt/master/docs/source/portfolio.md"),
]

def _fetch_bounded(url, seconds=45):
    import signal
    def _boom(s,f): raise TimeoutError(f"fetch exceeded {seconds}s")
    old = signal.signal(signal.SIGALRM, _boom)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fetch_public_page(url)
    except Exception as exc:
        return {"url": url, "ok": False, "error": f"bounded fetch failed: {exc}"}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)

def main():
    INBOX.mkdir(parents=True, exist_ok=True)
    if CACHE.exists():
        cache = json.loads(CACHE.read_text())
        sources = cache["sources"]
        print(f"[scout] reusing cache {len(sources)} seeds")
    else:
        for old in INBOX.iterdir():
            if old.is_file(): old.unlink()
        sources=[]
        for label, url in SEEDS:
            res = _fetch_bounded(url)
            rec={"label":label,"url":url,"ok":bool(res.get("ok"))}
            if res.get("ok"):
                raw=res["text"]
                # arXiv API returns XML, GitHub raw is markdown — html_to_text works as plain text stripper for html, keep raw fallback
                text = html_to_text(raw) if "<html" in raw[:2000].lower() or "<!doctype" in raw[:2000].lower() else " ".join(raw.split())
                rec.update({"status":200,"bytes":len(raw),"text_chars":len(text)})
                (INBOX/f"{slug(label)}.md").write_text(f"# {label}\nSource: {url}\n\n{text}\n",encoding="utf-8")
            else:
                err=str(res.get("error","unknown"))
                m=re.search(r"HTTP Error (\d+)",err)
                rec.update({"status":int(m.group(1)) if m else None,"error":err})
            sources.append(rec)
            print(f"[scout] {label}: {'OK '+str(rec.get('text_chars'))+' chars' if rec['ok'] else 'FAIL '+str(rec.get('status'))+' '+str(rec.get('error'))[:90]}",flush=True)
        CACHE.write_text(json.dumps({"sources":sources},indent=2),encoding="utf-8")
    # Candidate sentence extraction for manual/curated idea building
    candidates=[]
    kw=re.compile(r"(momentum|regime|volatility target|ATR|chandelier|trailing stop|stoploss|Sharpe|drawdown|position siz|risk per trade|moving average|RSI|trend follow|walk.forward|backtest)",re.I)
    for f in sorted(INBOX.glob("*.md")):
        txt=f.read_text(encoding="utf-8",errors="replace")
        for sent in re.split(r"(?<=[.!?])\s+", txt):
            if kw.search(sent) and 40 < len(sent) < 400:
                candidates.append({"file":f.name,"sentence":sent.strip()})
    (ROOT/"data"/"evolution_candidates.json").write_text(json.dumps(candidates,indent=2),encoding="utf-8")
    print(f"[extract] {len(candidates)} candidate sentences -> data/evolution_candidates.json")
    # Draft report with scrape table (ideas section filled in curated pass if JSON exists)
    ideas=[]
    if IDEAS_JSON.exists():
        try: ideas=json.loads(IDEAS_JSON.read_text())
        except Exception: ideas=[]
    lines=["# ARGUS Evolution Research — Crypto Trend Bot Improvement Cycle","",f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}","",
    "Method: ARGUS SCOUT (robots.txt respected, >=1s delay, plain User-Agent ARGUS-AI Scout/0.5, GET only, no auth, no circumvention). Refusals recorded as-is.","",
    "## Scrape table","","| Source | URL | Result | Chars / Why |","|---|---|---|---|"]
    for s in sources:
        if s["ok"]: lines.append(f"| {s['label']} | {s['url']} | fetched | {s.get('text_chars',0)} chars |")
        else: lines.append(f"| {s['label']} | {s['url']} | refused/failed | {s.get('status') or ''} {str(s.get('error',''))[:110]} |")
    lines+=["",f"Fetched: {sum(1 for s in sources if s['ok'])}/{len(sources)}",""]
    if ideas:
        lines+=["## Concrete testable ideas",""]
        for i,it in enumerate(ideas,1):
            lines.append(f"{i}. **[{it.get('category')}]** {it.get('idea')} — Source: {it.get('source_url')} — Prediction: {it.get('prediction')}")
        lines+=""
    REPORT_MD.write_text("\n".join(lines),encoding="utf-8")
    print(f"[report] {REPORT_MD} ideas={len(ideas)}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
