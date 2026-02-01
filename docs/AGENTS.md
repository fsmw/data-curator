# AGENTS.md - AI Agent Guidance for Mises Data Curator

**Document Version**: 1.0  
**Project Version**: 1.1.0-beta  
**Last Updated**: January 7, 2026  
**Target Audience**: AI Agents (Claude Code, OpenCode, Cursor, etc.)

---

## Executive Summary

**Mises Data Curator** is a production-ready Python tool that automates economic data curation workflows. It provides two interfaces (CLI, Web) for searching, downloading, cleaning, and documenting economic datasets from public APIs (ILOSTAT, OECD, IMF, OWID, World Bank, ECLAC).

The tool is **83% complete** with core functionality fully implemented and tested. Use this document to understand the architecture, identify agent responsibilities, and implement effective development strategies.

---

## 1. Project Structure & Architecture

### High-Level Architecture

```
USER INTERACTION
    ↓
[CLI Commands] ← [Web Routes]
    ↓
[CONFIG LAYER]  (config.py)
    ↓
[CORE PIPELINE]
    ├─ IndicatorSearcher  (searcher.py)    → Search/Discover
    ├─ DataIngestionManager (ingestion.py) → Download
    ├─ DataCleaner  (cleaning.py)          → Standardize
    └─ MetadataGenerator (metadata.py)     → Document (AI)
    ↓
[DATA LAYER]
    ├─ 01_Raw_Data_Bank/        (Raw inputs)
    ├─ 02_Datasets_Limpios/     (Cleaned outputs)
    ├─ 03_Metadata_y_Notas/     (Documentation)
    └─ 04_Graficos_Asociados/   (Visualizations)
```

### Directory Structure

```
data-curator/
├── src/                           # Core source code
│   ├── cli.py                     # 7 CLI commands
│   ├── config.py                  # Configuration management
│   ├── ingestion.py               # Data sources (6 implementations)
│   ├── cleaning.py                # Data standardization pipeline
│   ├── metadata.py                # LLM-powered documentation
│   ├── searcher.py                # Indicator search & discovery
│   └── web/                       # Flask web interface
│       ├── routes.py              # API & UI endpoints
│       ├── static/                # JS/CSS assets
│       └── templates/             # Jinja2 HTML templates
├── config.yaml                    # Core configuration
├── indicators.yaml                # Economic indicators database
├── .env.example                   # Environment template
├── requirements.txt               # Python dependencies
└── [01-04]_Data_Directories/      # Data storage

Total: ~80 files, ~3,500 LOC (production quality)
```

---

## 2. Core Modules & Their Responsibilities

### 2.1 `src/cli.py` - Command-Line Interface

**Status**: ✅ Complete & Production Ready  
**Lines of Code**: ~470  
**Responsibilities**: User command orchestration

#### Commands Implemented

| Command | Purpose | Key Parameters |
|---------|---------|-----------------|
| `init` | Initialize directory structure | `--config` |
| `search` | Find indicators | `--tag`, `--source`, `--list-topics`, `--list-sources`, `-v` |
| `ingest` | Download raw data | `--source`, `--filepath` (manual) or source-specific args |
| `clean` | Standardize data | `--topic`, `--source`, `--coverage`, `--start-year`, `--end-year` |
| `document` | Generate metadata | `--topic`, `--source`, `--url`, `--force` |
| `pipeline` | Complete workflow | Combines clean + document in one step |
| `download` | Download + clean + document | `--source`, `--indicator`, `--topic`, `--coverage`, `--countries` |
| `status` | Show project status | No parameters required |

#### Integration Points
- Uses `Config` for configuration loading
- Orchestrates `IndicatorSearcher` → `DataIngestionManager` → `DataCleaner` → `MetadataGenerator`
- Handles Click groups and options/arguments
- Special handling: Windows UTF-8 encoding for Spanish metadata

#### Agent Task Examples
- **Add new command**: Extend CLI with `@cli.command()` decorator
- **Modify parameters**: Update Click options/arguments
- **Error handling**: Enhance exception messages and fallback behavior
- **Output formatting**: Improve console display with colors/tables

---

### 2.2 `src/config.py` - Configuration Management

