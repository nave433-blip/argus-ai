"""Classification + risk scoring: transparent keyword/pattern rules.

Every score comes with the list of signals that produced it — no black
box. Categories are simple topical buckets; risk is a 0-100 score built
from weighted signal groups (financial exposure, legal/court, health,
urgency, secrecy cues). This is a triage aid for Evan's own documents,
not a judgment of any person.
"""
from __future__ import annotations

CATEGORIES: dict[str, list[str]] = {
    "finance": ["bitcoin", "btc", "eth", "crypto", "invoice", "payment", "budget", "loan", "bank", "price", "cost", "$"],
    "legal": ["court", "judge", "attorney", "case", "filing", "custody", "hearing", "contract", "agreement"],
    "health": ["doctor", "therapy", "treatment", "recovery", "clinic", "medication", "appointment"],
    "project": ["build", "release", "version", "github", "code", "feature", "roadmap", "deploy"],
    "personal": ["family", "daughter", "home", "birthday", "school"],
}

RISK_SIGNALS: dict[str, tuple[int, list[str]]] = {
    "financial_exposure": (15, ["wire transfer", "send funds", "investment", "guaranteed returns", "double your"]),
    "legal_pressure": (15, ["deadline", "court order", "lawsuit", "eviction", "foreclosure"]),
    "urgency": (10, ["urgent", "immediately", "act now", "expires today", "final notice"]),
    "secrecy_cues": (20, ["do not tell", "keep this secret", "confidential — destroy", "off the record"]),
    "credential_request": (25, ["password", "seed phrase", "private key", "ssn", "social security"]),
    "health_safety": (15, ["overdose", "relapse", "crisis", "emergency", "hospital"]),
}


def classify(text: str) -> dict:
    low = text.lower()
    scores = {cat: sum(low.count(w) for w in words) for cat, words in CATEGORIES.items()}
    if not any(scores.values()):
        return {"category": "uncategorized", "scores": scores}
    best = max(scores, key=lambda c: scores[c])
    return {"category": best, "scores": scores}


def risk_score(text: str) -> dict:
    low = text.lower()
    total = 0
    hits = []
    for name, (weight, phrases) in RISK_SIGNALS.items():
        matched = [p for p in phrases if p in low]
        if matched:
            total += weight
            hits.append({"signal": name, "weight": weight, "matched": matched})
    total = min(total, 100)
    level = "low" if total < 25 else "medium" if total < 55 else "high"
    return {"score": total, "level": level, "signals": hits}
