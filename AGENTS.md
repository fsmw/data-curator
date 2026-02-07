# AGENTS.md — Agent Guidance for this Repository

This file helps AI agents and contributors work effectively in this Python project (Mises Data Curator).
It is a concise, actionable summary. For an extended reference see docs/AGENTS.md in the repository.

## Quick facts

- Language: Python (src/)
- Entry points:
  - CLI: python -m src.cli
  - Web (partial): python -m src.web
- Tests: pytest (tests/)
- Dependencies: requirements.txt
- Main config files: config.yaml, indicators.yaml, .env.example

## Essential commands

- Install dependencies:
  - pip install -r requirements.txt

- Initialize directories:
  - python -m src.cli init --config config.yaml

- Search indicators:
  - python -m src.cli search <query>
  - python -m src.cli search --list-topics
  - python -m src.cli search --source owid

- Ingest (download) data:
  - python -m src.cli ingest --source <manual|owid|ilostat|oecd|imf|worldbank|eclac> [--filepath FILE] [--indicator ID] [--dataset ID] [--database ID] [--countries ARG,BRA,...] [--start-year YYYY] [--end-year YYYY]

- Full pipeline (download → clean → document):
  - python -m src.cli download --source <source> --topic <topic> [--slug|--indicator|--dataset|--database] [--countries ...] --start-year <yy> --end-year <yy> --coverage <coverage>

- Clean local CSV:
  - python -m src.cli clean <input_file> --topic <topic> --source <source>

- Document dataset (metadata generation):
  - python -m src.cli document <file> --topic <topic> --source <source> --url <original_source_url>

- Run web app (partial/for development):
  - python -m src.web

- Run tests:
  - pytest tests/

## Code organization

- src/
  - cli.py — Click-based command-line interface (group commands: init, search, ingest, download, clean, document, pipeline, status)
  - config.py — Config class: loads config.yaml and indicators.yaml, exposes helper methods (get_directory, get_sources, get_topics, get_llm_config, initialize_directories)
  - ingestion.py — DataSource abstract pattern and DataIngestionManager (implements multiple sources: manual, ILOSTAT, OECD, IMF, OWID, WorldBank partial)
  - cleaning.py — DataCleaner: cleaning rules, country-code normalization, year auto-detection, save_clean_dataset
  - metadata.py — MetadataGenerator: LLM integration (OpenRouter/Copilot hints) with template fallback and caching
  - searcher.py — IndicatorSearcher: flat list/tag-based search backed by indicators.yaml
  - web/ — Flask-based web UI (routes, templates, static). Partial/experimental
  - utils/, agents/, rag/, vector_store.py, embeddings.py, etc. — supporting modules

## Naming, style, and conventions

- Python style: PEP8 / snake_case is used throughout
- Dataset file naming enforced by code/docstrings: {topic}_{source}_{coverage}_{start}_{end}.csv (lowercase, snake_case)
- Config access: always use src.config.Config rather than hardcoding paths or strings
- LLM configuration: defined in config.yaml under llm; Config.get_llm_config() returns a provider/config dict

## Important implementation patterns

- Abstract DataSource pattern: create a subclass of DataSource in ingestion.py and register it in DataIngestionManager._get_source()
- Pipeline composition: ingestion → cleaning → metadata generation. CLI orchestrates these steps in download/pipeline commands
- Fallback strategies: metadata has LLM-first then template fallback; DataSources return empty DataFrame with warnings on failure
- Caching: metadata cache on disk (document references .metadata_cache/), raw data saved under configured raw directory (config.yaml directories)

## Tests & debugging

- Tests live under tests/ (unit, manual folders and many test_*.py files)
- Run pytest tests/ to execute tests
- Common debug helpers (ad-hoc python snippets used in docs):
  - python -c "from src.config import Config; print(Config().get_sources())"
  - python -c "from src.searcher import IndicatorSearcher; print(IndicatorSearcher(Config()).list_tags())"

## Observed gotchas

- Windows Unicode: cli.py applies a UTF-8 wrapper for stdout on Windows (see src/cli.py:19-24)
- LLM keys optional: metadata generation supports template fallback if no LLM key is provided
- Year auto-detection: cleaning code auto-detects year range from numeric 4-digit columns
- API formats vary: DataSource subclasses handle SDMX-JSON, REST JSON, Grapher CSV, etc.
- Config files required: config.yaml must exist (Config raises FileNotFoundError otherwise)

## Files and locations to inspect when changing behavior

- CLI behaviors: src/cli.py
- Config loading and directories: src/config.py
- Data ingestion and source implementations: src/ingestion.py
- Cleaning rules and naming logic: src/cleaning.py
- Metadata / LLM integration and caching: src/metadata.py
- Search & indicators: indicators.yaml and src/searcher.py
- Tests: tests/ (see test files for expected behaviors and examples)
- Extended agent guidance: docs/AGENTS.md (detailed reference)

## Safety and constraints for agents

- Do not invent new top-level CLI commands without updating tests and docs
- Always use the Config class for directory/file paths
- Respect existing file naming conventions when saving datasets
- Avoid adding secrets to repo; use .env or environment variables (see .env.example)

## Next steps for agents (suggested starter tasks)

- Run the test suite: pytest tests/
- Inspect failing tests and add/update unit tests when modifying code
- To add a new data source: implement DataSource subclass, register in DataIngestionManager, add indicators in indicators.yaml, and add tests
- To change LLM behavior: update config.yaml llm section and adapt src/metadata.py accordingly


---
Generated by an automated analysis of repository contents — only documents observed files and behaviors. See docs/AGENTS.md for a longer, narrative reference.
