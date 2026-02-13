# 📚 Mises Data Curation Tool - Documentation Index

## 🎯 Start Here

### For Quick Setup (5 minutes)
👉 **[QUICKSTART.md](QUICKSTART.md)** - Install, configure, and run your first command

### For Complete Overview
👉 **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What you have, how to use it, what's next

---

## 📖 Detailed Guides

### Complete Workflows & Examples
**[WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)**
- The 4-step workflow (Search → Download → Clean → Document)
- One-command download example (recommended!)
- Step-by-step examples for each topic
- Batch processing scripts
- Tips & tricks

### API Search & Discovery
**[API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md)**
- How to search for economic indicators
- Available indicators by topic and source
- Command examples
- Adding custom indicators

### Full Tool Documentation
**[README.md](README.md)**
- Complete feature list
- Installation & setup
- All 7 commands explained
- Configuration reference
- Architecture overview

---

## 🚀 Common Tasks

### I want to...

**Download economic data in one command:**
```bash
python -m src.cli download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --coverage latam
```
👉 See [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md#method-1-one-command-download--pipeline--recommended)

**Find what indicators are available:**
```bash
python -m src.cli search --list-topics
python -m src.cli search wage -v
```
👉 See [API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md)

**Upload and process my own data:**
```bash
python -m src.cli ingest --source manual --filepath my_data.xlsx
python -m src.cli pipeline my_data.csv --topic tema --source fuente
```
👉 See [README.md](README.md#usage)

**Check what's been processed:**
```bash
python -m src.cli status
ls 02_Datasets_Limpios/
ls 03_Metadata_y_Notas/
```
👉 See [QUICKSTART.md](QUICKSTART.md)

**Configure LLM for better metadata:**
1. Add API key to `.env`
2. Use `--force` flag to regenerate

👉 See [README.md](README.md#lgeneración-de-metadata-con-llm)

---

## 📋 Command Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `init` | Setup directory structure | `curate init` |
| `search` | Find indicators | `curate search wage -v` |
| `download` | ⭐ Download + clean + document (1 step) | `curate download --source oecd ...` |
| `ingest` | Download from API only | `curate ingest --source oecd ...` |
| `clean` | Clean dataset file | `curate clean file.csv --topic tema` |
| `document` | Generate metadata | `curate document file.csv --topic tema` |
| `pipeline` | Clean + document | `curate pipeline file.csv --topic tema` |
| `status` | Show project status | `curate status` |

👉 Full details: [README.md](README.md#%EF%B8%8F-configuraci%C3%B3n-avanzada)

---

## 🔍 Feature Overview

### ✅ What It Does

| Feature | Status | Where |
|---------|--------|-------|
| Search indicators | ✅ | [API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md) |
| Download from APIs | ✅ | [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md) |
| Clean data | ✅ | [README.md](README.md#%F0%9F%A7%B9-datos-limpios) |
| Generate metadata | ✅ | [README.md](README.md#-generaci%C3%B3n-de-metadata-con-llm) |
| One-command pipeline | ✅ | [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md#method-1-one-command-download--pipeline--recommended) |
| Organize by topic | ✅ | [README.md](README.md#-estructura-del-proyecto) |

### 🔌 Integrated Data Sources

| Source | Data | Free? | Auth? | Indicators |
|--------|------|-------|-------|------------|
| **ILOSTAT** | Labor/Employment | ✅ | ❌ | 3 |
| **OECD** | Economic | ✅ | ❌ | 7 |
| **IMF** | Macro | ✅ | ❌ | 2 |

All **free**, **public**, **no authentication required**

---

## 📊 Available Data

### By Topic

**salarios_reales** (Real Wages)
- Real wage index, average wage, minimum wage, productivity, inequality
- Source: OECD

**informalidad_laboral** (Informal Employment)
- Informal employment rate, worker count, unemployment
- Source: ILOSTAT

**presion_fiscal** (Tax Pressure)
- Tax revenue %, income tax rates
- Source: OECD

**libertad_economica** (Economic Freedom)
- GDP growth, inflation, unemployment
- Sources: IMF, ILOSTAT

### By Source

**ILOSTAT** - 3 indicators
- Unemployment rate, informal employment (2 variants)

**OECD** - 7 indicators
- Wages (3), taxes (2), productivity, inequality

**IMF** - 2 indicators
- GDP growth, inflation rate

---

## 🎓 Learning Path

**New to the tool?**
1. Read [QUICKSTART.md](QUICKSTART.md) (5 min)
2. Run `curate init` and `curate search --list-topics`
3. Try one example from [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)

**Want to understand the details?**
1. Read [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
2. Explore [API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md)
3. Review [README.md](README.md) for full reference

**Want to customize?**
1. Edit [config.yaml](config.yaml) for settings
2. Edit [indicators.yaml](indicators.yaml) to add indicators
3. See [README.md](README.md#-configuración-avanzada) for advanced options

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| [config.yaml](config.yaml) | Tool settings, cleaning rules, LLM config |
| [indicators.yaml](indicators.yaml) | Economic indicators database |
| [.env.example](.env.example) | API keys template (copy to .env) |
| [requirements.txt](requirements.txt) | Python dependencies |

---

## 💾 Directory Structure

```
mises/
├── src/                          # Python modules
│   ├── cli.py                    # 7 commands
│   ├── config.py                 # Configuration
│   ├── ingestion.py              # API downloads
│   ├── cleaning.py               # Data cleaning
│   ├── metadata.py               # Metadata generation
│   └── searcher.py               # Indicator search
│
├── 01_Raw_Data_Bank/             # Raw data from sources
├── 02_Datasets_Limpios/          # Cleaned, processed data
├── 03_Metadata_y_Notas/          # Auto-generated docs
├── 04_Graficos_Asociados/        # Visualizations
│
├── config.yaml                   # Tool configuration
├── indicators.yaml               # Indicators database
├── requirements.txt              # Dependencies
├── .env                          # API keys
│
└── 📚 Documentation:
    ├── README.md                         # Full docs
    ├── QUICKSTART.md                     # 5-min setup
    ├── WORKFLOW_GUIDE.md                 # Complete workflows
    ├── API_SEARCH_GUIDE.md               # API search
    ├── IMPLEMENTATION_SUMMARY.md         # Overview
    └── INDEX.md                          # This file!
```

---

## ❓ FAQ

**Q: Do I need API keys?**
A: No! All data sources are public and free.

**Q: Can I use this without internet?**
A: No for API downloads, but yes for processing local files.

**Q: Is my data secure?**
A: Everything runs locally. No data is uploaded anywhere.

**Q: Can I add my own data?**
A: Yes! Use `curate ingest --source manual`.

**Q: How do I customize topics?**
A: Edit `config.yaml` and `indicators.yaml`.

See full FAQ in [README.md](README.md#-desarrollo-futuro-roadmap) and [QUICKSTART.md](QUICKSTART.md)

---

## 📞 Support

- **Setup issues?** → [QUICKSTART.md](QUICKSTART.md)
- **How to use?** → [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)
- **Command help?** → `python -m src.cli COMMAND --help`
- **Technical details?** → [README.md](README.md)
- **Finding data?** → [API_SEARCH_GUIDE.md](API_SEARCH_GUIDE.md)

---

**Last Updated**: January 6, 2026
**Version**: 0.1.0 (MVP + API Integration)
**Status**: ✅ Ready for Production
