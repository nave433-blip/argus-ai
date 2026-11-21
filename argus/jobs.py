"""Distributed workers (local form): a SQLite job queue + worker.

Jobs live in a `jobs` table (default file: argus_jobs.db). Any number of
worker processes can run against the same queue file; claiming is atomic
(BEGIN IMMEDIATE + conditional UPDATE) so a job is handed to exactly one
worker. WAL mode + busy_timeout keep concurrent writers from erroring.

Job types in v0.5: "ingest" {inbox, db} — run the ingest pipeline for an
inbox into a target store DB. The Go crawler fits upstream of this: it
fetches seed URLs politely into queue.jsonl; a producer can turn those
fetched files into ingest jobs here. See README "Workers" section.

CLI: `python -m argus.cli enqueue-ingest --inbox data/inbox`
     `python -m argus.cli worker --id w1 [--once]`
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path


class JobQueue:
    def __init__(self, path: str | Path = "argus_jobs.db"):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs(
            id TEXT PRIMARY KEY, type TEXT, payload TEXT,
            status TEXT DEFAULT 'pending', worker_id TEXT,
            created_at REAL, claimed_at REAL, finished_at REAL,
            result TEXT, error TEXT);
        """)
        self.db.commit()

    def enqueue(self, job_type: str, payload: dict) -> str:
        job_id = uuid.uuid4().hex[:12]
        self.db.execute(
            "INSERT INTO jobs(id,type,payload,status,created_at) VALUES (?,?,?,'pending',?)",
            (job_id, job_type, json.dumps(payload), time.time()))
        self.db.commit()
        return job_id

    def claim(self, worker_id: str) -> dict | None:
        """Atomically claim the oldest pending job; None if queue empty."""
        cur = self.db.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            row = cur.execute(
                "SELECT * FROM jobs WHERE status='pending' ORDER BY created_at, id LIMIT 1"
            ).fetchone()
            if row is None:
                cur.execute("COMMIT")
                return None
            cur.execute(
                "UPDATE jobs SET status='claimed', worker_id=?, claimed_at=? "
                "WHERE id=? AND status='pending'",
                (worker_id, time.time(), row["id"]))
            if cur.rowcount != 1:  # lost a race despite the lock — be safe
                cur.execute("ROLLBACK")
                return None
            cur.execute("COMMIT")
        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:  # noqa: BLE001
                pass
            raise
        return self.get(row["id"])

    def complete(self, job_id: str, result: dict) -> None:
        self.db.execute(
            "UPDATE jobs SET status='done', finished_at=?, result=? WHERE id=?",
            (time.time(), json.dumps(result), job_id))
        self.db.commit()

    def fail(self, job_id: str, error: str) -> None:
        self.db.execute(
            "UPDATE jobs SET status='failed', finished_at=?, error=? WHERE id=?",
            (time.time(), str(error), job_id))
        self.db.commit()

    def get(self, job_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["payload"] = json.loads(out["payload"] or "{}")
        if out.get("result"):
            out["result"] = json.loads(out["result"])
        return out

    def stats(self) -> dict:
        rows = self.db.execute(
            "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}

    def close(self) -> None:
        self.db.close()


def process_job(job: dict) -> dict:
    """Execute one claimed job. Raises on failure (caller marks failed)."""
    payload = job["payload"]
    if job["type"] == "ingest":
        from .pipeline import run_pipeline
        from .store import Store
        store = Store(payload.get("db", "argus.db"))
        try:
            report = run_pipeline(payload["inbox"], store)
        finally:
            store.close()
        return {"ingested_docs": [r["doc_id"] for r in report],
                "doc_count": len(report)}
    raise ValueError(f"unknown job type: {job['type']!r}")


def run_worker(queue: JobQueue, worker_id: str, once: bool = False,
               poll_seconds: float = 2.0, max_jobs: int | None = None) -> int:
    """Claim and process jobs until the queue is empty (or forever).

    Returns the number of jobs processed. With once=True, processes at
    most one job. Without once, keeps polling — Ctrl-C to stop.
    """
    processed = 0
    while True:
        job = queue.claim(worker_id)
        if job is None:
            if once or max_jobs is not None:
                return processed
            time.sleep(poll_seconds)
            continue
        try:
            result = process_job(job)
            queue.complete(job["id"], result)
        except Exception as exc:  # noqa: BLE001 — record, don't crash the worker
            queue.fail(job["id"], str(exc))
        processed += 1
        if once or (max_jobs is not None and processed >= max_jobs):
            return processed
