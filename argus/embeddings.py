"""Embeddings: deterministic local embedder behind an Embedder interface.

The default HashingEmbedder is a TF-style hashing embedder: tokens are
hashed into a fixed-dimension vector with per-token weights, L2-normalized.
It needs no model download and no external API, and it is fully
deterministic (same text -> same vector, every run, every machine).
A real model (sentence-transformers, Ollama embeddings) can replace it by
implementing the same interface.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Embedder(Protocol):
    dim: int

    def embed(self, text: str) -> list[float]:
        ...

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class HashingEmbedder:
    """Deterministic hashing/TF embedder (default, zero-dependency)."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = tokenize(text)
        if not tokens:
            return vec
        # term-frequency weighting: weight = sign * (1 + log(count))
        counts: dict[str, int] = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1
        for tok, n in counts.items():
            digest = hashlib.md5(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign * (1.0 + math.log(n))
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a)) or 1.0
    db = math.sqrt(sum(y * y for y in b)) or 1.0
    return num / (da * db)
