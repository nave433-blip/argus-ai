"""Document chunking: overlapping word-window chunks with metadata."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Chunk:
    doc_id: str
    index: int
    text: str
    start_word: int
    end_word: int
    metadata: dict = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        return f"{self.doc_id}#c{self.index}"


def chunk_text(doc_id: str, text: str, size: int = 120, overlap: int = 30,
               metadata: dict | None = None) -> list[Chunk]:
    if size <= 0:
        raise ValueError("chunk size must be positive")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap must be in [0, size)")
    words = text.split()
    if not words:
        return []
    chunks: list[Chunk] = []
    step = size - overlap
    idx = 0
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(Chunk(
            doc_id=doc_id, index=idx,
            text=" ".join(words[start:end]),
            start_word=start, end_word=end,
            metadata=dict(metadata or {}),
        ))
        idx += 1
        if end == len(words):
            break
        start += step
    return chunks
