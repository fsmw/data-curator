# Design Log 01 — System Architecture Foundations

## Background
The project evolved from a CLI-first data curation tool into a mixed CLI + Flask web platform with AI-assisted workflows.

## Problem
There was no explicit design log history, so core architecture decisions were implicit in code and hard to track.

## Questions and Answers
- Q: Is this monolith or microservices?
  - A: Monolith Python app with modular subsystems under `src/` and Flask blueprints (`src/web`).
- Q: Is configuration centralized?
  - A: Yes, `src/config.py` provides directory, source, topic, LLM, and RAG configuration.

## Design
1. **Single Python codebase, multiple entrypoints**
   - CLI: `python -m src.cli`
   - Web: `python -m src.web`
2. **Config-driven architecture**
   - `Config` loads `config.yaml` + `indicators.yaml` and resolves data directories.
3. **Pipeline composition**
   - Ingestion → Cleaning → Metadata → Catalog indexing (`src/pipeline.py`).
4. **Web separation**
   - UI routes (`src/web/routes.py`) and API routes (`src/web/api/*`) split by concern.

## Implementation Plan
- [x] Keep architecture modular by subsystem (`ingestion`, `cleaning`, `metadata`, `dataset_catalog`, `web`, `agents`).
- [x] Keep path resolution via `Config.get_directory(...)` to avoid hardcoded paths.
- [x] Maintain CLI and Web as first-class interfaces.

## Examples
- ✅ `PipelineRunner` orchestrates validation, metadata generation, and catalog indexing in one flow (`src/pipeline.py`).
- ✅ `create_app()` configures auth, admin, API, i18n in one app bootstrap (`src/web/__init__.py`).
- ❌ Direct filesystem paths hardcoded in feature modules.

## Trade-offs
- **Pros:** Simpler deployment, easier local debugging, shared domain logic across CLI/Web.
- **Cons:** Large codebase coupling risk; requires discipline to preserve module boundaries.

