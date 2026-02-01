# AGENTS.md — Workspace Agent Guidance (Root)

This repository already contains an extensive agents guide at `docs/AGENTS.md` (recommended primary reference).

Purpose
- Give concise, repo-root guidance for AI agents working in this repository.

Quick facts
- Project: Mises Data Curator (Python) — CLI, Web (Flask)
- Key source files: `src/cli.py`, `src/ingestion.py`, `src/cleaning.py`, `src/metadata.py`, `src/searcher.py`
- Config files: `config.yaml`, `indicators.yaml`, `.env` (not committed)
- Data dirs: `01_Raw_Data_Bank/`, `02_Datasets_Limpios/`, `03_Metadata_y_Notas/`, `04_Graficos_Asociados/`

Primary guidance for agents
- Read `docs/AGENTS.md` first. It is the canonical, detailed instruction set for contributors and agents.
- Preserve repo conventions: PEP8, snake_case, docstrings in English.
- Use the `Config` class (`src/config.py`) for all configuration access. Do not hardcode paths or API keys.
- Follow the Abstract `DataSource` pattern when adding sources (`src/ingestion.py`). Register new sources in `DataIngestionManager._get_source()`.
- For CLI changes, add commands via Click in `src/cli.py` following existing patterns.
- For metadata/LLM work, prefer using the existing OpenRouter-compatible integration. Respect caching (`.metadata_cache/`) and use `--force` to regenerate.

Agent workflow rules
- Always run a quick search for `AGENTS.md`, `CLAUDE.md`, `README.md`, and `config.yaml` before making changes.
- When editing files, keep changes minimal and focused. Update docs and tests for any behavior changes.
- Never commit secrets. If a change requires API keys, use `.env.example` and instruct the user to populate `.env`.
- Respect the `docs/AGENTS.md` task difficulty and time estimates when proposing work (Easy/Medium/Hard sections).

On tests and validation
- The repo has minimal tests. Add unit tests in `tests/` when adding or modifying behavior that can and should be covered.
- Suggested commands (developer): `pytest tests/` and `python -m src.cli status`

What to update here
- Keep this root `AGENTS.md` short and current — point to `docs/AGENTS.md` for deep guidance.
- When `docs/AGENTS.md` changes significantly, update this file to reflect high-level changes and new entry points.

Pointers (quick links)
- `docs/AGENTS.md` — Full agent guide (canonical)
- `docs/CLAUDE.md` — Additional development instructions
- `README.md` — Project overview and quickstart
- `config.yaml` — Master configuration
- `indicators.yaml` — Tag-based indicators list

If you're an agent: begin by reading `docs/AGENTS.md` and then ask for specific tasks or permissions before making repo-wide changes.
