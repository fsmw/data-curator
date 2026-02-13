# OWID API Integration - Complete Guide

## Summary

Successfully integrated Our World in Data (OWID) Grapher API into the data curator tool! You can now download data programmatically from OWID instead of manual CSV downloads.

## What Changed

### Before
- ❌ Had to manually download CSVs from OWID website
- ❌ Manual file management and imports
- ❌ No automated data updates
- ❌ OWID marked as "no API available"

### After
- ✅ Direct API integration with OWID Grapher
- ✅ Automated downloads via CLI
- ✅ Filter by countries and time ranges
- ✅ Full pipeline support (download → clean → document)
- ✅ Data saved to organized directories

## How It Works

### OWID Grapher API

**Base URL:** `https://ourworldindata.org/grapher/{slug}.csv`

**Key Features:**
- No authentication required
- Public access to all chart data
- Filter by countries, time ranges
- CSV format (easy to parse)
- CC BY 4.0 license (open data)

**Query Parameters:**
- `country` - Filter countries (joined with `~`)
- `time` - Time range (`2015..2024`, `latest`, `earliest`)
- `csvType` - `filtered` (chart data) or `full` (all data)

## Using the OWID Integration

### Basic Usage

```bash
python -m src.cli download \
  --source owid \
  --slug life-expectancy \
  --countries "Argentina,Brazil,Chile" \
  --start-year 2015 \
  --end-year 2024 \
  --topic libertad_economica \
  --coverage latam
```

### Finding OWID Slugs

1. Go to https://ourworldindata.org/charts
2. Find your chart (e.g., "Life Expectancy")
3. URL will be: `https://ourworldindata.org/grapher/life-expectancy`
4. **Slug is:** `life-expectancy` (part after `/grapher/`)

### Example Commands

**Download GDP per capita:**
```bash
python -m src.cli download \
  --source owid \
  --slug gdp-per-capita-worldbank \
  --countries "Argentina,Brazil,Mexico" \
  --start-year 2000 \
  --end-year 2024 \
  --topic libertad_economica \
  --coverage latam
```

**Download Life Expectancy:**
```bash
python -m src.cli download \
  --source owid \
  --slug life-expectancy \
  --countries "Argentina,Chile" \
  --start-year 2010 \
  --end-year 2024 \
  --topic libertad_economica \
  --coverage latam
```

**Download without filters (all countries, all years):**
```bash
python -m src.cli download \
  --source owid \
  --slug gdp-per-capita-worldbank \
  --topic libertad_economica \
  --coverage global
```

## What Gets Created

When you run the download command, the tool:

1. **Downloads raw data** → `01_Raw_Data_Bank/OWID/{slug}_{timestamp}.csv`
2. **Cleans data** → Standardizes columns (Entity→country, Year→year)
3. **Saves cleaned** → `02_Datasets_Limpios/{topic}/{topic}_owid_{coverage}_{years}.csv`
4. **Generates metadata** → `03_Metadata_y_Notas/{topic}.md` (using LLM)

## Implementation Details

### New Files

1. **`src/ingestion.py`** - Added `OWIDSource` class:
   - Inherits from `DataSource` ABC
   - Handles OWID Grapher API requests
   - Standardizes column names
   - Manages query parameters

2. **`indicators.yaml`** - Updated OWID indicators:
   - Added `slug` field for each OWID indicator
   - Slug comes from chart URL

### Code Structure

```python
class OWIDSource(DataSource):
    BASE_URL = "https://ourworldindata.org/grapher"

    def fetch(self, slug, countries=None, start_year=None, end_year=None):
        # Build URL: {BASE_URL}/{slug}.csv
        # Add query params: ?country=X~Y&time=2015..2024
        # Parse CSV response
        # Standardize columns
        # Return DataFrame
```

### CLI Integration

Updated `download` command to support:
- `--slug` parameter for OWID
- Country names (not just codes)
- Optional time filtering
- Full pipeline execution

## Indicators with OWID Slugs

Current OWID indicators in `indicators.yaml`:

