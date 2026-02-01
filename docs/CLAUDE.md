# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Mises Data Curator** is a Python-based economic data curation tool that automates the workflow of ingesting, cleaning, documenting, and serving economic datasets. It provides two interfaces: CLI and Web (Flask).

The tool integrates with multiple data sources (ILOSTAT, OECD, IMF, World Bank, ECLAC) and uses LLM-powered metadata generation via OpenRouter for automated documentation.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize project structure
python -m src.cli init
```

### Running the Application

**CLI Interface:**
```bash
# Main CLI entry point
python -m src.cli <command>

# Common workflows
python -m src.cli status                    # Check project status
python -m src.cli search <query>            # Search indicators
python -m src.cli pipeline <file> --topic <topic> --source <source>
```

**Web Interface:**
```bash
# Launch Flask web server (check src/web/routes.py for implementation)
python -m src.web  # Entry point needs to be defined
```

### Testing
```bash
# Run simple test files
python test_search.py
python test_api.py
python test_app_init.py

# Test the pipeline with sample data
python -m src.cli pipeline sample_wages_data.csv --topic test --source sample --coverage test
```

## Architecture

### Core Data Flow

The application follows a pipeline architecture:

1. **Ingestion** (`src/ingestion.py`): Abstract `DataSource` base class with concrete implementations for each API (ILOSTAT, OECD, IMF, etc.) and manual uploads
2. **Cleaning** (`src/cleaning.py`): Standardizes country codes, dates, handles missing values
3. **Metadata Generation** (`src/metadata.py`): Uses OpenRouter LLM API to generate documentation, with fallback to templates
4. **Search** (`src/searcher.py`): Queries indicators across sources using `indicators.yaml` mappings

### Module Organization

```
src/
├── cli.py              # Click-based CLI commands
├── config.py           # Configuration manager (YAML + env vars)
├── ingestion.py        # DataSource abstract class + implementations
├── cleaning.py         # DataCleaner for standardization
├── metadata.py         # MetadataGenerator with LLM integration
├── searcher.py         # IndicatorSearcher for discovery
└── web/                # Flask web interface
    └── routes.py       # Blueprint with UI routes + API endpoints
```

### Configuration Files

- **`config.yaml`**: Core settings (directories, topics, sources, cleaning rules, LLM config)
- **`indicators.yaml`**: List of economic indicators with tags for flexible searching (tag-based, not topic-based)
- **`.env`**: API keys (OPENROUTER_API_KEY, OECD_API_KEY, etc.) - never commit this file

### Data Directory Structure

```
01_Raw_Data_Bank/           # Raw data by source (ILOSTAT/, OECD/, etc.)
02_Datasets_Limpios/        # Clean datasets organized by topic
03_Metadata_y_Notas/        # Generated markdown documentation
04_Graficos_Asociados/      # Graphics/visualizations
```

Files follow naming convention: `{topic}_{source}_{coverage}_{start_year}_{end_year}.csv`

### Web Architecture (Flask)

- **Blueprint-based**: `ui_bp` in `src/web/routes.py`
- **SSE for Progress**: `/api/progress/stream` endpoint for real-time updates
- **Navigation**: Consistent across all pages via `NAV_ITEMS` and `base_context()`

## Recent Updates (2026-01)

### OWID API Integration
**Our World in Data now has full API support!**

OWID Grapher API integrated - no more manual CSV downloads:
```bash
python -m src.cli download \
  --source owid \
  --slug life-expectancy \
  --countries "Argentina,Brazil" \
  --start-year 2015 \
  --end-year 2024 \
  --topic libertad_economica
