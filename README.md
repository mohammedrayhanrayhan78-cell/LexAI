# Production-Ready AI Legal Assistant

Embeddings now use Gemini `gemini-embedding-2` at 768 dimensions. Existing documents indexed with `text-embedding-004` (or any older model) must be **re-uploaded** so their vectors match the new model.

## Quickstart

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env