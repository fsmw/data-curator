# 🚀 Quick Start Guide - Mises Data Curation Tool

## Setup (5 minutes)

### 1. Install dependencies
```bash
cd c:\dev\mises
pip install -r requirements.txt
```

### 2. Configure GitHub Copilot CLI (recommended)
```bash
# Copy template
copy .env.example .env

# Start Copilot CLI and authenticate
copilot
# then run /login
```

`.env` example:
```env
COPILOT_MODEL=gpt-5-mini
```

### 3. Initialize directory structure
```bash
python -m src.cli init
```

---

## Basic Workflow

### Option A: Full Pipeline (Recommended)
Clean + Document in one command:

```bash
python -m src.cli pipeline your_data.csv \
    --topic salarios_reales \
    --source owid \
    --coverage latam \
    --url https://source-url.com
```

### Option B: Step by Step

**Step 1: Clean data**
```bash
python -m src.cli clean your_data.csv \
    --topic salarios_reales \
    --source owid \
    --coverage global
```

**Step 2: Generate metadata**
```bash
python -m src.cli document 02_Datasets_Limpios/salarios_reales/salarios_reales_owid_global_2000_2024.csv \
    --topic salarios_reales \
    --source owid \
    --url https://source-url.com
```

---

## Common Use Cases

### 1. Import manual dataset
```bash
# Copy your file to the project, then:
python -m src.cli ingest --source manual --filepath your_file.xlsx
```

### 2. Process multiple datasets
```bash
# Clean all datasets
python -m src.cli clean wages.csv --topic salarios_reales --source ilostat --coverage latam
python -m src.cli clean informal.csv --topic informalidad_laboral --source ilostat --coverage latam
python -m src.cli clean taxes.csv --topic presion_fiscal --source oecd --coverage oecd

# Check status
python -m src.cli status
```

### 3. Regenerate metadata with LLM
```bash
# Force regenerate (ignore cache)
python -m src.cli document dataset.csv \
    --topic my_topic \
    --source my_source \
    --force
```

---

## Tips

✅ **Naming conventions**: Use snake_case for topics (salarios_reales, not "Salarios Reales")

✅ **Source identifiers**: Use short lowercase names (owid, ilostat, indec, not "Our World in Data")

✅ **Coverage codes**: Use standard codes (latam, oecd, global, not "Latin America")

✅ **Copilot Auth**: Authenticate with Copilot CLI (`copilot` + `/login`) for AI-powered metadata. Without it, uses basic templates.

✅ **Caching**: Metadata is cached by default to save API costs. Use `--force` to regenerate.

---

## Test Installation

Run the sample data test:

```bash
python -m src.cli pipeline sample_wages_data.csv \
    --topic test \
    --source sample \
    --coverage test

python -m src.cli status
```

Should show:
- ✅ All directories created
- 📈 Clean datasets: 1+
- 📝 Metadata files: 1+

---

## Need Help?

```bash
# See all commands
python -m src.cli --help

# Help for specific command
python -m src.cli clean --help
python -m src.cli pipeline --help
```

---

**Ready to curate! 📊✨**