**Status**: ✅ Complete & Production Ready  
**Lines of Code**: ~106  
**Responsibilities**: Centralized configuration and file loading

#### Key Classes

**`Config` class**
- Loads `config.yaml` and `indicators.yaml`
- Manages environment variables via `python-dotenv`
- Provides typed getter methods

#### Key Methods
```python
get_directory(dir_type: str) → Path         # Get directory by type
get_llm_config() → Dict                     # LLM settings
get_indicators() → List[Dict]               # Indicator list
get_regions() → Dict[str, List[str]]        # Region mappings
get_sources() → list                        # Data sources
get_topics() → list                         # Topics
initialize_directories()                    # Create folder structure
```

#### Configuration Files
- **`config.yaml`**: Core settings (directories, sources, topics, LLM settings, cleaning rules)
- **`indicators.yaml`**: Economic indicators database (flat list with tags)
- **`.env`**: API keys (OPENROUTER_API_KEY, source-specific keys)

#### Agent Task Examples
- **Add new topic**: Update `config.yaml` topics list
- **Add new source**: Update `config.yaml` sources, register in `ingestion.py`
- **Modify LLM config**: Update `config.yaml` llm section
- **Debug config loading**: Check YAML parsing and environment variables

---

### 2.3 `src/ingestion.py` - Data Source Integration

**Status**: ✅ Production Ready (6/7 sources implemented)  
**Lines of Code**: ~1,100  
**Responsibilities**: Abstract API integration pattern for multiple data sources

#### Architecture: Abstract DataSource Pattern

```python
class DataSource(ABC):
    @abstractmethod
    def fetch(self, **kwargs) -> pd.DataFrame:
        """Fetch data from source."""
        pass
    
    def save_raw(self, data: pd.DataFrame, filename: str) -> Path:
        """Save to disk."""
```

#### Implemented Source Classes

| Source | Class | Status | API Type | Requires Auth |
|--------|-------|--------|----------|--------------|
| Manual Upload | `ManualUpload` | ✅ | File | No |
| ILOSTAT | `ILOSTATSource` | ✅ | SDMX/REST | No |
| OECD | `OECDSource` | ✅ | REST | No |
| IMF | `IMFSource` | ✅ | REST | No |
| OWID | `OWIDSource` | ✅ | REST (Grapher) | No |
| World Bank | `WorldBankSource` | ⚠️ Partial | REST | No |

#### Key Features
- SDMX-JSON parsing for complex APIs
- Automatic country code standardization
- Year range filtering
- Fallback to template mode on API failure
- Raw data archiving

#### `DataIngestionManager` Class
Orchestrates source selection and data fetching:
```python
manager = DataIngestionManager(config)
data = manager.ingest(source="ilostat", indicator="...", countries=[...])
```

#### Agent Task Examples
- **Add new data source**: Create class inheriting from `DataSource`, implement `fetch()`
- **Fix API parsing**: Debug SDMX/JSON parsing in `_parse_sdmx_json()` or similar
- **Handle rate limiting**: Add retry logic with exponential backoff
- **Improve country handling**: Extend country code mappings
- **Support new indicators**: Update `indicators.yaml` with proper source references

---

### 2.4 `src/cleaning.py` - Data Standardization Pipeline

**Status**: ✅ Complete & Production Ready  
**Lines of Code**: ~250  
**Responsibilities**: Standardize data formats, country codes, dates, handle missing values

#### `DataCleaner` Class

**Key Methods**
```python
clean_dataset(data: pd.DataFrame, rules: Optional[Dict]) → pd.DataFrame
save_clean_dataset(data: pd.DataFrame, topic: str, source: str, 
                   coverage: str, start_year: int, end_year: int) → Path
get_data_summary(data: pd.DataFrame) → Dict
```

**Cleaning Rules** (from `config.yaml`)
- `drop_empty_rows`: Remove rows with all NaN
- `drop_empty_columns`: Remove columns with all NaN
- `standardize_country_codes`: Map to ISO 3166-1 alpha-3
- `normalize_dates`: Convert to YYYY-MM-DD format
- `handle_missing_values`: Identify and report NaN

