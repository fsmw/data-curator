# Web Search Fix - Summary

## Issues Fixed

### 1. Alpine.js Scope Bug (Critical)
**Problem:** The search.html template had duplicate `x-data="searchForm()"` declarations on lines 3 and 37, creating two isolated Alpine.js scopes. When you clicked search, results were stored in one scope but the table was rendering from a different empty scope.

**Fix:** Wrapped both the search form and results table in a single `x-data="searchForm()"` wrapper div.

**Result:** Search now properly updates the results table ✓

### 2. Mock Data vs Real Indicators
**Problem:** The `/api/search` endpoint was using hardcoded MOCK_INDICATORS instead of your actual `indicators.yaml` configuration.

**Fix:** Updated `src/web/routes.py` to use the real `IndicatorSearcher` class that queries `indicators.yaml`.

**Result:** Search now returns your actual configured indicators ✓

### 3. Missing OWID Indicators
**Problem:** Your `indicators.yaml` had NO Our World in Data (OWID) indicators defined, only OECD/ILOSTAT/IMF/etc.

**Fix:** Added 5 key OWID indicators to `indicators.yaml`:
- `tax_revenue_owid` - Tax revenue as % of GDP
- `gdp_per_capita_owid` - GDP per capita
- `real_wages_owid` - Real wages index
- `inequality_gini_owid` - Gini coefficient
- `government_spending_owid` - Government spending

**Result:** OWID is now your main source for these economic indicators ✓

### 4. Missing Web Module Entry Point
**Problem:** Couldn't run `python -m src.web` because no `__main__.py` existed.

**Fix:** Created `src/web/__main__.py` with proper Flask app initialization.

**Result:** Can now easily start the web server ✓

## How to Use

### Start the Web Server
```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m src.web
```

Then open http://127.0.0.1:5000 in your browser.

### Search for Indicators
1. Navigate to the "Search" page
2. Type a query like "tax", "wages", "inequality", etc.
3. Optionally filter by source (OWID, OECD, ILOSTAT, etc.)
4. Click "Buscar" or press Enter

### Example Searches
- `tax` → Returns tax-related indicators from OWID and OECD
- `wages` → Returns wage indicators from OWID, ILOSTAT, OECD
- Filter by source: Select "Our World in Data" → Shows only OWID indicators

## Important Note About OWID

**Our World in Data does NOT have a public API.** Unlike OECD, ILOSTAT, or IMF, OWID provides downloadable CSV files but no programmatic API access.

### Current OWID Workflow:
1. Indicators are defined in `indicators.yaml` with OWID URLs
2. Data must be manually downloaded from those URLs
3. Use `python -m src.cli ingest --source manual --filepath <downloaded_file.csv>`
4. Then run the cleaning/documentation pipeline

### To Add More OWID Indicators:
1. Browse https://ourworldindata.org/
2. Find the indicator page (e.g., https://ourworldindata.org/taxation)
3. Add entry to `indicators.yaml`:
```yaml
your_indicator_name:
  source: owid
  description: "Description here"
  coverage: "Global"
  years: "2000-2024"
  countries: "ARG,BRA,CHL,COL,MEX,PER,URY"
  url: "https://ourworldindata.org/grapher/your-indicator"
```
4. Download the CSV from the OWID page
5. Import manually using the CLI

## Testing

### Test Search via CLI:
```bash
python -m src.cli search tax
python -m src.cli search --source owid
python -m src.cli search --list-sources
```

### Test Search via Web API:
```bash
curl "http://127.0.0.1:5000/api/search?q=tax" | python -m json.tool
curl "http://127.0.0.1:5000/api/search?source=owid" | python -m json.tool
```

## Files Modified

1. `src/web/templates/search.html` - Fixed Alpine.js scope bug
2. `src/web/routes.py` - Connected to real IndicatorSearcher
3. `indicators.yaml` - Added OWID indicators
4. `src/web/__main__.py` - Created web server entry point (NEW)

## Next Steps (Optional)

If you want automatic OWID data fetching:
1. Create `OWIDSource` class in `src/ingestion.py`
2. Implement CSV download from OWID URLs
3. Add to `DataIngestionManager._get_source()` switch

This would allow:
```bash
python -m src.cli download --source owid --indicator tax_revenue_owid --topic presion_fiscal
```

But this requires parsing OWID's HTML/JavaScript to find the CSV download links, as they don't provide a stable API.
