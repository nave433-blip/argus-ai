"""SCOUT — discovery fetcher.

Fetches Evan's own documents from the inbox and, on request, PUBLIC
clearnet web pages — politely: robots.txt respected, >=1s delay, plain
User-Agent, GET only, no auth, no paywall/login bypass, no Tor/dark web.
This mirrors the guardrails of Evan's url-pattern-finder tool.

Crawl results pass through the HOT KEYWORD engine (argus.keywords):
pages hitting Evan's buzz words (trends/cryptocurrency/swell/dip/crash/
buy/sell/invest — plus misspelled, phonetic and encoded variants) are
flagged `hot` and returned FIRST. Keywords change priority, never
permission.
"""
from __future__ import annotations

import time
import urllib.request
import urllib.robotparser
from pathlib import Path

UA = "ARGUS-AI Scout/0.5 (personal research; public pages only)"
_last_fetch = 0.0


def fetch_public_page(url: str, min_delay: float = 1.0, timeout: float = 12.0) -> dict:
    global _last_fetch
    if not url.startswith(("https://", "http://")):
        return {"url": url, "ok": False, "error": "only http/https public URLs"}
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(urllib.parse.urljoin(url, "/robots.txt"))
        rp.read()
        if not rp.can_fetch(UA, url):
            return {"url": url, "ok": False, "error": "robots.txt disallows"}
    except Exception:
        return {"url": url, "ok": False, "error": "robots.txt unreadable — skipped"}
    wait = min_delay - (time.time() - _last_fetch)
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(200_000).decode("utf-8", errors="replace")
        _last_fetch = time.time()
        return {"url": url, "ok": True, "text": body}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "ok": False, "error": str(exc)}


def discover_inbox(inbox: str | Path) -> list[str]:
    p = Path(inbox)
    return [str(f) for f in sorted(p.iterdir()) if f.is_file()] if p.exists() else []


def crawl_pages(urls, engine=None, fetcher=None) -> list[dict]:
    """Fetch public pages and return them HOT-KEYWORD FIRST.

    Each page is scored with the hot-keyword engine (argus.keywords):
    results carry keyword_score, keyword_matches and a `hot` flag, and
    are sorted so hot/high-scoring pages come first — they take
    priority over normal scraping results. Fetching itself is unchanged:
    public pages only, robots respected, polite delay (fetch_public_page).
    `fetcher` is injectable for tests: fetcher(url) -> fetch_public_page
    shaped dict.
    """
    from ..keywords import KeywordEngine

    engine = engine or KeywordEngine()
    fetch = fetcher or fetch_public_page
    pages = []
    for url in urls:
        got = fetch(url)
        pages.append({
            "url": url,
            "ok": bool(got.get("ok")),
            "error": got.get("error"),
            "text": got.get("text", "") if got.get("ok") else "",
        })
    return engine.prioritize(pages)