| ID | Name | Slug |
|----|------|------|
| `tax_revenue_owid` | Tax Revenue (% GDP) | `tax-revenues` |
| `gdp_per_capita_owid` | GDP Per Capita | `gdp-per-capita-worldbank` |
| `real_wages_owid` | Real Wages Index | *(slug TBD - chart may not exist)* |
| `inequality_gini_owid` | Gini Coefficient | `economic-inequality-gini-index` |
| `government_spending_owid` | Government Spending | `total-gov-expenditure-gdp` |
| `life_expectancy_owid` | Life Expectancy | `life-expectancy` |

## Testing

### Test 1: Basic Download ✅
```bash
python -m src.cli download \
  --source owid \
  --slug life-expectancy \
  --countries "Argentina,Brazil" \
  --start-year 2015 \
  --end-year 2020 \
  --topic libertad_economica \
  --coverage latam
```

**Result:** Successfully downloaded 12 rows, cleaned, and documented!

### Verify Results
```bash
# Check raw data
ls 01_Raw_Data_Bank/OWID/

# Check cleaned data
cat 02_Datasets_Limpios/libertad_economica/libertad_economica_owid_latam_2015_2020.csv

# Check metadata
cat 03_Metadata_y_Notas/libertad_economica.md
```

## Common Issues & Solutions

### Issue: 404 Not Found
**Cause:** Incorrect slug or chart doesn't exist

**Solution:**
1. Verify slug at https://ourworldindata.org/charts
2. Check if chart has data download option
3. Some charts may not have CSV endpoints

### Issue: No Data Returned
**Cause:** Filters too restrictive or no data for those countries/years

**Solution:**
1. Try without filters first
2. Check if countries have data for that indicator
3. Try different time range

### Issue: Column Names Don't Match
**Cause:** OWID uses different column names per chart

**Solution:**
- The tool auto-standardizes: Entity→country, Year→year
- Other columns preserved as-is
- Check raw data to see actual column names

## Finding More OWID Indicators

### Method 1: Browse Charts
1. Visit https://ourworldindata.org/charts
2. Browse by topic
3. Click chart to get URL
4. Extract slug from URL

### Method 2: Search
1. Go to https://ourworldindata.org
2. Use search bar
3. Find relevant chart
4. Get slug from URL

### Method 3: Topic Pages
- https://ourworldindata.org/economic-growth
- https://ourworldindata.org/income-inequality
- https://ourworldindata.org/taxation
- https://ourworldindata.org/government-spending
- https://ourworldindata.org/life-expectancy

## Adding New OWID Indicators

1. Find the chart on OWID
2. Extract slug from URL
3. Add to `indicators.yaml`:

```yaml
- id: your_indicator_owid
  source: owid
  name: "Indicator Name"
  description: "What it measures"
  slug: "chart-slug-from-url"
  tags: [relevant, tags, here]
  url: "https://ourworldindata.org/grapher/slug"
```

4. Use in commands:
```bash
python -m src.cli download \
  --source owid \
  --slug your-slug \
  --topic your_topic \
  --coverage latam
```

## Benefits

1. **Automation** - No more manual downloads
2. **Reproducibility** - Same command = same data
3. **Updates** - Easy to refresh data periodically
4. **Filtering** - Download only what you need
5. **Integration** - Works with existing pipeline (clean + document)
6. **Free** - No API key required, open data

## Limitations

1. **No Authentication** - Can't access private/restricted data
2. **Chart-Based** - Only works with published charts
3. **Rate Limits** - Unknown, but likely present
4. **Slug Discovery** - Must find slug manually from website
5. **Column Variation** - Each chart has different columns

## Future Improvements

1. **Slug Discovery Tool** - Auto-find slugs by keyword search
2. **Batch Downloads** - Download multiple indicators at once
3. **Update Check** - Detect when OWID data has changed
4. **Metadata Caching** - Store chart metadata locally
5. **Error Recovery** - Better handling of failed downloads

## Resources

- **OWID API Docs:** https://docs.owid.io/projects/etl/api/
- **OWID Charts:** https://ourworldindata.org/charts
- **Chart Examples:** https://ourworldindata.org/grapher/
- **Data License:** CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)

---

**Status:** ✅ Fully integrated and tested
**Date:** January 8, 2026
**Version:** 0.2.0 with OWID API support