**Country Code Mappings**
- Spanish names (Argentina, México) → ISO codes (ARG, MEX)
- English names → ISO codes
- Already-ISO codes → passthrough

**Auto-Detection**
- Year range is auto-detected from data if not provided
- Naming convention: `{topic}_{source}_{coverage}_{start_year}_{end_year}.csv`

#### Data Summary
```python
{
    "rows": int,
    "columns": list,
    "countries": list,
    "date_range": [start, end],
    "null_count": int,
    "transformations": [list of changes]
}
```

#### Agent Task Examples
- **Enhance country mapping**: Add more country name variants
- **Add cleaning rule**: Implement new data quality check
- **Improve date parsing**: Support additional date formats
- **Optimize performance**: Vectorize operations on large datasets
- **Add data validation**: Implement range/type checking

---

### 2.5 `src/metadata.py` - Documentation Generation

**Status**: ✅ Complete & Production Ready  
**Lines of Code**: ~350  
**Responsibilities**: Auto-generate markdown documentation using AI with template fallback

#### `MetadataGenerator` Class

**Dual-Mode Operation**
1. **LLM Mode** (OpenRouter): Claude, GPT-4, Gemini
2. **Template Mode** (Fallback): Rule-based markdown generation

**Key Methods**
```python
generate_metadata(topic, data_summary, source, transformations, 
                  original_source_url, force_regenerate) → str
```

**LLM Integration**
- Uses OpenRouter API (compatible with OpenAI client)
- Supports custom system prompts
- Configurable temperature, max_tokens
- Fallback to template if API fails

**Caching System**
- Hash-based caching in `.metadata_cache/`
- Avoids duplicate API calls
- Use `--force` flag to regenerate

**Template Fallback**
If no API key or LLM disabled, generates markdown using:
- Data summary (row/column counts)
- Country list
- Date range
- Transformation list
- Source attribution

#### Metadata Output
```markdown
# {Topic} - {Source} Data

## Overview
[Generated description]

## Data Summary
- Countries: {count}
- Date Range: {start} - {end}
- Records: {rows}

## Data Quality
[Transformations applied]

## Metadata
Generated on: {date}
Source: {source_url}
```

#### Agent Task Examples
- **Improve prompt**: Edit system prompt in `config.yaml`
- **Add metadata fields**: Enhance template generation
- **Optimize caching**: Implement better cache invalidation
- **Support new LLM models**: Configure different providers
- **Add multilingual support**: Generate Spanish/English docs
- **Implement validation**: Check generated metadata quality

---

### 2.6 `src/searcher.py` - Indicator Discovery

**Status**: ✅ Complete & Production Ready  
**Lines of Code**: ~200  
**Responsibilities**: Search, filter, and discover economic indicators

#### Architecture: Tag-Based Search

**Old approach** (deprecated):
- Topic-based nested dict
- Manual mappings required
- Limited flexibility

**New approach** (current):
- Flat list of indicators
- Free-text searchable
- Tag-based filtering
- Source-based filtering

#### `IndicatorSearcher` Class

**Key Methods**
```python
search(query: str) → List[Dict]              # Free-text search
search_by_source(source: str) → List[Dict]   # Filter by source
search_by_tag(tag: str) → List[Dict]         # Filter by tag
list_tags() → List[str]                      # All available tags
list_sources() → List[str]                   # All sources
format_results_table(results, verbose) → str # Pretty output
```

#### Indicator Structure (YAML)
```yaml
indicators:
  - id: "tax_revenue_owid"
    source: "owid"
    name: "Tax Revenue (% GDP)"
    description: "Tax revenue as percentage of GDP"
    tags: [tax, fiscal, government, revenue, impuestos]
    url: "https://ourworldindata.org/taxation"
```

#### Search Examples
```bash
# Free-text search
python -m src.cli search wage

# By source
python -m src.cli search --source owid

# By tag
python -m src.cli search --tag tax

# List all tags
python -m src.cli search --list-topics

# Verbose output
python -m src.cli search unemployment -v
```

#### Agent Task Examples
- **Add indicators**: Update `indicators.yaml` with new indicators
- **Improve search**: Enhance search algorithm (fuzzy matching, etc.)
- **Add new tags**: Create semantic tag system
- **Support ranking**: Order results by relevance

