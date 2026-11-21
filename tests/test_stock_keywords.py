"""Stock hot-keyword list (data/hot_keywords_stocks.json): loads into the
shared KeywordEngine and fires on stock-market language, including the
fuzzy paths (misspelling / phonetic / encoded)."""
from pathlib import Path

from argus.keywords import KeywordEngine

PATH = Path(__file__).resolve().parent.parent / "data" / "hot_keywords_stocks.json"


def _engine():
    return KeywordEngine(path=PATH)


def test_stock_list_loads_with_expected_terms():
    eng = _engine()
    kws = {e["keyword"] for e in eng.entries}
    for term in ("earnings", "guidance", "upgrade", "downgrade", "surge",
                 "plunge", "breakout", "squeeze", "volatility", "merger"):
        assert term in kws


def test_exact_and_morphological_hits():
    eng = _engine()
    scored = eng.score_text(
        "Shares surge after earnings beat; company raises guidance "
        "and declares a dividend.")
    hit = {m["keyword"] for m in scored["matches"]}
    assert {"surge", "earnings", "beat", "guidance", "dividend"} <= hit
    assert scored["score"] > 0


def test_misspelling_and_phonetic_paths():
    eng = _engine()
    scored = eng.score_text("Guidence raised; stock in a sellof.")
    hit = {m["keyword"] for m in scored["matches"]}
    assert "guidance" in hit       # misspelling (edit distance)
    assert "selloff" in hit        # misspelling of selloff


def test_encoded_leet_hit():
    eng = _engine()
    scored = eng.score_text("massive squ33ze underway")
    hit = {m["keyword"] for m in scored["matches"]}
    assert "squeeze" in hit
