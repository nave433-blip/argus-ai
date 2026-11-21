"""v0.5 tests: Ollama (mocked), Graph RAG, media metadata, job queue,
adapter fallback + mocked-server behavior. No live servers required."""
import io
import json
import struct
import sys
import tempfile
import unittest
import wave
import zlib
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from argus import adapters
from argus.agents.oracle import Oracle
from argus.embeddings import HashingEmbedder
from argus.ingest import load_document
from argus.jobs import JobQueue, run_worker
from argus.media import extract_media_metadata
from argus.ollama import OllamaClient, OllamaConfig, OllamaEmbedder, OllamaGenerator
from argus.pipeline import run_pipeline
from argus.search import HybridSearch
from argus.store import Store

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- Ollama
def fake_ollama_opener(url, data, timeout):
    if url.endswith("/api/tags"):
        return json.dumps({"models": [{"name": "llama3.1"}]}).encode()
    if url.endswith("/api/generate"):
        req = json.loads(data.decode())
        assert "Context:" in req["prompt"]
        return json.dumps({"response": "Grounded answer [bitcoin-treasury-note#c0]."}).encode()
    if url.endswith("/api/embeddings"):
        return json.dumps({"embedding": [0.1, 0.2, 0.3, 0.4]}).encode()
    raise AssertionError(f"unexpected url {url}")


def dead_opener(url, data, timeout):
    raise OSError("connection refused")


class TestOllamaMocked(unittest.TestCase):
    def test_available_generate_embed(self):
        client = OllamaClient(OllamaConfig(), opener=fake_ollama_opener)
        self.assertTrue(client.available())
        self.assertEqual(client.models(), ["llama3.1"])
        self.assertIn("Grounded answer", client.generate("Context: x\nQ?"))
        emb = OllamaEmbedder(client)
        vec = emb.embed("hello")
        self.assertEqual(vec, [0.1, 0.2, 0.3, 0.4])
        self.assertEqual(emb.dim, 4)

    def test_unavailable_falls_back(self):
        client = OllamaClient(OllamaConfig(), opener=dead_opener)
        self.assertFalse(client.available())
        gen = OllamaGenerator(client)
        self.assertIsNone(gen.generate("anything"))


# -------------------------------------------------------------- Graph RAG
class TestGraphRAG(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "t.db")
        run_pipeline(ROOT / "data" / "inbox", self.store)
        gen = OllamaGenerator(OllamaClient(OllamaConfig(), opener=dead_opener))
        self.oracle = Oracle(HybridSearch(self.store, HashingEmbedder()),
                             store=self.store, generator=gen)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_extractive_answer_shape(self):
        out = self.oracle.ask("who discussed the bitcoin treasury policy?", limit=3)
        self.assertIn("extractive", out["mode"])
        self.assertTrue(out["citations"])
        self.assertTrue(all("#c" in c for c in out["citations"]))
        self.assertIn(out["citations"][0], out["answer"])  # cited inline
        ctx = out["graph_context"]
        self.assertTrue(ctx["entities"])                    # seed entities
        self.assertTrue(ctx["neighbors"])                   # 1-hop expansion
        self.assertTrue(ctx["related_docs"])

    def test_generative_when_ollama_up(self):
        gen = OllamaGenerator(OllamaClient(OllamaConfig(), opener=fake_ollama_opener))
        oracle = Oracle(HybridSearch(self.store, HashingEmbedder()),
                        store=self.store, generator=gen)
        out = oracle.ask("what was the bitcoin budget?", limit=3)
        self.assertIn("ollama", out["mode"])
        self.assertIn("Grounded answer", out["answer"])


# ----------------------------------------------------------------- Media
def _make_png(path: Path, w=7, h=3):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + b"\x00" * (w * 3) for _ in range(h))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    path.write_bytes(png)


def _make_jpeg(path: Path, w=11, h=5):
    sof = struct.pack(">H", 8 + 3 * 3) + b"\x08" + struct.pack(">HH", h, w) \
        + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01"
    app0 = struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    path.write_bytes(b"\xff\xd8" + b"\xff\xe0" + app0 + b"\xff\xc0" + sof + b"\xff\xd9")


def _make_wav(path: Path, seconds=1, rate=8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * 2 * rate * seconds)