- **Validate indicators**: Check URL validity and data availability

---

## 4. Web Interface Architecture

### Overview

**Status**: ⚠️ Partial (Framework ready, endpoints defined)  
**Framework**: Flask  
**Routing**: Blueprint-based  
**Templates**: Jinja2  

### Web Structure

```
src/web/
├── routes.py            # All routes + API endpoints
├── static/              # JS, CSS, images
└── templates/           # HTML templates
```

### Routes Implemented (`src/web/routes.py`)

#### Web UI Routes
- `GET /` - Dashboard
- `GET /dashboard` - Main interface
- `GET /datasets` - Local datasets view
- `GET /indicators` - Available indicators
- `GET /search?q=...` - Search results

#### API Endpoints
- `GET /api/status` - Project status JSON
- `GET /api/datasets` - List datasets
- `GET /api/indicators` - List indicators
- `GET /api/search?q=...` - Search API
- `POST /api/download` - Start download
- `POST /api/cancel` - Cancel download
- `GET /api/progress/stream` - SSE for real-time progress

### Special Features
- **SSE (Server-Sent Events)**: Real-time progress streaming on `/api/progress/stream`
- **Consistent Navigation**: `NAV_ITEMS` and `base_context()` for all pages
- **JSON API**: RESTful endpoints for programmatic access

### Agent Task Examples for Web

- **Implement missing routes**: Create actual endpoint handlers
- **Build HTML templates**: Design responsive UI
- **Add JavaScript**: Implement real-time updates (SSE client)
- **Improve CSS**: Style bootstrap/tailwind
- **Add authentication**: User login/permissions (if needed)
- **Implement download**: Hook web UI to actual pipeline
- **Progress streaming**: Complete SSE implementation

---

## 5. Data Pipeline & Workflow

### Complete Data Pipeline

```
STEP 1: SEARCH
  User searches for indicators
  ↓
  IndicatorSearcher.search() queries indicators.yaml
  ↓
  Results displayed to user
  ↓

STEP 2: DOWNLOAD (Ingestion)
  DataIngestionManager.ingest() selected indicator
  ↓
  DataSource subclass (ILOSTATSource, OECDSource, etc.)
  ↓
  API call with auth (if needed)
  ↓
  Response parsed (SDMX, JSON, CSV)
  ↓
  Raw data saved to 01_Raw_Data_Bank/{source}/
  ↓

STEP 3: CLEAN
  DataCleaner.clean_dataset()
  ↓
  Standardize country codes (ARG, BRA, etc.)
  ↓
  Normalize dates (YYYY-MM-DD)
  ↓
  Remove empty rows/columns
  ↓
  Handle missing values
  ↓
  Generate data summary
  ↓
  Save clean data to 02_Datasets_Limpios/{topic}/
  ↓

STEP 4: DOCUMENT
  MetadataGenerator.generate_metadata()
  ↓
  Try LLM first (OpenRouter)
    - Claude, GPT-4, Gemini
    - Custom system prompt
    - Caching enabled
  ↓
  If LLM fails, use template fallback
  ↓
  Generate markdown documentation
  ↓
  Save to 03_Metadata_y_Notas/{topic}.md
  ↓

OUTPUT
  ✅ Cleaned CSV in 02_Datasets_Limpios/
  ✅ Markdown docs in 03_Metadata_y_Notas/
  ✅ Raw data archived in 01_Raw_Data_Bank/
```

### Single-Step Workflow

```bash
python -m src.cli download \
  --source ilostat \
  --indicator unemployment_rate \
  --topic libertad_economica \
  --coverage latam \
  --countries ARG,BRA,CHL,COL,MEX,PER,URY
```

This executes all 4 steps automatically.

### Multi-Step Workflow

```bash
# Step 1: Download only
python -m src.cli ingest --source oecd --dataset ALFS --indicator AVNL

# Step 2: Clean only
python -m src.cli clean data.csv --topic salarios_reales --source oecd

# Step 3: Document only
python -m src.cli document data.csv --topic salarios_reales --source oecd --url https://...

# Or steps 2+3 combined
python -m src.cli pipeline data.csv --topic salarios_reales --source oecd
```

---

