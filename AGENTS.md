# AGENTS.md — Agent Guidance for this Repository

This file helps AI agents and contributors work effectively in this Python project (Mises Data Curator).
It is a concise, actionable summary. For an extended reference see docs/AGENTS.md in the repository.


## Design Log Methodology

The project follows a rigorous design log methodology for all significant features and architectural changes.

### Before Making Changes
1. Check design logs in `./design-log/` for existing designs and implementation notes
2. For new features: Create design log first, get approval, then implement
3. Read related design logs to understand context and constraints

### When Creating Design Logs
1. Structure: Background → Problem → Questions and Answers → Design → Implementation Plan → Examples → Trade-offs
2. Be specific: Include file paths, type signatures, validation rules
3. Show examples: Use ✅\❌ for good/bad patterns, include realistic code
4. Explain why: Don't just describe what, explain rationale and trade-offs
5. Ask Questions (in the file): For anything that is not clear, or missing information
6. When answering question: keep the questions, just add answers
7. Be brief: write short explanations and only what most relevant
8. Draw Diagrams: Use mermain inline diagrams when it makes sense

### When Implementing
1. Follow the implementation plan phases from the design log
2. Write tests first or update existing tests to match new behavior
3. Do not Update design log initial section once implementation started
4. Append design log with "Implementation Results" section as you go
5. Document deviations: Explain why implementation differs from design
6. Run tests: Include test results (X/Y passing) in implementation notes
7. After Implementation add a summary of deviations from original design

### When Answering Questions
1. Reference design logs by number when relevant (e.g., "See Design Log #50")
2. Use codebase terminology: ViewState, Contract, phase annotations
3. Show type signatures: This is a Python project
4. Consider backward compatibility: Default to non-breaking changes

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
  - metadata.py — MetadataGenerator: GitHub Copilot SDK integration with template fallback and caching
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
