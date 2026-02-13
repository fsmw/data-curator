# Search Guide - Tag-Based Indicator Discovery

## Quick Start

The indicator system is now **tag-based** instead of topic-based. Search by ANY term!

### CLI Search

```bash
# Free-text search (searches everything)
python -m src.cli search tax
python -m src.cli search wages
python -m src.cli search inequality
python -m src.cli search salarios  # Spanish works too!

# Filter by source
python -m src.cli search --source owid
python -m src.cli search --source oecd
python -m src.cli search --source ilostat

# Search by specific tag
python -m src.cli search --tag wages
python -m src.cli search --tag fiscal
python -m src.cli search --tag inequality

# Verbose output (shows all details)
python -m src.cli search wages -v
python -m src.cli search --tag fiscal -v

# List available tags
python -m src.cli search --list-topics

# List available sources
python -m src.cli search --list-sources
```

### Web Interface

1. Start the server:
```bash
source .venv/bin/activate  # Linux/Mac
python -m src.web
```

2. Open http://127.0.0.1:5000

3. Use the search page:
   - Type any term: "tax", "wages", "inflation"
   - Filter by source dropdown: OWID, OECD, etc.
   - Results show tags for each indicator

## How Tags Work

Each indicator has multiple searchable tags:

```yaml
- id: real_wages_owid
  source: owid
  name: "Real Wages Index"
  description: "Real wages index (2015=100)"
  tags: [wages, salary, income, salarios, remuneracion, purchasing power]
  url: "https://ourworldindata.org/grapher/real-wages"
```

When you search for "wages" or "salarios", this indicator will be found!

## Available Tags

Run `python -m src.cli search --list-topics` to see all 60+ tags:

**Economic domains:**
- `gdp`, `growth`, `inflation`, `trade`, `fdi`

**Fiscal/Tax:**
- `tax`, `fiscal`, `revenue`, `spending`, `government`
- `impuestos`, `tributacion`, `gasto publico` (Spanish)

**Labor/Wages:**
- `wages`, `salary`, `employment`, `unemployment`, `labor`
- `salarios`, `empleo`, `desempleo`, `trabajo` (Spanish)

**Inequality:**
- `inequality`, `gini`, `poverty`, `distribution`, `wealth`
- `desigualdad`, `pobreza` (Spanish)

**And many more...**

## Sources

Currently supported sources (21 indicators total):

- **OWID** (5 indicators) - Our World in Data - manual downloads
- **OECD** (5 indicators) - OECD API
- **ILOSTAT** (3 indicators) - ILO labor statistics
- **IMF** (2 indicators) - IMF World Economic Outlook
- **World Bank** (4 indicators) - World Bank API
- **ECLAC** (2 indicators) - ECLAC Latin America data

## Adding New Indicators

Simply add to `indicators.yaml`:

```yaml
indicators:
  - id: your_indicator_id
    source: owid  # or oecd, ilostat, etc.
    name: "Human-Readable Name"
    description: "Brief description of what this measures"
    tags: [relevant, search, terms, english, spanish]
    url: "https://source-url.com"  # optional
    code: "API_CODE"  # for APIs like OECD, ILOSTAT
```

**Tag guidelines:**
- Include English + Spanish terms
- Add subject terms (wages, tax, gdp)
- Add related concepts (purchasing power, inequality)
- Use lowercase
- Separate with commas

## Examples

### Example 1: Find all wage indicators
```bash
$ python -m src.cli search --tag wages

📊 Real Wages Index (real_wages_owid)
   Source: OWID
   Tags: wages, salary, income, salarios, remuneracion, purchasing power

📊 Real Wage Index (real_wage_index)
   Source: OECD
   Tags: wages, salary, real income, salarios, remuneracion

📊 Minimum Wage (minimum_wage)
   Source: OECD
   Tags: wages, minimum wage, labor, salario minimo, trabajo

📊 Wage Growth (wage_growth)
   Source: ILOSTAT
   Tags: wages, growth, salary, salarios, crecimiento
```

### Example 2: Find OWID indicators
```bash
$ python -m src.cli search --source owid

tax_revenue_owid       Tax Revenue (% GDP)              OWID
gdp_per_capita_owid    GDP Per Capita                   OWID
real_wages_owid        Real Wages Index                 OWID
inequality_gini_owid   Gini Coefficient                 OWID
government_spending_owid Government Spending (% GDP)    OWID
```

### Example 3: Spanish search
```bash
$ python -m src.cli search impuestos

tax_revenue_owid     Tax Revenue (% GDP)         OWID
tax_revenue_gdp      Tax Revenue (% GDP)         OECD
tax_pressure_eclac   Tax Pressure                ECLAC
```

## API Usage

For programmatic access:

```python
from src.config import Config
from src.searcher import IndicatorSearcher

config = Config()
searcher = IndicatorSearcher(config)

# Free-text search
results = searcher.search("tax")

# Filter by source
owid_indicators = searcher.search_by_source("owid")

# Search by tag
wage_indicators = searcher.search_by_tag("wages")

# Get all tags
all_tags = searcher.list_tags()

# Get specific indicator
indicator = searcher.get_indicator_by_id("tax_revenue_owid")
```

## Web API Endpoints

```bash
# Search by query
GET /api/search?q=tax

# Filter by source
GET /api/search?source=owid

# Both
GET /api/search?q=inflation&source=imf
```

## Migration from Old System

If you have code using the old topic-based system:

**Old:**
```python
results = searcher.search_by_topic("salarios_reales")
topics = searcher.list_topics()
```

**New:**
```python
results = searcher.search_by_tag("wages")  # or "salarios"
tags = searcher.list_tags()
```

The old rigid topics are gone. Use flexible tags instead!

---

**Questions? Check:**
- `REFACTORING_SUMMARY.md` - Why we refactored
- `indicators.yaml` - All available indicators
- `src/searcher.py` - Search implementation
