"""Media metadata extraction — stdlib only, real parsing.

Images: PNG (IHDR), JPEG (SOF markers), GIF (logical screen descriptor)
-> format + pixel dimensions. Audio: WAV via the `wave` module ->
duration, channels, sample rate, sample width. Everything else (MP3,
MP4, ...) is registered with size + SHA-256 and labeled honestly:
transcription/OCR remains a pluggable extractor slot (see ingest.py),
it is NOT faked here.
"""
from __future__ import annotations

import hashlib
import struct
import wave
from pathlib import Path

# JPEG Start-Of-Frame markers (excluding DHT/JPG/RSTn etc.)
_SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def _png_info(data: bytes) -> dict:
    # PNG signature (8) + IHDR chunk: len(4) 'IHDR' width(4) height(4)
    # bit_depth(1) color_type(1)
    if len(data) < 33 or data[12:16] != b"IHDR":
        return {"format": "png", "parse_error": "missing IHDR"}
    width, height = struct.unpack(">II", data[16:24])
    return {"format": "png", "width": width, "height": height,
            "bit_depth": data[24], "color_type": data[25]}


def _gif_info(data: bytes) -> dict:
    if len(data) < 13:
        return {"format": "gif", "parse_error": "truncated header"}
    width, height = struct.unpack("<HH", data[6:10])
    return {"format": "gif", "width": width, "height": height}


def _jpeg_info(data: bytes) -> dict:
    i = 2  # skip SOI
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in _SOF_MARKERS:
            height, width = struct.unpack(">HH", data[i + 5:i + 9])
            return {"format": "jpeg", "width": width, "height": height,
                    "progressive": marker in (0xC2, 0xC6, 0xCA, 0xCE)}
        i += 2 + seg_len
    return {"format": "jpeg", "parse_error": "no SOF marker found"}


def _wav_info(path: Path) -> dict:
    try:
        with wave.open(str(path), "rb") as w:
            frames, rate = w.getnframes(), w.getframerate()
            return {"format": "wav", "channels": w.getnchannels(),
                    "sample_rate": rate, "sample_width_bytes": w.getsampwidth(),
                    "frames": frames,
                    "duration_seconds": round(frames / rate, 3) if rate else None}
    except (wave.Error, EOFError) as exc:
        return {"format": "wav", "parse_error": str(exc)}


def extract_media_metadata(path: Path) -> dict:
    """Return real metadata for a media file (see module docstring)."""
    path = Path(path)
    meta: dict = {
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "extension": path.suffix.lower(),
        "transcription": "extractor slot — not wired (no transcription performed)",
    }
    ext = path.suffix.lower()
    if ext == ".wav":
        meta.update(_wav_info(path))
    elif ext in (".png", ".jpg", ".jpeg", ".gif"):
        head = path.read_bytes()[:256 * 1024]
        if ext == ".png":
            meta.update(_png_info(head))
        elif ext == ".gif":
            meta.update(_gif_info(head))
        else:
            meta.update(_jpeg_info(head))
    elif ext in (".mp3", ".m4a"):
        meta.update({"format": ext[1:], "note": "audio registered; "
                     "duration/transcription need an extractor (slot)"})
    elif ext in (".mp4", ".mov"):
        meta.update({"format": ext[1:], "note": "video registered; "
                     "stream probing needs an extractor (slot)"})
    else:
        meta["format"] = ext[1:] or "unknown"
    return meta
