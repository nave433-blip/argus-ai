"""HOT KEYWORD priority engine — Evan's buzz-word layer for the scrapers.

A configurable list of hot keywords (data/hot_keywords.json) takes
PRIORITY over normal scraping: pages and URLs that hit hot keywords are
scored, flagged `hot`, and processed/returned first. Matching is
deliberately forgiving because the real world misspells, mangles and
encodes words (and Evan dictates by voice, so "trends" arrives as
"trains" and "sell" arrives as "cell"):

  EXACT          the token is the keyword (or a configured alias)
  MORPHOLOGICAL  plural / -ing / -ed / -er variants, stems, and long
                 prefixes ("dips" -> dip, "investing" -> invest,
                 "crypto" -> cryptocurrency)
  ENCODED        leet-speak normalized back (s3ll -> sell), reversed
                 tokens (lles -> sell), and base64-looking tokens that
                 decode to text containing a keyword
  SPELLING       edit distance <= 2 (<= 1 for short keywords)
  PHONETIC       Soundex or metaphone-lite code equality
                 (cell -> sell, cracken -> kraken)

False-positive guards: fuzzy match types (SPELLING/PHONETIC) only apply
to tokens and keywords of length >= 4, tokens on a small common-word
stoplist never fuzzy-match, each keyword's score contribution is capped
at 3 token hits, and fuzzy matches score less than exact ones.

Keywords change PRIORITY, never PERMISSION: every fetch still goes
through the usual public-only, robots-respecting guardrails.

Stdlib only.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path

DEFAULT_KEYWORDS_PATH = Path(__file__).resolve().parent.parent / "data" / "hot_keywords.json"

MATCH_TYPES = ("EXACT", "MORPHOLOGICAL", "ENCODED", "SPELLING", "PHONETIC")

# Fuzzy matches are worth less than seeing the word written plainly.
_TYPE_FACTOR = {
    "EXACT": 1.0,
    "MORPHOLOGICAL": 0.9,
    "ENCODED": 0.9,
    "SPELLING": 0.7,
    "PHONETIC": 0.6,
}

MIN_FUZZY_LEN = 4          # spelling/phonetic need tokens & keywords >= 4 chars
MAX_PER_KEYWORD_HITS = 3   # keyword-stuffing can't farm score off one word

# Common words that sit within edit/phonetic distance of hot keywords
# ("well" ~ sell, "call" ~ sell-ish, "cape" ~ ...) — never fuzzy-match.
STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "will",
    "are", "was", "were", "has", "had", "not", "but", "you", "your",
    "they", "them", "then", "than", "when", "what", "well", "bell",
    "tell", "fell", "hell", "ball", "call", "fall", "wall", "all",
    "sellars", "seller",  # handled morphologically anyway; kept off fuzzy
    "trend",  # singular is a morphological hit on "trends", not fuzzy
}

_LEET = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t",
    "@": "a", "$": "s", "!": "i", "+": "t",
})

_TOKEN_RE = re.compile(r"[a-z0-9@$]+")
_B64_RE = re.compile(r"[A-Za-z0-9+/]{6,}={0,2}")

# token = keyword + one of these tails still counts as the same word
# family ("investors", "buyers", "investments"). The closed tail list is
# the guard: "diploma" does NOT match "dip" ("loma" is not a tail).
_SUFFIX_TAILS = {"s", "es", "ing", "ed", "er", "ers", "or", "ors",
                 "ly", "est", "ism", "ist", "ists", "ment", "ments"}


# --------------------------------------------------------------------------
# phonetics (stdlib implementations)
# --------------------------------------------------------------------------
def soundex(word: str) -> str:
    """Classic American Soundex."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    codes = {c: d for letters, d in (
        ("bfpv", "1"), ("cskgjqxz", "2"), ("dt", "3"),
        ("l", "4"), ("mn", "5"), ("r", "6")) for c in letters}
    first = w[0]
    digits = []
    prev = codes.get(first, "")
    for ch in w[1:]:
        d = codes.get(ch, "")
        if d and d != prev:
            digits.append(d)
        if ch not in "hw":
            prev = d
    return (first.upper() + "".join(digits) + "000")[:4]


