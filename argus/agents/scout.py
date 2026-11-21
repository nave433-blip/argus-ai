"""SCOUT — discovery fetcher.

Fetches Evan's own documents from the inbox and, on request, PUBLIC
clearnet web pages — politely: robots.txt respected, >=1s delay, plain
User-Agent, GET only, no auth, no paywall/login bypass, no Tor/dark web.
This mirrors the guardrails of Evan's url-pattern-finder tool.
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
