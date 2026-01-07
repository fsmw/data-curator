# ⚡ Quick Reference - Mises Data Curation Tool

## 🎯 Most Common Commands

### Search for Data
```bash
# List all topics
curate search --list-topics

# Search for wage indicators
curate search wage -v

# See all ILOSTAT indicators
curate search --source ilostat
```

### Download & Pipeline (ONE COMMAND!) ⭐
```bash
curate download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --coverage latam \
    --countries ARG,BRA,CHL,COL,MEX,PER,URY
```

### Or Step-by-Step
```bash
# Download
curate ingest --source oecd --dataset ALFS --indicator AVNL --countries ARG,BRA,CHL

# Process
curate pipeline file.csv --topic salarios_reales --source oecd --coverage latam
```

### View Results
```bash
curate status

ls 02_Datasets_Limpios/
ls 03_Metadata_y_Notas/
```

---

## 📊 Indicators by Topic (Search These!)

### Wages
```bash
curate search wage                    # real_wage_index, average_wage_usd, etc.
```

### Employment
```bash
curate search informal                # Informal employment rates
curate search unemployment            # Unemployment rate
```

### Taxes & Government
```bash
curate search tax                     # tax_revenue_gdp, income_tax_rate
```

### Economic Freedom
```bash
curate search gdp                     # gdp_growth
curate search inflation               # inflation_rate
```

---

## 🌍 Countries Supported

**Latin America** (default):
```
ARG (Argentina)
BRA (Brazil)
CHL (Chile)
COL (Colombia)
MEX (Mexico)
PER (Peru)
URY (Uruguay)
```

**OECD** (selected):
```
USA, ESP, FRA, DEU, GBR, ITA, CAN, AUS, JPN, KOR
```

**Global**:
```
* (all countries available in the indicator)
```

---

## 🔗 Data Sources

| Source | Speed | Auth | Free? | Examples |
|--------|-------|------|-------|----------|
| ILOSTAT | ~1s | ✅ | ✅ | Unemployment, informal employment |
| OECD | ~2s | ✅ | ✅ | Wages, taxes, productivity |
| IMF | ~1s | ✅ | ✅ | GDP growth, inflation |

---

## 📝 Common Parameters

```bash
# Required
--source {ilostat|oecd|imf}          # Data source
--indicator TEXT                     # Indicator name
--topic TEXT                         # salarios_reales, informalidad_laboral, etc.

# Optional (defaults shown)
--countries ARG,BRA,CHL              # Comma-separated ISO codes
--start-year 2010                    # Starting year
--end-year 2024                      # Ending year
--coverage latam                     # Geographic area
--url https://source.org             # Original source URL
--config config.yaml                 # Configuration file
```

---

## 🎬 Real Examples

### Example 1: Unemployment (One Command)
```bash
curate download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --countries ARG,BRA,CHL,COL,MEX,PER,URY
```

### Example 2: Wage Data (One Command)
```bash
curate download \
    --source oecd \
    --dataset ALFS \
    --indicator AVNL \
    --topic salarios_reales \
    --countries ARG,BRA,CHL,MEX
```

### Example 3: Economic Growth (One Command)
```bash
curate download \
    --source imf \
    --database WEO \
    --indicator NGDP_RPCH \
    --topic libertad_economica \
    --start-year 2015 \
    --end-year 2023
```

### Example 4: Your Own Data
```bash
# Upload
curate ingest --source manual --filepath my_data.xlsx

# Process
curate pipeline my_data.csv --topic mi_tema --source custom
```

---

## ✅ Workflow Checklist

- [ ] `curate init` - Initialize project
- [ ] `curate search --list-topics` - See what's available
- [ ] `curate search YOUR_KEYWORD -v` - Find your indicator
- [ ] `curate download ...` - Download & process (one command!)
- [ ] `curate status` - Verify everything worked
- [ ] Check `02_Datasets_Limpios/` for cleaned data
- [ ] Check `03_Metadata_y_Notas/` for documentation

---

## 🔧 Configuration

### Add API Key (for LLM metadata)
```bash
# 1. Copy template
cp .env.example .env

# 2. Add your OpenRouter key
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# 3. Use --force to regenerate metadata
curate document file.csv --topic tema --source fuente --force
```

### Add Custom Indicator
```yaml
# In indicators.yaml
indicators:
  my_indicator:
    source: oecd
    oecd_dataset: "MY_DATASET"
    oecd_indicator: "MY_CODE"
    description: "My custom indicator"
    coverage: "Global"
    years: "2010-2024"
    countries: "ARG,BRA,CHL"
```

---

## 🐛 Troubleshooting

**No data returned?**
```bash
# Check parameters
curate search your_indicator -v

# Try with more years
--start-year 2000 --end-year 2024
```

**Command not found?**
```bash
# Make sure you're in the project directory
cd c:\dev\mises

# Activate virtual environment
venv\Scripts\activate

# Then run commands
python -m src.cli search --help
```

**API connection failed?**
```bash
# Use manual upload instead
curate ingest --source manual --filepath your_file.csv
```

---

## 📚 Documentation

| Document | Read When |
|----------|-----------|
| [INDEX.md](INDEX.md) | You're lost, need a map |
| [QUICKSTART.md](QUICKSTART.md) | You have 5 minutes |
| [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) | You want detailed examples |
| [API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md) | You're searching for data |
| [README.md](README.md) | You need complete reference |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | You want an overview |

---

## 💡 Pro Tips

✅ **Batch download multiple indicators:**
```bash
for indicator in wage unemployment inflation; do
  curate search $indicator -v
done
```

✅ **Update existing data with new years:**
```bash
curate download --source oecd ... --start-year 2020 --end-year 2024
```

✅ **Use --force to regenerate metadata:**
```bash
curate document data.csv --topic tema --source fuente --force
```

✅ **Check what changed:**
```bash
curate status
ls -la 02_Datasets_Limpios/*/
```

---

## 🎓 Learning Path

**30 seconds**: Read this cheat sheet

**5 minutes**: Run `curate init` and `curate search --list-topics`

**15 minutes**: Try `curate download --source ilostat ...`

**1 hour**: Read [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) and experiment with different indicators

**Mastery**: Customize config.yaml and indicators.yaml for your use case

---

**Version**: 0.1.0 (MVP + API Integration)  
**Status**: ✅ Ready to Use  
**Last Updated**: January 6, 2026
