# AES-128-GCM encrypted config (`aes128_configuration` feature)

ARGUS can store its own configuration (adapter URLs, local paths, any
future API endpoints) encrypted at rest with AES-128-GCM.

- Generate a key: `python -m argus.cli keygen`
- Keep it in the `ARGUS_CONFIG_KEY` environment variable. It is never
  written to disk by ARGUS.
- Encrypt/decrypt via `argus.config_crypto.encrypt_config /
  decrypt_config` (see tests for a round-trip example).
- Requires the `cryptography` package (in requirements.txt and in the
  project venv). Without it, the functions raise a clear error and the
  rest of ARGUS runs normally — encryption is opt-in, for ARGUS's own
  config only.
