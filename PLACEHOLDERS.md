# PLACEHOLDERS — needs Evan's hands / decisions

Everything from the v0.4 manifest + roadmap is wired in v0.5 (Ollama
integration, Graph RAG, real Qdrant/Neo4j/OpenSearch adapters, dashboard,
media metadata, local distributed workers, Docker + CI). What genuinely
remains:

- [ ] **Live servers for the adapters + Ollama:** the clients are
      code-complete and mock-tested, but no Qdrant/Neo4j/OpenSearch
      server — and no Ollama server — runs in the dev environment, and
      Docker isn't installed there. On Evan's machine:
      `docker compose up -d` brings the stores up; install Ollama +
      `ollama pull llama3.1` for generative answers. First live run
      against real servers is still unverified.
- [ ] **Media transcription / OCR:** media ingestion extracts real
      metadata (dimensions, WAV duration, hashes), but transcription
      and OCR remain extractor slots — wiring whisper/OCR adds heavy
      deps; Evan's call.
- [ ] **Scanned/image PDFs:** built-in extractor handles text-layer
      PDFs only; scanned PDFs need pypdf + OCR (same decision as above).
- [ ] **Neural embeddings (optional):** hashing embedder is the default;
      Ollama embeddings are wired. sentence-transformers is a drop-in
      behind `argus.embeddings.Embedder` if Evan wants it.
- [ ] **ARGUS_CONFIG_KEY:** if Evan wants encrypted config, he generates
      the key (`python -m argus.cli keygen`) and stores it in his own
      password manager / env — never in this repo.
- [ ] **GitHub push:** v0.5 is committed locally; pushing to
      github.com/nave433-blip needs his go (parent agent handles it).
