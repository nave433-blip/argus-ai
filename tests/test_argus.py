import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from argus.agents.nexus import Nexus
from argus.chunking import chunk_text
from argus.classify import classify, risk_score
from argus.config_crypto import decrypt_config, encrypt_config, generate_key
from argus.embeddings import HashingEmbedder, cosine
from argus.entities import extract_entities
from argus.pipeline import run_pipeline
from argus.search import HybridSearch
from argus.store import Store

ROOT = Path(__file__).resolve().parent.parent


class TestChunking(unittest.TestCase):
    def test_overlap_and_coverage(self):
        text = " ".join(f"w{i}" for i in range(300))
        chunks = chunk_text("doc", text, size=120, overlap=30)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0].start_word, 0)
        self.assertEqual(chunks[1].start_word, 90)  # 120 - 30
        self.assertEqual(chunks[-1].end_word, 300)

    def test_empty(self):
        self.assertEqual(chunk_text("doc", ""), [])


class TestEmbeddings(unittest.TestCase):
    def test_deterministic(self):
        e = HashingEmbedder()
        a, b = e.embed("bitcoin treasury policy"), e.embed("bitcoin treasury policy")
        self.assertEqual(a, b)
        self.assertAlmostEqual(cosine(a, b), 1.0, places=5)

    def test_similar_beats_unrelated(self):
        e = HashingEmbedder()
        q = e.embed("bitcoin wallet payment")
        near = e.embed("bitcoin wallet payment policy budget")
        far = e.embed("court custody hearing judge filing")
        self.assertGreater(cosine(q, near), cosine(q, far))


class TestHybridSearchSeeded(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "t.db")
        run_pipeline(ROOT / "data" / "inbox", self.store)
        self.search = HybridSearch(self.store, HashingEmbedder())

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_bitcoin_query_hits_bitcoin_doc(self):
        hits = self.search.search("bitcoin treasury policy budget", limit=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["doc_id"], "bitcoin-treasury-note")

    def test_court_query_hits_court_doc(self):
        hits = self.search.search("custody hearing judge court filing", limit=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["doc_id"], "court-documents-summary")


class TestEntities(unittest.TestCase):
    def test_extraction(self):
        text = ("On 2026-03-14, Marcus Webb from Northgate Capital met in "
                "Bloomington about $25,000 and wallet "
                "0x742d35Cc6634C0532925a3b844Bc454e4438f44e.")
        ents = {(e["type"], e["value"]) for e in extract_entities(text)}
        self.assertIn(("DATE", "2026-03-14"), ents)
        self.assertIn(("MONEY", "$25,000"), ents)
        self.assertTrue(any(t == "CRYPTO_ADDRESS" for t, _ in ents))
        self.assertTrue(any(t == "PERSON" for t, _ in ents))


class TestRiskAndClassify(unittest.TestCase):
    def test_scam_scores_high(self):
        text = (ROOT / "data" / "inbox" / "scam-warning-example.txt").read_text()
        r = risk_score(text)
        self.assertGreaterEqual(r["score"], 55)
        self.assertEqual(r["level"], "high")
        self.assertTrue(r["signals"])  # explained

    def test_plain_text_scores_low(self):
        r = risk_score("Family picnic at the park on Saturday with the kids.")
        self.assertEqual(r["level"], "low")

    def test_classify(self):
        self.assertEqual(classify("The court judge set a hearing for the case filing.")["category"], "legal")


class TestConfigCrypto(unittest.TestCase):
    def test_roundtrip(self):
        key = generate_key()
        payload = encrypt_config({"qdrant_url": "http://localhost:6333", "n": 1}, key_b64=key)
        self.assertNotIn("localhost", json.dumps(payload))
        self.assertEqual(decrypt_config(payload, key_b64=key)["n"], 1)


class TestNexusRouting(unittest.TestCase):
    def test_routes(self):
        with tempfile.TemporaryDirectory() as td:
            nexus = Nexus(Store(Path(td) / "n.db"))
            out = nexus.route({"type": "ingest", "inbox": str(ROOT / "data" / "inbox")})
            self.assertEqual(len(out["ingested"]), 3)
            s = nexus.route({"type": "search", "query": "bitcoin", "limit": 2})
            self.assertEqual(s["agent"], "ORACLE")
            self.assertTrue(s["results"])
            g = nexus.route({"type": "graph"})
            self.assertEqual(g["agent"], "ATLAS")
            self.assertTrue(g["graph"]["nodes"])
            a = nexus.route({"type": "assess", "text": "send your password immediately, urgent"})
            self.assertEqual(a["agent"], "GUARDIAN")
            self.assertIn("credential_content", a["assessment"]["policy_flags"])
            bad = nexus.route({"type": "nonsense"})
            self.assertIn("error", bad)


if __name__ == "__main__":
    unittest.main()