class TestMediaMetadata(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_png_dimensions(self):
        p = self.dir / "img.png"
        _make_png(p, 7, 3)
        meta = extract_media_metadata(p)
        self.assertEqual((meta["format"], meta["width"], meta["height"]), ("png", 7, 3))
        self.assertEqual(len(meta["sha256"]), 64)

    def test_jpeg_dimensions(self):
        p = self.dir / "img.jpg"
        _make_jpeg(p, 11, 5)
        meta = extract_media_metadata(p)
        self.assertEqual((meta["format"], meta["width"], meta["height"]), ("jpeg", 11, 5))

    def test_gif_dimensions(self):
        p = self.dir / "img.gif"
        p.write_bytes(b"GIF89a" + struct.pack("<HH", 13, 4) + b"\x00" * 10)
        meta = extract_media_metadata(p)
        self.assertEqual((meta["width"], meta["height"]), (13, 4))

    def test_wav_duration_and_channels(self):
        p = self.dir / "clip.wav"
        _make_wav(p, seconds=1, rate=8000)
        meta = extract_media_metadata(p)
        self.assertEqual(meta["channels"], 2)
        self.assertEqual(meta["sample_rate"], 8000)
        self.assertAlmostEqual(meta["duration_seconds"], 1.0, places=2)

    def test_ingest_registers_media_metadata(self):
        p = self.dir / "pic.png"
        _make_png(p, 2, 2)
        doc = load_document(p)
        self.assertEqual(doc.kind, "media")
        self.assertEqual(doc.metadata["media_metadata"]["width"], 2)


# -------------------------------------------------------------- Job queue
class TestJobQueue(unittest.TestCase):
    def test_claim_is_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            qpath = Path(td) / "jobs.db"
            q1, q2 = JobQueue(qpath), JobQueue(qpath)
            jid = q1.enqueue("ingest", {"inbox": str(ROOT / "data" / "inbox"),
                                        "db": str(Path(td) / "out.db")})
            first = q1.claim("worker-a")
            self.assertIsNotNone(first)
            self.assertEqual(first["id"], jid)
            self.assertIsNone(q2.claim("worker-b"))  # already claimed
            self.assertEqual(run_worker(q1, "worker-a", once=True), 0)
            q1.close(); q2.close()

    def test_worker_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            qpath = Path(td) / "jobs.db"
            queue = JobQueue(qpath)
            jid = queue.enqueue("ingest", {"inbox": str(ROOT / "data" / "inbox"),
                                           "db": str(Path(td) / "out.db")})
            processed = run_worker(queue, "w1", max_jobs=1)
            self.assertEqual(processed, 1)
            job = queue.get(jid)
            self.assertEqual(job["status"], "done")
            self.assertEqual(job["result"]["doc_count"], 3)
            self.assertEqual(queue.stats(), {"done": 1})
            queue.close()

    def test_failed_job_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            queue = JobQueue(Path(td) / "jobs.db")
            jid = queue.enqueue("ingest", {"inbox": "/nonexistent-inbox",
                                           "db": str(Path(td) / "o.db")})
            run_worker(queue, "w1", max_jobs=1)
            job = queue.get(jid)
            self.assertEqual(job["status"], "failed")
            self.assertTrue(job["error"])
            queue.close()


# --------------------------------------------------------------- Adapters
def fake_rest_opener_factory(kind):
    def opener(url, data, headers, timeout):
        if data is None:  # GET ping
            return 200, b'{"title":"ok"}'
        payload = json.loads(data.decode()) if data else {}
        if kind == "qdrant" and "/points/search" in url:
            return 200, json.dumps({"result": [
                {"score": 0.9, "payload": {"chunk_id": "d#c0"}}]}).encode()
        if kind == "neo4j" and "/tx/commit" in url:
            return 200, json.dumps({"results": [
                {"columns": ["neighbor", "relation"],
                 "data": [{"row": ["Marcus Webb", "CO_OCCURS"]}]}], "errors": []}).encode()
        if kind == "opensearch" and "_search" in url:
            return 200, json.dumps({"hits": {"hits": [
                {"_score": 1.5, "_source": {"chunk_id": "d#c0", "doc_id": "d",
                                            "text": "hit text"}}]}}).encode()
        return 200, b"{}"
    return opener


class TestAdapters(unittest.TestCase):
    def test_fallback_when_unconfigured(self):
        env = {k: v for k, v in __import__("os").environ.items()
               if not k.startswith("ARGUS_")}
        with mock.patch.dict("os.environ", env, clear=True):
            self.assertIsNone(adapters.get_vector_store())
            self.assertIsNone(adapters.get_graph_store())
            self.assertIsNone(adapters.get_search_index())

    def test_fallback_when_server_unreachable(self):
        def boom(url, data, headers, timeout):
            raise OSError("refused")
        with mock.patch.dict("os.environ", {"ARGUS_QDRANT_URL": "http://localhost:6333"}):
            self.assertIsNone(adapters.get_vector_store(opener=boom))

    def test_qdrant_search_mocked(self):
        a = adapters.QdrantAdapter("http://q:6333", opener=fake_rest_opener_factory("qdrant"))
        self.assertTrue(a.ping())
        hits = a.search([0.1, 0.2], limit=3)
        self.assertEqual(hits[0]["chunk_id"], "d#c0")

    def test_neo4j_neighbors_mocked(self):
        a = adapters.Neo4jAdapter("http://n:7474", password="x",
                                  opener=fake_rest_opener_factory("neo4j"))
        rows = a.neighbors("Northgate Capital")
        self.assertEqual(rows[0]["neighbor"], "Marcus Webb")

    def test_opensearch_search_mocked(self):
        a = adapters.OpenSearchAdapter("http://o:9200",
                                       opener=fake_rest_opener_factory("opensearch"))
        hits = a.search("bitcoin")
        self.assertEqual(hits[0]["text"], "hit text")


if __name__ == "__main__":
    unittest.main()
