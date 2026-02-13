# 🚀 Complete Workflow: From Search to Curation

This guide shows the complete data curation workflow using the new tools.

## The 4-Step Workflow

```
1. SEARCH    → Discover what data is available
2. DOWNLOAD  → Fetch from public APIs (in one command!)
3. CLEAN     → Standardize country codes, dates, etc.
4. DOCUMENT  → Generate metadata with AI
```

---

## Method 1: One-Command Download + Pipeline ⭐ (Recommended)

Everything in a single command:

```bash
python -m src.cli download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --coverage latam \
    --countries ARG,BRA,CHL,COL,MEX,PER,URY \
    --start-year 2010 \
    --end-year 2024 \
    --url https://ilostat.ilo.org
```

**Output:**
```
✅ Complete! All in one command:
   📥 Downloaded: 49 rows from ILOSTAT
   🧹 Cleaned: 49 rows
   📊 Saved: 02_Datasets_Limpios/libertad_economica/...csv
   📝 Documented: 03_Metadata_y_Notas/libertad_economica.md
```

---

## Method 2: Step-by-Step (For More Control)

### Step 1: Search for Data

```bash
# Find what's available
python -m src.cli search --list-topics

python -m src.cli search --list-sources

python -m src.cli search wage -v
```

### Step 2: Download from API

```bash
python -m src.cli ingest \
    --source oecd \
    --dataset ALFS \
    --indicator AVNL \
    --countries ARG,BRA,CHL,MEX,COL \
    --start-year 2010 \
    --end-year 2024
```

**Output:** Raw data displayed in terminal

### Step 3: Save & Pipeline

```bash
# Assuming data was saved as 'wages.csv'
python -m src.cli pipeline wages.csv \
    --topic salarios_reales \
    --source oecd \
    --coverage latam \
    --url https://stats.oecd.org
```

---

## Complete Examples

### Example 1: Latin American Wages (OECD)

```bash
# Single command
python -m src.cli download \
    --source oecd \
    --dataset ALFS \
    --indicator AVNL \
    --topic salarios_reales \
    --coverage latam \
    --countries ARG,BRA,CHL,MEX,COL \
    --url https://stats.oecd.org/sdmx-json/data/ALFS
```

### Example 2: Informal Employment (ILOSTAT)

```bash
python -m src.cli download \
    --source ilostat \
    --indicator informal_employment_rate \
    --topic informalidad_laboral \
    --coverage latam \
    --countries ARG,BRA,CHL,COL,MEX,PER,URY
```

### Example 3: Economic Freedom (IMF - Real GDP Growth)

```bash
python -m src.cli download \
    --source imf \
    --database WEO \
    --indicator NGDP_RPCH \
    --topic libertad_economica \
    --coverage latam \
    --countries ARG,BRA,CHL,COL,MEX,PER,URY \
    --start-year 2015 \
    --end-year 2023
```

### Example 4: Fiscal Pressure (OECD - Tax Revenue)

```bash
python -m src.cli download \
    --source oecd \
    --dataset REV \
    --indicator 1100_1200_1300 \
    --topic presion_fiscal \
    --coverage oecd \
    --countries ARG,BRA,CHL,MEX,COL,PER \
    --url https://stats.oecd.org/Index.aspx?DataSetCode=REV
```

---

## Available Indicators by Topic

### 📊 **salarios_reales** (Real Wages)
```bash
python -m src.cli search real_wage -v
python -m src.cli search average_wage -v
python -m src.cli search wage_inequality -v
```

Sources: **OECD**

### 📊 **informalidad_laboral** (Informal Employment)
```bash
python -m src.cli search informal -v
python -m src.cli search unemployment -v
```

Sources: **ILOSTAT**

### 📊 **presion_fiscal** (Tax Pressure)
```bash
python -m src.cli search tax_revenue -v
python -m src.cli search income_tax -v
```

Sources: **OECD**

### 📊 **libertad_economica** (Economic Freedom)
```bash
python -m src.cli search gdp_growth -v
python -m src.cli search inflation -v
```

Sources: **IMF**, **ILOSTAT**

---

## View Your Results

### Check Project Status
```bash
python -m src.cli status
```

Shows:
- Datasets processed: ✅
- Metadata generated: ✅
- API configuration: ✅

### List Processed Data
```bash
# List cleaned datasets
ls 02_Datasets_Limpios/

# View metadata
ls 03_Metadata_y_Notas/
```

---

## Advanced: Batch Processing

Create a script to download multiple indicators:

```bash
#!/bin/bash

# Download all indicators for a topic
echo "Downloading wage indicators..."
python -m src.cli download --source oecd --dataset ALFS --indicator AVNL --topic salarios_reales --coverage latam

echo "Downloading informal employment..."
python -m src.cli download --source ilostat --indicator informal_employment_rate --topic informalidad_laboral --coverage latam

echo "Downloading tax revenue..."
python -m src.cli download --source oecd --dataset REV --indicator 1100 --topic presion_fiscal --coverage oecd

echo "✅ All downloads complete!"
```

---

## Tips & Tricks

✅ **Use `--countries` to filter**: 
```bash
--countries ARG,BRA,CHL  # Only 3 countries
```

✅ **Specify exact year range**:
```bash
--start-year 2015 --end-year 2023
```

✅ **Update URL for better metadata**:
```bash
--url https://source-url.org/data
```

✅ **Search before downloading**:
```bash
python -m src.cli search your_indicator -v  # See available countries/years
```

✅ **One-liner to search, then download**:
```bash
python -m src.cli search wage -v && python -m src.cli download --source oecd ...
```

---

## API Details

| API | Countries | Years | Auth | Speed |
|-----|-----------|-------|------|-------|
| **ILOSTAT** | 190+ | 2010-2024 | None | ~1s |
| **OECD** | 40+ | varies | None | ~2s |
| **IMF** | 200+ | 1980-2024 | None | ~1s |

All **free**, **public**, **no authentication required** ✅

---

## Troubleshooting

### No data returned?
```bash
# Check your parameters
python -m src.cli search your_indicator -v

# Try with more years
--start-year 2000 --end-year 2024
```

### API connection failed?
```bash
# Fallback to manual upload
python -m src.cli ingest --source manual --filepath your_file.csv
```

### Wrong countries?
```bash
# Use ISO 3166-1 alpha-3 codes
--countries ARG,BRA,CHL  # Correct
--countries Argentina,Brazil  # Wrong
```

---

See [API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md) and [README.md](README.md) for more details.
