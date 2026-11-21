"""Ingestion: load documents from an inbox directory.

Supported natively: .txt, .md. PDFs go through a pluggable extractor
interface — the default StdlibPdfTextExtractor pulls the text layer from
uncompressed/simple PDFs via zlib stream decompression; register a richer
extractor (e.g. pypdf) via `register_extractor` without touching the core.
Media files (.mp3/.mp4/.wav/.png/.jpg/.gif) are registered as media
documents with REAL extracted metadata (argus/media.py: image
dimensions, WAV duration/channels, size + SHA-256 for everything) —
transcription/OCR stays a pluggable extractor slot, honestly labeled.
"""
from __future__ import annotations

import re
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

MEDIA_EXTS = {".mp3", ".mp4", ".wav", ".m4a", ".png", ".jpg", ".jpeg", ".gif"}


@dataclass
class Document:
    doc_id: str
    source: str
    kind: str  # text | markdown | pdf | media
    text: str
    metadata: dict = field(default_factory=dict)


class PdfExtractor:
    """Interface for PDF text-layer extraction."""

    def extract(self, path: Path) -> str:
        raise NotImplementedError


class StdlibPdfTextExtractor(PdfExtractor):
    """Best-effort text-layer extraction using only the stdlib.

    Handles FlateDecode content streams and Tj/TJ text operators. PDFs
    without a text layer (scans) return "" — plug in pypdf/OCR for those.
    """

    def extract(self, path: Path) -> str:
        raw = path.read_bytes()
        out: list[str] = []
        for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
            data = m.group(1)
            try:
                data = zlib.decompress(data)
            except zlib.error:
                pass
            for tj in re.findall(rb"\((?:[^()\\]|\\.)*\)\s*Tj", data):
                out.append(self._unescape(tj[1:tj.rindex(b")")]))
            for tj in re.findall(rb"\[(.*?)\]\s*TJ", data, re.S):
                parts = re.findall(rb"\((?:[^()\\]|\\.)*\)", tj)
                out.append(b"".join(self._unescape(p[1:-1]) for p in parts))
        text = b" ".join(out).decode("latin-1", errors="replace")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _unescape(b: bytes) -> bytes:
        return (b.replace(b"\\(", b"(").replace(b"\\)", b")")
                 .replace(b"\\\\", b"\\").replace(b"\\n", b" "))


_EXTRACTORS: dict[str, Callable[[Path], str]] = {}


def register_extractor(ext: str, fn: Callable[[Path], str]) -> None:
    _EXTRACTORS[ext.lower()] = fn


def load_document(path: Path) -> Document:
    ext = path.suffix.lower()
    doc_id = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
    if ext in (".txt", ".md"):
        kind = "markdown" if ext == ".md" else "text"
        return Document(doc_id, str(path), kind,
                        path.read_text(encoding="utf-8", errors="replace"))
    if ext == ".pdf":
        if ext in _EXTRACTORS:
            text = _EXTRACTORS[ext](path)
        else:
            text = StdlibPdfTextExtractor().extract(path)
        return Document(doc_id, str(path), "pdf", text)
    if ext in MEDIA_EXTS:
        from .media import extract_media_metadata
        meta = extract_media_metadata(path)
        return Document(doc_id, str(path), "media", "",
                        {"media": True, "bytes": meta["size_bytes"],
                         "media_metadata": meta})
    raise ValueError(f"unsupported file type: {ext}")


def ingest_inbox(inbox: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(inbox.iterdir()):
        if path.is_file() and not path.name.startswith("."):
            try:
                docs.append(load_document(path))
            except ValueError:
                continue
    return docs
