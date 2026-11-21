"""Hot keyword engine: every match type, priority ordering, and the
SCOUT / pipeline / GUARDIAN wiring."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from argus.keywords import KeywordEngine, metaphone_lite, soundex
from argus.agents.guardian import Guardian, HOT_KEYWORD_NOTE
from argus.agents.scout import crawl_pages


def types_for(engine, text):
    return {(m["keyword"], m["match_type"]) for m in engine.score_text(text)["matches"]}


class TestMatchTypes(unittest.TestCase):
    def setUp(self):
        self.e = KeywordEngine()

    def test_exact(self):
        self.assertIn(("trends", "EXACT"), types_for(self.e, "market trends today"))
        self.assertIn(("cryptocurrency", "EXACT"),
                      types_for(self.e, "Cryptocurrency news"))

    def test_alias_trains_is_trends(self):
        # Evan dictated "trains" for "trends" — both spellings are seeds.
        self.assertIn(("trends", "EXACT"), types_for(self.e, "watch the trains"))

    def test_morphological(self):
        self.assertIn(("dip", "MORPHOLOGICAL"), types_for(self.e, "the dips"))
        self.assertIn(("swell", "MORPHOLOGICAL"), types_for(self.e, "swells"))
        self.assertIn(("invest", "MORPHOLOGICAL"),
                      types_for(self.e, "investors are investing"))
        self.assertIn(("crash", "MORPHOLOGICAL"), types_for(self.e, "it crashed"))
        self.assertIn(("cryptocurrency", "MORPHOLOGICAL"),
                      types_for(self.e, "crypto markets"))

    def test_spelling(self):
        self.assertIn(("cryptocurrency", "SPELLING"),
                      types_for(self.e, "crptocurrency rallies"))
        self.assertIn(("crash", "SPELLING"), types_for(self.e, "a crsh coming"))

    def test_phonetic(self):
        k = KeywordEngine([{"keyword": "kraken", "weight": 2}])
        # doubled-letter mangling: too far for edit distance, same sound
        self.assertIn(("kraken", "PHONETIC"), types_for(k, "crakkenn exchange"))
        # Evan's voice transcript said "cell" for "sell": it must still
        # land on the sell keyword (spelling or phonetic path).
        hits = {kw for kw, _ in types_for(self.e, "cell the dip")}
        self.assertIn("sell", hits)
        self.assertEqual(soundex("sell"), "S400")
        self.assertEqual(metaphone_lite("cell"), metaphone_lite("sell"))

    def test_encoded(self):
        self.assertIn(("sell", "ENCODED"), types_for(self.e, "s3ll now"))
        # reversed token: "lles" is "sell" backwards
        self.assertIn(("sell", "ENCODED"), types_for(self.e, "lles everything"))
        import base64
        token = base64.b64encode(b"crash").decode()
        self.assertIn(("crash", "ENCODED"), types_for(self.e, f"signal {token} soon"))

    def test_false_positive_guards(self):
        # "well" is edit-distance 1 from "sell" but a common word: no hit.
        self.assertEqual(self.e.score_text("the well is deep")["matches"], [])
        # "diploma" starts with "dip" but is not a suffix variant.
        hits = {kw for kw, _ in types_for(self.e, "diploma ceremony")}
        self.assertNotIn("dip", hits)
        # plain unrelated text scores zero
        r = self.e.score_text("gardening tools and local weather")
        self.assertEqual(r["score"], 0.0)
        self.assertFalse(r["hot"])

    def test_hot_flag_and_priority_order(self):
        r = self.e.score_text("Cryptocurrency crash: sell as the dip deepens")
        self.assertTrue(r["hot"])
        pages = [{"url": "https://x.com/garden", "text": "roses and soil"},
                 {"url": "https://x.com/market", "text": "cryptocurrency crash, sell the dip"},
                 {"url": "https://x.com/blog", "text": "my travel blog"}]
        out = self.e.prioritize(pages)
        self.assertEqual(out[0]["url"], "https://x.com/market")
        self.assertTrue(out[0]["hot"])
        self.assertFalse(out[-1]["hot"])


class TestScoutWiring(unittest.TestCase):
    def test_crawl_pages_hot_first(self):
        texts = {
            "https://a.example/quiet": "local weather and gardening",
            "https://a.example/hot": "cryptocurrency crash — sell the dip, trends down",
        }

        def fake_fetch(url):
            return {"url": url, "ok": True, "text": texts[url]}

        pages = crawl_pages(list(texts), fetcher=fake_fetch)
        self.assertEqual(pages[0]["url"], "https://a.example/hot")
        self.assertTrue(pages[0]["hot"])
        self.assertGreater(pages[0]["keyword_score"], pages[1]["keyword_score"])
        self.assertTrue(pages[0]["keyword_matches"])


class TestGuardianNote(unittest.TestCase):
    def test_hot_hits_are_relevance_not_risk(self):
        g = Guardian()
        text = "crash sell dip cryptocurrency trends"
        plain = g.assess(text)
        e = KeywordEngine()
        matches = e.score_text(text)["matches"]
        with_hot = g.assess(text, hot_matches=matches)
        self.assertEqual(plain["risk"]["score"], with_hot["risk"]["score"])
        self.assertEqual(with_hot["hot_keywords"]["note"], HOT_KEYWORD_NOTE)
        self.assertTrue(with_hot["hot_keywords"]["matches"])


class TestPipelineStorage(unittest.TestCase):
    def test_hot_keywords_stored_as_entities_and_metadata(self):
        import tempfile
        from argus.pipeline import run_pipeline
        from argus.store import Store

        with tempfile.TemporaryDirectory() as td:
            inbox = Path(td) / "inbox"
            inbox.mkdir()
            (inbox / "hot.txt").write_text(
                "Cryptocurrency crash: investors sell the dip as trends fall.")
            (inbox / "calm.txt").write_text("A quiet note about lunch plans.")
            store = Store(Path(td) / "t.db")
            report = run_pipeline(inbox, store)
            by_id = {r["doc_id"]: r for r in report}
            hot_doc = next(r for r in report if r["hot"])
            self.assertGreater(hot_doc["keyword_score"], 0)
            ents = {(e["type"], e["value"]) for e in store.entities(hot_doc["doc_id"])}
            self.assertIn(("HOT_KEYWORD", "crash"), ents)
            self.assertIn(("HOT_KEYWORD", "cryptocurrency"), ents)
            docs = {d["doc_id"]: d for d in store.documents()}
            import json
            meta = json.loads(docs[hot_doc["doc_id"]]["metadata"])
            self.assertTrue(meta["hot"])
            self.assertTrue(meta["hot_keywords"])
            calm = next(r for r in report if not r["hot"])
            self.assertEqual(by_id[calm["doc_id"]]["keyword_matches"], [])
            store.close()


if __name__ == "__main__":
    unittest.main()