def metaphone_lite(word: str) -> str:
    """Small metaphone-style code: soft c/g, ph->f, vowel dropping,
    duplicate collapsing. Consistency matters more than completeness —
    the same function codes both the keyword and the token."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    if w[:2] in ("kn", "gn", "pn"):
        w = w[1:]
    if w.startswith("wr"):
        w = w[1:]
    if w.startswith("wh"):
        w = "w" + w[2:]
    w = w.replace("ph", "f").replace("ck", "k").replace("x", "ks")
    if w.endswith("mb"):
        w = w[:-1]
    out = []
    for i, ch in enumerate(w):
        nxt = w[i + 1] if i + 1 < len(w) else ""
        if ch == "c":
            out.append("s" if nxt in "eiy" else "k")
        elif ch == "g":
            out.append("j" if nxt in "eiy" else "k")
        elif ch == "q":
            out.append("k")
        elif ch == "v":
            out.append("f")
        elif ch == "z":
            out.append("s")
        elif ch == "h" and i > 0 and w[i - 1] not in "csptg":
            continue  # silent h (not after c/s/p/t/g)
        else:
            out.append(ch)
    w = "".join(out).replace("th", "t")
    if len(w) > 1:
        w = w[0] + re.sub(r"[aeiou]", "", w[1:])
    return re.sub(r"(.)\1+", r"\1", w).upper()


# --------------------------------------------------------------------------
# morphology + spelling helpers
# --------------------------------------------------------------------------
def _stem(word: str) -> str:
    w = word
    for suf in ("ingly", "edly", "ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: -len(suf)]
            break
    if w.endswith("i") and len(w) > 3:  # dippies -> dippy-ish; keep simple
        pass
    return w


def _variants(keyword: str) -> set[str]:
    """Plural / -ing / -ed / -er surface forms of a keyword."""
    k = keyword
    forms = {k + "s", k + "es"}
    if k.endswith("y") and len(k) > 2 and k[-2] not in "aeiou":
        forms.add(k[:-1] + "ies")
    if k.endswith("e"):
        forms.add(k[:-1] + "ing")
        forms.add(k[:-1] + "ed")
        forms.add(k[:-1] + "er")
    else:
        forms.add(k + "ing")
        forms.add(k + "ed")
        forms.add(k + "er")
        # doubled final consonant: dip -> dipping / dipped
        if len(k) >= 3 and k[-1] not in "aeiouwxy" and k[-2] in "aeiou":
            forms.add(k + k[-1] + "ing")
            forms.add(k + k[-1] + "ed")
    return forms


def _levenshtein(a: str, b: str, cap: int = 2) -> int:
    """Edit distance with early exit above `cap`."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            cur.append(v)
            row_min = min(row_min, v)
        if row_min > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def _decode_leet(token: str) -> str:
    return token.translate(_LEET)


def _try_base64_word(token: str) -> str | None:
    """If a raw token looks like base64 and decodes to printable text,
    return the decoded text (else None). Never raises."""
    if len(token) < 6 or not _B64_RE.fullmatch(token):
        return None
    try:
        padded = token + "=" * (-len(token) % 4)
        raw = base64.b64decode(padded, validate=True)
        text = raw.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    if text.isprintable() and re.search(r"[a-zA-Z]{3,}", text):
        return text
    return None