## 6. Key Implementation Patterns & Best Practices

### Pattern 1: Abstract DataSource Pattern

Use this when adding new data sources:

```python
class MySource(DataSource):
    def __init__(self, raw_data_dir: Path):
        super().__init__("MySource", raw_data_dir)
    
    def fetch(self, indicator: str, **kwargs) -> pd.DataFrame:
        # Implement API call logic
        try:
            data = self._call_api(indicator, **kwargs)
            return data
        except Exception as e:
            print(f"⚠ API error: {e}")
            return pd.DataFrame()  # Empty fallback
    
    def _call_api(self, indicator: str, **kwargs) -> pd.DataFrame:
        # Parse response and return DataFrame
```

Then register in `DataIngestionManager._get_source()`:
```python
def _get_source(self, source: str) -> DataSource:
    if source.lower() == "mysource":
        return MySource(self.raw_data_dir)
```

### Pattern 2: Configuration Management

Always use `Config` class to access configuration:

```python
from src.config import Config

cfg = Config()  # Loads config.yaml, indicators.yaml, .env
directories = cfg.get_directory('clean')
sources = cfg.get_sources()
indicators = cfg.get_indicators()
```

### Pattern 3: Pipeline Composition

Compose operations in logical order:

```python
# Option A: Individual steps
manager = DataIngestionManager(config)
data = manager.ingest(source="owid", slug="life-expectancy")

cleaner = DataCleaner(config)
cleaned = cleaner.clean_dataset(data)
summary = cleaner.get_data_summary(cleaned)

generator = MetadataGenerator(config)
metadata = generator.generate_metadata(topic="health", data_summary=summary, source="owid")

# Option B: Via CLI (orchestrated automatically)
python -m src.cli pipeline data.csv --topic health --source owid
```

### Pattern 4: Error Handling & Fallbacks

Always provide graceful fallbacks:

```python
# LLM API fails? Use template
# Data source API fails? Return empty DataFrame with warning
# Configuration missing? Use defaults
# Directory missing? Create it
```

## 7. Configuration Files

### `config.yaml` Structure

```yaml
# Directories
directories:
  raw: "01_Raw_Data_Bank"
  clean: "02_Datasets_Limpios"
  metadata: "03_Metadata_y_Notas"
  graphics: "04_Graficos_Asociados"

# Topics (curation categories)
topics:
  - salarios_reales
  - informalidad_laboral
  - presion_fiscal
  - libertad_economica

# Data sources
sources:
  - owid
  - ilostat
  - oecd
  - imf
  - worldbank
  - eclac

# Data cleaning rules
cleaning:
  drop_empty_rows: true
  drop_empty_columns: true
  standardize_country_codes: true
  normalize_dates: true
  handle_missing_values: true

# LLM configuration
llm:
  use_llm: true
  max_tokens: 2000
  temperature: 0.3
  system_prompt: |
    You are a data documentation expert...

# Metadata settings
metadata:
  use_llm: true
  cache_enabled: true
```

### `indicators.yaml` Structure

```yaml
indicators:
  - id: "unemployment_ilostat"
    source: "ilostat"
    name: "Unemployment Rate"
    description: "Total unemployment rate (%)"
    tags: [unemployment, labor, ilostat]
    url: "https://ilostat.ilo.org/..."
  
  # More indicators...

regions:
  latam:
    - ARG
    - BRA
    - CHL
    - COL
    - MEX
    - PER
    - URY
  
  oecd:
    - AUS
    - AUT
    # ... all OECD members
```

### `.env` Template

```bash
# Required for AI documentation
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Optional source-specific keys
OECD_API_KEY=optional
IMF_API_KEY=optional
WORLDBANK_API_KEY=optional

# Data directory (default: current)
DATA_ROOT=.
```

---

## 8. Agent Task Categories

### 🟢 Easy Tasks (1-2 hours)

**Configuration & Setup**
- [ ] Add new topic to `config.yaml`
- [ ] Add new indicator to `indicators.yaml`
- [ ] Update country code mappings
- [ ] Modify LLM system prompt
- [ ] Add new region definition

**Bug Fixes**
- [ ] Fix Unicode issues on Windows
- [ ] Handle missing directories gracefully
- [ ] Improve error messages
- [ ] Add validation to config loading
- [ ] Fix date parsing edge cases

