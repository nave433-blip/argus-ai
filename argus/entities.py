"""Entity extraction: transparent rule/regex-based extraction.

Types: PERSON (capitalized name heuristic), ORG (suffix/cue based),
PLACE (gazetteer + cue based), DATE, MONEY, CRYPTO_ADDRESS (BTC/ETH),
EMAIL, URL. Deliberately simple and explainable — swap in spaCy/LLM
extraction later behind the same function signature.
"""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("CRYPTO_ADDRESS", re.compile(r"\b(bc1[a-z0-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|0x[a-fA-F0-9]{40})\b")),
    ("EMAIL", re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")),
    ("URL", re.compile(r"https?://[^\s)>\"]+")),
    ("MONEY", re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?\s?(?:million|billion|k|M|B)?\b|\b\d[\d,]*(?:\.\d{2})?\s?(?:USD|BTC|ETH)\b")),
    ("DATE", re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b")),
]
_ORG_RE = re.compile(r"\b([A-Z][A-Za-z0-9&]*(?:\s+[A-Z][A-Za-z0-9&]*)*\s+(?:Inc|LLC|Ltd|Corp|Corporation|Labs|Foundation|University|Institute|Group|Holdings|Capital|Technologies|Systems))\b")
_PERSON_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b")
_PLACES = {"Bloomington", "Indianapolis", "Kalamazoo", "Chicago", "New York",
           "Los Angeles", "San Francisco", "Austin", "Miami", "Indiana",
           "Michigan", "Illinois", "California", "Texas"}
_STOPWORDS = {"The", "This", "That", "When", "After", "Before", "Monday",
              "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}


def extract_entities(text: str) -> list[dict]:
    text = re.sub(r"\s+", " ", text)  # flatten newlines so names stay whole
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(etype: str, value: str) -> None:
        key = (etype, value.strip())
        if value.strip() and key not in seen:
            seen.add(key)
            found.append({"type": etype, "value": value.strip()})

    for etype, pat in _PATTERNS:
        for m in pat.finditer(text):
            add(etype, m.group(0))
    for m in _ORG_RE.finditer(text):
        add("ORG", m.group(1))
    for place in _PLACES:
        if re.search(rf"\b{re.escape(place)}\b", text):
            add("PLACE", place)
    for m in _PERSON_RE.finditer(text):
        name = m.group(1)
        if any(w in _STOPWORDS for w in name.split()):
            continue
        if any(name == e["value"] for e in found if e["type"] == "ORG"):
            continue
        add("PERSON", name)
    return found


def cooccurrence_relations(entities: list[dict]) -> list[tuple[str, str, str]]:
    """Entities appearing in the same document are linked as co_occurs."""
    values = [e["value"] for e in entities]
    rels = []
    for i, a in enumerate(values):
        for b in values[i + 1:]:
            rels.append((a, b, "co_occurs"))
    return rels
