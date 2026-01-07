# 🔍 API Search & Discovery Guide

The tool now includes a **search command similar to `apt search` or `dnf search`** to discover and download data from ILOSTAT, OECD, and IMF APIs.

## Quick Start

### Step 1: Discover Data

Search for available indicators:

```bash
# List all topics
python -m src.cli search --list-topics

# List all sources
python -m src.cli search --list-sources

# Search for specific indicators
python -m src.cli search wage              # Search by keyword
python -m src.cli search informal -v       # Verbose details
python -m src.cli search --source ilostat  # Search by source
```

### Step 2: Get Details

```bash
# See all wage indicators with details
python -m src.cli search wage -v

# Shows:
# - Indicator name
# - Description
# - Source (ILOSTAT, OECD, IMF)
# - Available years
# - Geographic coverage
# - Available countries
```

### Step 3: Download Data

```bash
# Download from IMF (GDP growth)
python -m src.cli ingest \
    --source imf \
    --database WEO \
    --indicator NGDP_RPCH \
    --countries ARG,BRA,CHL \
    --start-year 2015 \
    --end-year 2023

# Download from ILOSTAT (Informal employment)
python -m src.cli ingest \
    --source ilostat \
    --indicator informal_employment_rate \
    --countries ARG,BRA,CHL,COL,MEX,PER \
    --start-year 2010 \
    --end-year 2024

# Download from OECD (Real wages)
python -m src.cli ingest \
    --source oecd \
    --dataset ALFS \
    --indicator AVNL \
    --countries ARG,BRA,CHL,MEX \
    --start-year 2010 \
    --end-year 2024
```

### Step 4: Pipeline It

Once data is downloaded, clean and document it:

```bash
python -m src.cli pipeline downloaded_data.csv \
    --topic informalidad_laboral \
    --source ilostat \
    --coverage latam \
    --url https://ilostat.ilo.org
```

---

## Available Indicators

### By Topic

```bash
python -m src.cli search --list-topics
```

**salarios_reales** (5 indicators)
- real_wage_index
- average_wage_usd
- minimum_wage
- labor_productivity
- wage_inequality_gini

**informalidad_laboral** (3 indicators)
- informal_employment_rate
- informal_workers_count
- unemployment_rate

**presion_fiscal** (2 indicators)
- tax_revenue_gdp
- income_tax_rate

**libertad_economica** (3 indicators)
- gdp_growth
- inflation_rate
- unemployment_rate

### By Source

```bash
# ILOSTAT (3 indicators)
python -m src.cli search --source ilostat

# OECD (7 indicators)
python -m src.cli search --source oecd

# IMF (2 indicators)
python -m src.cli search --source imf
```

---

## Examples

### Example 1: Search & Download Wage Data

```bash
# Discover
python -m src.cli search wage -v

# Download
python -m src.cli ingest \
    --source oecd \
    --dataset ALFS \
    --indicator AVNL \
    --countries ARG,BRA,CHL,MEX,COL \
    --start-year 2010 \
    --end-year 2024

# Pipeline
python -m src.cli pipeline oecd_wages.csv \
    --topic salarios_reales \
    --source oecd \
    --coverage latam \
    --url https://stats.oecd.org
```

### Example 2: Multiple Indicators

```bash
# Search for all economic freedom indicators
python -m src.cli search gdp -v
python -m src.cli search inflation -v
python -m src.cli search unemployment -v

# Download each
python -m src.cli ingest --source imf --database WEO --indicator NGDP_RPCH --countries ARG,BRA,CHL --start-year 2015 --end-year 2023
python -m src.cli ingest --source imf --database WEO --indicator PCPIPCH --countries ARG,BRA,CHL --start-year 2015 --end-year 2023
```

---

## Supported Indicators

### ILOSTAT (3)
- `informal_employment_rate` - Informal employment (% of total)
- `informal_workers_count` - Number of informal workers
- `unemployment_rate` - Unemployment rate (%)

### OECD (7)
- `real_wage_index` - Real wage index (2015=100)
- `average_wage_usd` - Average nominal wage (USD)
- `minimum_wage` - Minimum wage levels
- `labor_productivity` - Labor productivity index
- `wage_inequality_gini` - Wage inequality (Gini)
- `tax_revenue_gdp` - Tax revenue as % GDP
- `income_tax_rate` - Average income tax rate

### IMF (2)
- `gdp_growth` - Real GDP growth (annual %)
- `inflation_rate` - Inflation rate (annual %)

---

## Adding Custom Indicators

Edit `indicators.yaml` to add your own:

```yaml
indicators:
  my_indicator:
    source: oecd
    oecd_dataset: "MY_DATASET"
    oecd_indicator: "MY_CODE"
    description: "My custom indicator"
    coverage: "Global"
    years: "2010-2024"
    countries: "ARG,BRA,CHL,..."
```

Then use:
```bash
python -m src.cli search my_indicator -v
python -m src.cli ingest --source oecd --dataset MY_DATASET --indicator MY_CODE ...
```

---

## Notes

⚠️ **API Connectivity**: 
- APIs are public and free
- Some firewalls may block connections
- If API fails, system falls back to manual upload mode

✅ **Data Caching**:
- Raw downloads saved to `01_Raw_Data_Bank/{source}/`
- Metadata cached to avoid regeneration costs
- Use `--force` flag to regenerate

✅ **Flexible Queries**:
- Search is keyword-based (fuzzy matching)
- Use `-v` for detailed information
- Combine multiple filters

---

See [README.md](README.md) for complete tool documentation.