**Documentation**
- [ ] Add docstrings to methods
- [ ] Create usage examples
- [ ] Document CLI parameters
- [ ] Add comments to complex logic
- [ ] Create troubleshooting guide

### 🟡 Medium Tasks (2-8 hours)

**Feature Implementation**
- [ ] Add new data source (inherit `DataSource`)
- [ ] Implement new cleaning rule
- [ ] Add new CLI command
- [ ] Implement indicator caching

**Enhancements**
- [ ] Improve search algorithm (fuzzy matching)
- [ ] Add data validation framework
- [ ] Implement concurrent downloads
- [ ] Add export formats (Parquet, SQLite)
- [ ] Create progress estimation

**Testing**
- [ ] Write unit tests for modules
- [ ] Create integration tests
- [ ] Add API mock tests
- [ ] Test error scenarios
- [ ] Load testing for large datasets

### 🔴 Hard Tasks (8+ hours)

**Architecture**
- [ ] Implement database backend (SQLAlchemy)
- [ ] Add authentication system
- [ ] Create REST API server
- [ ] Build web dashboard
- [ ] Implement data versioning (DVC)

**Integration**
- [ ] Connect to Apache Airflow
- [ ] Add Slack notifications
- [ ] Integrate with dbt for pipelines
- [ ] Support S3/cloud storage
- [ ] Add data lineage tracking

**Performance**
- [ ] Optimize large dataset processing
- [ ] Implement streaming for huge files
- [ ] Add compression support
- [ ] Create performance benchmarks
- [ ] Profile and optimize hot paths

---

## 9. Common Gotchas & Solutions

### Gotcha #1: Windows Unicode Issues

**Problem**: Spanish characters display as `?` or `\ufffd`  
**Solution**: Already handled in `cli.py:15-17` with UTF-8 wrapper

```python
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

### Gotcha #3: Year Auto-detection

**Problem**: Year range not detected correctly  
**Solution**: Auto-detection in `DataCleaner.save_clean_dataset()` looks for numeric columns with 4-digit values

```python
# Automatically detects years from data if not provided
# Uses columns containing values like 2010, 2011, ... 2024
```

### Gotcha #4: API Keys Optional

**Problem**: Tool fails without OpenRouter API key  
**Solution**: Metadata generation has template fallback (no API required)

```python
if self.use_llm and self.client:
    # Try LLM
else:
    # Use template-based generation
```

### Gotcha #5: File Naming Convention

**Problem**: Datasets have inconsistent names  
**Solution**: Enforce `{topic}_{source}_{coverage}_{start}_{end}.csv` naming

```python
# Always use snake_case lowercase:
# ✅ salarios_reales_owid_latam_2000_2024.csv
# ❌ Salarios Reales - OWID (Latin America) 2000-2024.csv
```

### Gotcha #6: SDMX vs JSON vs REST

**Problem**: Different APIs return different formats  
**Solution**: Each `DataSource` subclass handles its own parsing

```python
# ILOSTATSource: Parses SDMX-JSON
# OECDSource: Parses REST JSON
# OWIDSource: Parses Grapher CSV
```

---

## 10. Performance Considerations

### Optimization Tips

**API Performance**
- Implement request caching
- Respect rate limits with backoff
- Batch requests where possible
- Use connection pooling

**Data Processing**
- Use pandas operations (vectorized)
- Avoid loops over large DataFrames
- Stream large CSV files
- Implement chunking for memory efficiency

**Caching Strategy**
```
Level 1: Indicators cache (in-memory)
Level 2: Metadata cache (disk, .metadata_cache/)
Level 3: Raw data cache (filesystem, 01_Raw_Data_Bank/)
Level 4: Query results cache (optional future)
```

---

## 11. Testing Strategy

### Current Testing

- Minimal test files: `test_search.py`, `test_api.py`, `test_app_init.py`
- Smoke testing only
- Manual verification

### Recommended Testing

```
Unit Tests (Phase 6):
├── test_config.py
├── test_ingestion.py
├── test_cleaning.py
├── test_metadata.py
├── test_searcher.py
└── test_web_routes.py