```

**Key points:**
- Uses OWID Grapher chart slugs (from URLs)
- No authentication needed
- Filters by country and time range
- Full pipeline: download → clean → document
- See `OWID_API_INTEGRATION.md` for details

**New class:** `OWIDSource` in `src/ingestion.py:547`

### Tag-Based Search Refactoring
**The indicator system was refactored from topic-based to tag-based search:**

**Old approach (deprecated):**
- Indicators defined as nested dict with manual `topic_indicators` mappings
- Required maintaining topic lists manually
- Search limited to predefined topics

**New approach (current):**
- Indicators are a flat list with searchable tags
- No manual topic mappings needed
- Search by any term, source, or tag
- More flexible and maintainable

**Example indicator structure:**
```yaml
indicators:
  - id: tax_revenue_owid
    source: owid
    name: "Tax Revenue (% GDP)"
    description: "Tax revenue as percentage of GDP"
    tags: [tax, fiscal, government, revenue, impuestos]
    url: "https://ourworldindata.org/taxation"
```

**Key methods in IndicatorSearcher:**
- `search(query)` - Free-text search across all fields
- `search_by_source(source)` - Filter by data source
- `search_by_tag(tag)` - Find indicators with specific tag
- `list_tags()` - Show all available tags

See `REFACTORING_SUMMARY.md` for complete details.

## Key Implementation Patterns

### 1. Abstract DataSource Pattern
All data sources inherit from `DataSource` ABC:
```python
class DataSource(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        pass
```

Implementations: `ManualUpload`, `ILOSTATSource`, `OECDSource`, `IMFSource`, etc.

### 2. Configuration Management
The `Config` class (`src/config.py`) centralizes all configuration:
- Loads `config.yaml` and `indicators.yaml`
- Provides typed getters: `get_directory()`, `get_llm_config()`, `get_indicator()`
- Handles environment variables via `python-dotenv`

### 3. LLM Integration
`MetadataGenerator` uses OpenAI-compatible client for OpenRouter:
```python
import openai
client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)
```

Metadata generation includes caching to avoid duplicate API calls. Use `--force` flag to regenerate.

### 4. Pipeline Composition
Commands like `pipeline` and `download` compose multiple operations:
```python
data = manager.ingest(source, **kwargs)      # Step 1: Fetch
cleaned = cleaner.clean_dataset(data)        # Step 2: Clean
metadata = generator.generate_metadata(...)  # Step 3: Document
```

## Working with Data Sources

### Adding a New Data Source

1. Create a new class in `src/ingestion.py` inheriting from `DataSource`
2. Implement the `fetch()` method with source-specific API logic
3. Register in `DataIngestionManager._get_source()` switch statement
4. Add to `config.yaml` sources list
5. Update `indicators.yaml` with indicator mappings

### Testing API Integration

Use the `search` command to verify indicator mappings:
```bash
python -m src.cli search --source ilostat
python -m src.cli search wage -v  # Verbose output
```

## Common Gotchas

1. **Unicode on Windows**: The CLI sets `sys.stdout` encoding to UTF-8 to handle Spanish metadata
3. **Year Auto-detection**: `DataCleaner.save_clean_dataset()` auto-detects year range if not provided
4. **API Keys**: OpenRouter API key is optional; metadata falls back to template-based generation
5. **File Naming**: All topics/sources should use `snake_case` lowercase for consistency

## Testing Strategy

Currently uses minimal test files (`test_*.py`) for smoke testing. Each file tests a specific component:
- `test_search.py`: Search logic with mock data
- `test_api.py`: API integration tests

## Development Workflow

When adding new features:

1. **For CLI commands**: Add to `src/cli.py` using `@cli.command()` decorator
3. **For web routes**: Add to `src/web/routes.py` blueprint and create corresponding template
4. **For data sources**: Follow the Abstract DataSource Pattern above
5. **For indicators**: Update `indicators.yaml` with new mappings

When modifying the data pipeline (ingestion/cleaning/metadata):
- Changes to cleaning logic affect all datasets
- Test with `pipeline` command on sample data first
- Metadata regeneration requires `--force` flag if content changed

## Important Files

- `src/cli.py:470` - CLI entry point
- `src/config.py:96` - Directory initialization logic
- `indicators.yaml:187` - Topic-to-indicator mappings
- `config.yaml:39` - LLM metadata settings
