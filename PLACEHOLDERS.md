# PLACEHOLDERS — needs Evan's hands / decisions

- [ ] **Real embedding model (optional upgrade):** core ships with the
      deterministic hashing embedder. To upgrade: install
      sentence-transformers (or wire Ollama embeddings) and implement
      `argus.embeddings.Embedder` — pipeline code does not change.
- [ ] **Qdrant / Neo4j servers:** adapters are interfaces only. Wiring
      them needs the servers running (Docker) and connection details —
      Evan's call on whether local Docker is worth it vs SQLite.
- [ ] **Ollama for ORACLE generative answers:** roadmap item; needs
      Ollama installed + a model pulled on Evan's machine.
- [ ] **PDF quality:** built-in extractor handles simple text-layer
      PDFs. Scanned/image PDFs need pypdf + OCR — install decision is
      Evan's (adds heavy deps).
- [ ] **ARGUS_CONFIG_KEY:** if Evan wants encrypted config, he generates
      the key (`python -m argus.cli keygen`) and stores it in his own
      password manager / env — never in this repo.
- [ ] **GitHub push:** repo is committed locally; pushing to
      github.com/nave433-blip needs his go (parent agent handles it).
