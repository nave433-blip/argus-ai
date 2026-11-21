"""AES-128-GCM encrypted configuration for ARGUS's OWN config/secrets.

Standard practice: the app's config file (API endpoints, adapter
credentials, local paths) can be stored encrypted at rest. The key comes
from the ARGUS_CONFIG_KEY environment variable (base64, 16 bytes) and is
never written to disk by this module. Requires the `cryptography` package;
without it, functions raise a clear error and the interface + usage are
documented in docs/AES_CONFIG.md.
"""
from __future__ import annotations

import base64
import json
import os

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _HAVE_CRYPTO = True
except ImportError:  # pragma: no cover
    AESGCM = None  # type: ignore
    _HAVE_CRYPTO = False


def available() -> bool:
    return _HAVE_CRYPTO


def generate_key() -> str:
    """Return a fresh base64 AES-128 key (store it in ARGUS_CONFIG_KEY)."""
    if not _HAVE_CRYPTO:
        raise RuntimeError("cryptography package not installed — see docs/AES_CONFIG.md")
    return base64.b64encode(AESGCM.generate_key(bit_length=128)).decode()


def _key_from_env() -> bytes:
    raw = os.environ.get("ARGUS_CONFIG_KEY", "")
    if not raw:
        raise RuntimeError("ARGUS_CONFIG_KEY env var not set (base64 AES-128 key)")
    key = base64.b64decode(raw)
    if len(key) != 16:
        raise ValueError("ARGUS_CONFIG_KEY must decode to exactly 16 bytes (AES-128)")
    return key


def encrypt_config(config: dict, key_b64: str | None = None) -> dict:
    """Encrypt a config dict -> {nonce, ciphertext} (both base64)."""
    if not _HAVE_CRYPTO:
        raise RuntimeError("cryptography package not installed — see docs/AES_CONFIG.md")
    key = base64.b64decode(key_b64) if key_b64 else _key_from_env()
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct = aes.encrypt(nonce, json.dumps(config).encode("utf-8"), None)
    return {"nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ct).decode()}


def decrypt_config(payload: dict, key_b64: str | None = None) -> dict:
    if not _HAVE_CRYPTO:
        raise RuntimeError("cryptography package not installed — see docs/AES_CONFIG.md")
    key = base64.b64decode(key_b64) if key_b64 else _key_from_env()
    aes = AESGCM(key)
    pt = aes.decrypt(base64.b64decode(payload["nonce"]),
                     base64.b64decode(payload["ciphertext"]), None)
    return json.loads(pt.decode("utf-8"))