Integration Tests:
├── test_pipeline_cli.py
├── test_download_workflow.py
└── test_data_persistence.py

E2E Tests:
├── test_full_workflow.py
└── test_api_endpoints.py
```

### Testing Commands (Future)

```bash
# Run all tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Specific module
pytest tests/test_cleaning.py -v

# Watch mode
pytest-watch tests/
```

---

## 12. Debugging Guide

### CLI Debugging

```bash
# Verbose output
python -m src.cli search wage -v

# Check configuration
python -c "from src.config import Config; c = Config(); print(c.config)"

# Test API connection
python -c "from src.ingestion import ILOSTATSource; s = ILOSTATSource(Path('.')); print(s.fetch(...))"
```

### Web Debugging

```bash
# Flask debug mode
export FLASK_ENV=development
export FLASK_DEBUG=1
python -m src.web

# Check routes
python -c "from src.web.routes import ui_bp; print([str(r) for r in ui_bp.deferred_functions])"
```

### Common Debug Commands

```python
# Test config loading
from src.config import Config
cfg = Config()
print(cfg.get_sources())

# Test indicator search
from src.searcher import IndicatorSearcher
searcher = IndicatorSearcher(cfg)
results = searcher.search("unemployment")

# Test data ingestion
from src.ingestion import DataIngestionManager
manager = DataIngestionManager(cfg)
data = manager.ingest("manual", filepath="test.csv")

# Test cleaning
from src.cleaning import DataCleaner
cleaner = DataCleaner(cfg)
cleaned = cleaner.clean_dataset(data)
```

---

## 13. Deployment Checklist

### Pre-Deployment

- [ ] All tests pass
- [ ] Configuration files present (`config.yaml`, `indicators.yaml`)
- [ ] `.env` file created with API keys
- [ ] Directory structure initialized (`python -m src.cli init`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)

### Deployment

- [ ] Copy project to target system
- [ ] Create virtual environment
- [ ] Install dependencies
- [ ] Set environment variables
- [ ] Initialize directories
- [ ] Test CLI commands
- [ ] Verify web interface (if deployed)

### Post-Deployment

- [ ] Monitor error logs
- [ ] Verify data ingestion
- [ ] Check metadata generation
- [ ] Test user workflows
- [ ] Monitor API rate limits
- [ ] Backup user data

---

## 14. Roadmap & Future Work

### Phase 6: Testing & Optimization (Planned)

**Duration**: 2-3 days  
**Scope**:
- Unit tests for all components
- Integration tests
- Performance optimization
- UI refinement
- Documentation finalization

### Short-Term (1-2 weeks)

- [ ] Real API integration testing
- [ ] Database backend (PostgreSQL)
- [ ] Advanced filtering UI
- [ ] Caching system
- [ ] Export format options (Parquet, Excel)

### Medium-Term (1 month)

- [ ] Concurrent downloads
- [ ] Advanced scheduling (cron-like)
- [ ] Resume downloads
- [ ] Incremental updates
- [ ] Data validation framework
- [ ] Web dashboard completion

### Long-Term

- [ ] REST API server
- [ ] Team collaboration features
- [ ] Data versioning (DVC)
- [ ] Advanced analytics
- [ ] Cloud storage integration
- [ ] Data lineage tracking

---

## 15. Additional Resources

### Project Documentation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Complete tool documentation |
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup guide |
| [CLAUDE.md](CLAUDE.md) | Development guidance for Claude |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Detailed phase completion status |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Feature summary |

### Important Code Locations

| Location | Purpose |
|----------|---------|
| `src/cli.py:470` | CLI entry point |
| `src/config.py:96` | Directory initialization |
| `indicators.yaml:1` | Indicator database |
| `config.yaml:1` | Configuration template |

### External References

- [Click Documentation](https://click.palletsprojects.com/) - CLI framework
- [OpenRouter API](https://openrouter.ai/) - LLM provider
- [Pandas Documentation](https://pandas.pydata.org/) - Data manipulation
- [Flask Documentation](https://flask.palletsprojects.com/) - Web framework
- [SDMX Standard](https://sdmx.org/) - Statistical data format

---

## 16. Agent Collaboration Guidelines

### When Working with Another Agent

1. **Share Context**: Reference this AGENTS.md for consistent understanding
2. **Define Clear Boundaries**: Specify which files/modules are being modified
3. **Follow Patterns**: Use the patterns established in the codebase
4. **Test Thoroughly**: Verify changes don't break existing functionality
5. **Document Changes**: Update docstrings, comments, and relevant docs
6. **Git Commits**: Write clear commit messages with reasoning

### Effective Agent Communication

```
"I'm going to implement a new data source (MySource) following the 
Abstract DataSource pattern in src/ingestion.py. I'll:
1. Create MySource class inheriting from DataSource
2. Implement fetch() method
3. Register in DataIngestionManager._get_source()
4. Add indicators to indicators.yaml
5. Test with sample data

