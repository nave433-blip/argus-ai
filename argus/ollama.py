"""Ollama integration: local LLM client over plain stdlib HTTP.

Talks to an Ollama server (default http://localhost:11434) using only
urllib — no third-party `ollama` package needed. Configuration comes
from the environment (or an explicit config dict, e.g. decrypted via
argus.config_crypto):

  ARGUS_OLLAMA_URL    base URL, default http://localhost:11434
  ARGUS_OLLAMA_MODEL  chat/generation model, default "llama3.1"
  ARGUS_OLLAMA_EMBED_MODEL  embedding model, default "nomic-embed-text"

Two adapters sit behind the existing interfaces:
  * OllamaEmbedder  — implements argus.embeddings.Embedder
  * OllamaGenerator — generate(prompt) -> str, used by ORACLE for
                      generative Graph RAG answers

Everything degrades gracefully: if no server answers, available()
returns False and callers fall back to the local hashing embedder /
extractive answers. The HTTP layer is injectable (`opener`) so the
client is unit-testable without a live server.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Callable, Optional, Sequence

# opener(url, data_bytes|None, timeout) -> response body bytes
Opener = Callable[[str, Optional[bytes], float], bytes]


def _default_opener(url: str, data: Optional[bytes], timeout: float) -> bytes:
    req = urllib.request.Request(
        url, data=data, method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class OllamaConfig:
    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.base_url = (cfg.get("ollama_url") or os.environ.get(
            "ARGUS_OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = cfg.get("ollama_model") or os.environ.get(
            "ARGUS_OLLAMA_MODEL", "llama3.1")
        self.embed_model = cfg.get("ollama_embed_model") or os.environ.get(
            "ARGUS_OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.timeout = float(cfg.get("ollama_timeout", 30.0))


class OllamaClient:
    def __init__(self, config: OllamaConfig | None = None,
                 opener: Opener | None = None):
        self.config = config or OllamaConfig()
        self._open = opener or _default_opener
        self._available: bool | None = None

    # -- transport ------------------------------------------------------
    def _get(self, path: str) -> dict:
        body = self._open(self.config.base_url + path, None, 5.0)
        return json.loads(body.decode("utf-8"))

    def _post(self, path: str, payload: dict, timeout: float | None = None) -> dict:
        data = json.dumps(payload).encode("utf-8")
        body = self._open(self.config.base_url + path, data,
                          timeout or self.config.timeout)
        return json.loads(body.decode("utf-8"))

    # -- API ------------------------------------------------------------
    def available(self, refresh: bool = False) -> bool:
        """True iff an Ollama server answers /api/tags. Cached."""
        if self._available is None or refresh:
            try:
                self._get("/api/tags")
                self._available = True
            except Exception:  # noqa: BLE001 — any failure = not available
                self._available = False
        return bool(self._available)

    def models(self) -> list[str]:
        try:
            return [m.get("name", "") for m in self._get("/api/tags").get("models", [])]
        except Exception:  # noqa: BLE001
            return []

    def generate(self, prompt: str, model: str | None = None) -> str:
        out = self._post("/api/generate", {
            "model": model or self.config.model,
            "prompt": prompt, "stream": False})
        return out.get("response", "")

    def embed(self, text: str, model: str | None = None) -> list[float]:
        out = self._post("/api/embeddings", {
            "model": model or self.config.embed_model, "prompt": text})
        vec = out.get("embedding")
        if not vec:
            raise RuntimeError("Ollama embeddings response had no 'embedding' field")
        return [float(v) for v in vec]


class OllamaGenerator:
    """Generator interface used by ORACLE: generate(prompt) -> str|None.

    Returns None (instead of raising) when the server is unreachable so
    ORACLE can fall back to extractive Graph RAG synthesis.
    """

    def __init__(self, client: OllamaClient | None = None):
        self.client = client or OllamaClient()

    def available(self) -> bool:
        return self.client.available()

    def generate(self, prompt: str) -> str | None:
        if not self.client.available():
            return None
        try:
            return self.client.generate(prompt)
        except Exception:  # noqa: BLE001
            return None


class OllamaEmbedder:
    """Embedder interface backed by Ollama embeddings.

    `dim` is learned from the first successful embedding (Ollama models
    differ); it defaults to 768 (nomic-embed-text) before that. If the
    server is down, embed() raises — callers that need a guaranteed-local
    path should use HashingEmbedder (the default pipeline embedder).
    """

    def __init__(self, client: OllamaClient | None = None):
        self.client = client or OllamaClient()
        self.dim = 768

    def embed(self, text: str) -> list[float]:
        vec = self.client.embed(text)
        self.dim = len(vec)
        return vec

    def embed_many(self, texts: Sequence[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
