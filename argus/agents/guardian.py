"""GUARDIAN — risk scoring + policy checks.

Scores documents with the transparent rules in argus.classify and
enforces ingestion policy: media-only or empty documents are flagged,
documents containing credential-request patterns are quarantined
(flagged, still stored — Evan's own archive may legitimately contain
his own notes; the flag is a warning, not a deletion).

NOTE on hot keywords: hits from the HOT KEYWORD engine
(argus.keywords) are a RELEVANCE signal — they mark what Evan wants
prioritized, never a risk signal. A document full of "crash / sell /
dip" buzz words is topical, not dangerous; GUARDIAN reports the hits
under `hot_keywords` and they never raise the risk score.
"""
from __future__ import annotations

from ..classify import classify, risk_score

POLICY_FLAGS = {
    "empty_document": "no extractable text (scan/media without extractor)",
    "credential_content": "document mentions passwords/keys — handle with care",
}

HOT_KEYWORD_NOTE = ("hot-keyword hits are a relevance signal "
                    "(Evan's priority topics), not a risk signal")


class Guardian:
    def assess(self, text: str, kind: str = "text",
               hot_matches: list[dict] | None = None) -> dict:
        flags = []
        if not text.strip():
            flags.append("empty_document")
        low = text.lower()
        if any(w in low for w in ("password", "seed phrase", "private key")):
            flags.append("credential_content")
        result = {
            "classification": classify(text),
            "risk": risk_score(text),
            "policy_flags": flags,
            "flag_meanings": {f: POLICY_FLAGS[f] for f in flags},
        }
        if hot_matches:
            result["hot_keywords"] = {
                "matches": hot_matches,
                "note": HOT_KEYWORD_NOTE,
            }
        return result