# --------------------------------------------------------------------------
# the engine
# --------------------------------------------------------------------------
class KeywordEngine:
    """Scores text/URLs against the hot-keyword list.

    keywords: list of {"keyword": str, "weight": float,
                       "aliases": [str], "note": str} (aliases optional).
    """

    def __init__(self, keywords: list[dict] | None = None,
                 hot_threshold: float = 5.0, path: str | Path | None = None):
        if keywords is None:
            data = self._load(path or DEFAULT_KEYWORDS_PATH)
            keywords = data["keywords"]
            hot_threshold = float(data.get("hot_threshold", hot_threshold))
        self.hot_threshold = float(hot_threshold)
        self.entries: list[dict] = []
        for e in keywords:
            kw = str(e["keyword"]).lower().strip()
            if not kw:
                continue
            aliases = [str(a).lower().strip() for a in e.get("aliases", [])]
            self.entries.append({
                "keyword": kw,
                "weight": float(e.get("weight", 1.0)),
                "aliases": [a for a in aliases if a],
                "note": e.get("note", ""),
                "variants": _variants(kw),
                "stem": _stem(kw),
                "soundex": soundex(kw),
                "metaphone": metaphone_lite(kw),
            })
        self._exact = {}   # token -> entry (keywords + aliases)
        for e in self.entries:
            self._exact[e["keyword"]] = e
            for a in e["aliases"]:
                self._exact[a] = e

    @staticmethod
    def _load(path: str | Path) -> dict:
        p = Path(path)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"keywords": [], "hot_threshold": 5.0}

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> "KeywordEngine":
        return cls(None, path=path)

    # -- one token vs one entry -------------------------------------------
    def _match_token(self, token: str, entry: dict) -> str | None:
        kw = entry["keyword"]
        if token == kw:
            return "EXACT"
        if token in entry["variants"] or _stem(token) == entry["stem"]:
            return "MORPHOLOGICAL"
        # keyword + closed suffix tail: "investors", "buyers"
        if token.startswith(kw) and token[len(kw):] in _SUFFIX_TAILS:
            return "MORPHOLOGICAL"
        # long prefix: "crypto" for "cryptocurrency"
        if len(token) >= 5 and len(kw) >= 8 and kw.startswith(token):
            return "MORPHOLOGICAL"
        leet = _decode_leet(token)
        if leet != token and (leet == kw or leet in entry["variants"]
                              or _stem(leet) == entry["stem"]):
            return "ENCODED"
        if token[::-1] == kw:
            return "ENCODED"
        # fuzzy types need a plain alphabetic token: leet/digit tokens
        # are ENCODED territory ("s3ll" must not also phonetic-hit swell)
        if (token.isalpha() and len(token) >= MIN_FUZZY_LEN
                and len(kw) >= MIN_FUZZY_LEN and token not in STOPWORDS):
            cap = 1 if len(kw) <= 5 else 2
            if _levenshtein(token, kw, cap) <= cap:
                return "SPELLING"
            if (soundex(token) == entry["soundex"]
                    or metaphone_lite(token) == entry["metaphone"]):
                return "PHONETIC"
        return None

    # -- scoring ------------------------------------------------------------
    def score_text(self, text: str) -> dict:
        """-> {"score": float, "hot": bool, "matches": [match, ...]}.

        Each match: {keyword, matched_token, match_type, weight}.
        Per (keyword, token) only the strongest match type is kept, and
        each keyword contributes at most MAX_PER_KEYWORD_HITS hits.
        """
        if not text:
            return {"score": 0.0, "hot": False, "matches": []}
        best: dict[tuple[str, str], dict] = {}

        def offer(keyword: str, token: str, mtype: str, weight: float):
            key = (keyword, token)
            cand = {"keyword": keyword, "matched_token": token,
                    "match_type": mtype,
                    "weight": round(weight * _TYPE_FACTOR[mtype], 3)}
            if key not in best or cand["weight"] > best[key]["weight"]:
                best[key] = cand

        # base64-looking tokens in the RAW text (case matters for base64)
        for raw in _B64_RE.findall(text):
            decoded = _try_base64_word(raw)
            if not decoded:
                continue
            for word in _TOKEN_RE.findall(decoded.lower()):
                entry = self._exact.get(word)
                if entry:
                    offer(entry["keyword"], raw, "ENCODED", entry["weight"])

        tokens = _TOKEN_RE.findall(text.lower())
        for token in tokens:
            if len(token) < 3:
                continue
            entry = self._exact.get(token)
            if entry is not None:
                offer(entry["keyword"], token, "EXACT", entry["weight"])
                continue
            for e in self.entries:
                mtype = self._match_token(token, e)
                if mtype:
                    offer(e["keyword"], token, mtype, e["weight"])

        per_keyword: dict[str, list[dict]] = {}
        for m in best.values():
            per_keyword.setdefault(m["keyword"], []).append(m)
        matches: list[dict] = []
        score = 0.0
        for kw, hits in per_keyword.items():
            hits.sort(key=lambda m: -m["weight"])
            for m in hits[:MAX_PER_KEYWORD_HITS]:
                matches.append(m)
                score += m["weight"]
        matches.sort(key=lambda m: (-m["weight"], m["keyword"], m["matched_token"]))
        score = round(score, 3)
        return {"score": score, "hot": score >= self.hot_threshold,
                "matches": matches}

    # -- prioritization -------------------------------------------------------
    @staticmethod
    def _item_text(item) -> str:
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            parts = [str(item.get(k) or "") for k in
                     ("url", "title", "meta_description", "excerpt", "text", "source")]
            return " ".join(p for p in parts if p)
        return str(item)

    def prioritize(self, items: list) -> list:
        """Return items sorted hot-first (score desc, stable for ties).

        Dict items are annotated in place with keyword_score,
        keyword_matches and hot. Plain strings are wrapped as
        {"url": s, ...annotations}.
        """
        out = []
        for item in items:
            result = self.score_text(self._item_text(item))
            if isinstance(item, dict):
                item = {**item, "keyword_score": result["score"],
                        "keyword_matches": result["matches"],
                        "hot": result["hot"]}
            else:
                item = {"url": item, "keyword_score": result["score"],
                        "keyword_matches": result["matches"],
                        "hot": result["hot"]}
            out.append(item)
        out.sort(key=lambda d: -d["keyword_score"])
        return out