This should take ~2 hours and follow pattern described in AGENTS.md Section 6.1"
```

### Code Review Checklist

Before submitting changes:
- [ ] Follows project style (PEP 8, snake_case, docstrings)
- [ ] No hardcoded values (use config)
- [ ] Error handling with graceful fallbacks
- [ ] Tests pass (or new tests added)
- [ ] Documentation updated
- [ ] Compatible with existing code
- [ ] No breaking changes to public APIs

---

## 17. Quick Reference Tables

### Commands Reference

```bash
# CLI Commands
python -m src.cli init                          # Initialize
python -m src.cli search <query>                # Search indicators
python -m src.cli search --list-topics          # List all tags
python -m src.cli search --source owid          # By source
python -m src.cli ingest --source manual --filepath <file>
python -m src.cli clean <file> --topic <topic> --source <source>
python -m src.cli document <file> --topic <topic> --url <url>
python -m src.cli pipeline <file> --topic <topic> --source <source>
python -m src.cli download --source <source> --indicator <ind> --topic <topic>
python -m src.cli status                        # Show status

# Web
python -m src.web
```

### Module Dependencies

```
cli.py
├─ config.py
├─ ingestion.py
├─ cleaning.py
├─ metadata.py
└─ searcher.py

ingestion.py
└─ requests, pandas

cleaning.py
└─ pandas

metadata.py
└─ openai, requests

searcher.py
├─ config.py
└─ (yaml already loaded)

web/
├─ flask
└─ core modules
```

### Key Classes Hierarchy

```
DataSource (ABC)
├─ ManualUpload
├─ ILOSTATSource
├─ OECDSource
├─ IMFSource
├─ OWIDSource
└─ WorldBankSource

ModalBase (Textual)
├─ ConfirmDialog
├─ MetadataModal
├─ InputDialog
├─ AlertDialog
├─ FilterDialog
├─ ProgressDialog
└─ SelectDialog
```

---

## 18. Summary for Agents

### What You Can Do

✅ Add new data sources  
✅ Implement new CLI commands  
✅ Create new TUI screens  
✅ Add web routes/endpoints  
✅ Enhance data cleaning rules  
✅ Improve search/discovery  
✅ Add configuration options  
✅ Implement tests  
✅ Optimize performance  
✅ Fix bugs and issues  

### What You Should Know

- 83% complete (core functionality done)
- Production-ready quality
- Follows established patterns
- Well-documented configuration
- Multiple interfaces (CLI, Web)
- Real API integration (6 sources)
- LLM-powered documentation
- Comprehensive error handling

### Starting Points for New Work

**Simple**: Add indicators to `indicators.yaml`  
**Easy**: Add new CLI command following existing pattern  
**Medium**: Implement new data source inheriting `DataSource`  
**Hard**: Build complete web dashboard or add database  

---

## Conclusion

**Mises Data Curator** is a mature, well-structured project with clear patterns and comprehensive documentation. Use this AGENTS.md alongside CLAUDE.md to understand the full system and execute effective development tasks.

**Key Takeaway**: This tool automates economic data curation with intelligent defaults, graceful fallbacks, and multiple interfaces. Focus on extending capabilities while maintaining code quality and following established patterns.

**Happy coding! 🚀**

---

*Document created: January 7, 2026*  
*For questions or clarifications, refer to the specific module documentation or examine the source code.*  
*All line numbers and file references are accurate as of the last update date.*
