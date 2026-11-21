"""GUARDIAN — risk scoring + policy checks.

Scores documents with the transparent rules in argus.classify and
enforces ingestion policy: media-only or empty documents are flagged,
documents containing credential-request patterns are quarantined
(flagged, still stored — Evan's own archive may legitimately contain
his own notes; the flag is a warning, not a deletion).
"""
from __future__ import annotations

from ..classify import classify, risk_score

POLICY_FLAGS = {
    "empty_document": "no extractable text (scan/media without extractor)",
    "credential_content": "document mentions passwords/keys — handle with care",
}


class Guardian:
    def assess(self, text: str, kind: str = "text") -> dict:
        flags = []
        if not text.strip():
            flags.append("empty_document")
        low = text.lower()
        if any(w in low for w in ("password", "seed phrase", "private key")):
            flags.append("credential_content")
        return {
            "classification": classify(text),
            "risk": risk_score(text),
            "policy_flags": flags,
            "flag_meanings": {f: POLICY_FLAGS[f] for f in flags},
        }
