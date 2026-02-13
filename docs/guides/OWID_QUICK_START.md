# OWID API - Quick Start

## 🚀 Download Data in One Command

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

This will:
1. ✅ Download data from OWID API
2. ✅ Clean and standardize it
3. ✅ Generate metadata with LLM
4. ✅ Save everything to organized folders

## 🔍 Finding Chart Slugs

1. Go to https://ourworldindata.org/charts
2. Find your chart
3. URL: `https://ourworldindata.org/grapher/[SLUG]`
4. Use the `[SLUG]` part!

**Examples:**
- Life Expectancy: `life-expectancy`
- GDP Per Capita: `gdp-per-capita-worldbank`
- Gini Index: `economic-inequality-gini-index`

## 📋 Available OWID Indicators

Search all OWID indicators:
```bash
python -m src.cli search --source owid -v
```

Current indicators (6 total):
- Tax Revenue (% GDP) - `tax-revenues`
- GDP Per Capita - `gdp-per-capita-worldbank`
- Real Wages Index - `real-wages`
- Gini Coefficient - `economic-inequality-gini-index`
- Government Spending - `total-gov-expenditure-gdp`
- Life Expectancy - `life-expectancy`

## 💡 Pro Tips

**Download without filters (all data):**
```bash
python -m src.cli download \
  --source owid \
  --slug gdp-per-capita-worldbank \
  --topic libertad_economica \
  --coverage global
```

**Check what you downloaded:**
```bash
# Raw data
ls 01_Raw_Data_Bank/OWID/

# Cleaned data
ls 02_Datasets_Limpios/

# Metadata
cat 03_Metadata_y_Notas/libertad_economica.md
```

## ⚙️ Optional Parameters

- `--countries` - Filter countries (comma-separated names)
- `--start-year` - Start year (default: 2010)
- `--end-year` - End year (default: 2024)
- `--topic` - Organize data by topic
- `--coverage` - Geographic scope (latam, global, etc.)
- `--url` - Source URL for metadata

## 🎯 Example Workflows

**Economic Inequality Study:**
```bash
# Download Gini coefficient
python -m src.cli download \
  --source owid \
  --slug economic-inequality-gini-index \
  --countries "Argentina,Brazil,Chile,Colombia,Mexico" \
  --start-year 2000 \
  --end-year 2024 \
  --topic libertad_economica \
  --coverage latam
```

**Health Analysis:**
```bash
# Download life expectancy
python -m src.cli download \
  --source owid \
  --slug life-expectancy \
  --countries "Argentina,Uruguay,Chile" \
  --start-year 1990 \
  --end-year 2024 \
  --topic libertad_economica \
  --coverage cono_sur
```

**Economic Growth:**
```bash
# Download GDP per capita
python -m src.cli download \
  --source owid \
  --slug gdp-per-capita-worldbank \
  --countries "Argentina,Brazil,Mexico" \
  --topic libertad_economica \
  --coverage latam
```

## ❗ Common Errors

**404 Not Found:**
- Check slug is correct
- Visit chart URL to verify it exists
- Some charts don't have CSV endpoints

**No data returned:**
- Try without country filters first
- Check if data exists for those countries/years
- Use verbose mode to see API request

## 📚 More Info

- Full documentation: `OWID_API_INTEGRATION.md`
- Search guide: `SEARCH_GUIDE.md`
- OWID Charts: https://ourworldindata.org/charts
