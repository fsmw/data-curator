# Complete Command Reference - All 5 Sources

## 🌐 Quick Examples for Each Source

### 1️⃣ ILOSTAT - International Labour Organization

**Get unemployment data:**
```bash
python -m src.cli download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --countries ARG,BRA,CHL,COL,MEX,PER,URY
```

**Get informal employment:**
```bash
python -m src.cli download \
    --source ilostat \
    --indicator informal_employment_rate \
    --topic informalidad_laboral
```

---

### 2️⃣ OECD - Organisation for Economic Co-operation and Development

**Get wage data:**
```bash
python -m src.cli download \
    --source oecd \
    --dataset ALFS \
    --indicator AVE \
    --topic salarios_reales
```

**Get tax revenue data:**
```bash
python -m src.cli download \
    --source oecd \
    --dataset REV \
    --topic presion_fiscal \
    --start-year 2015 \
    --end-year 2023
```

**Get minimum wage:**
```bash
python -m src.cli download \
    --source oecd \
    --dataset LAB_STAT \
    --indicator MIN_WAGE \
    --topic salarios_reales
```

---

### 3️⃣ IMF - International Monetary Fund

**Get GDP growth:**
```bash
python -m src.cli download \
    --source imf \
    --database WEO \
    --indicator NGDP_RPCH \
    --topic libertad_economica
```

**Get inflation rates:**
```bash
python -m src.cli download \
    --source imf \
    --database WEO \
    --indicator PCPIPCH \
    --topic libertad_economica
```

---

### 4️⃣ World Bank

**Get GINI inequality index:**
```bash
python -m src.cli download \
    --source worldbank \
    --indicator SI.POV.GINI \
    --topic libertad_economica
```

**Get poverty data:**
```bash
python -m src.cli download \
    --source worldbank \
    --indicator SI.POV.DDAY \
    --topic libertad_economica
```

**Get trade openness:**
```bash
python -m src.cli download \
    --source worldbank \
    --indicator NE.TRD.GNRL.ZS \
    --topic libertad_economica
```

**Get foreign direct investment:**
```bash
python -m src.cli download \
    --source worldbank \
    --indicator BX.KLT.DINV.CD.WD \
    --topic libertad_economica
```

---

### 5️⃣ ECLAC - Economic Commission for Latin America and Caribbean

**Get productivity data:**
```bash
python -m src.cli download \
    --source eclac \
    --indicator TFP \
    --topic libertad_economica
```

**Get inequality data:**
```bash
python -m src.cli download \
    --source eclac \
    --indicator DESIGUALDAD \
    --topic libertad_economica
```

**Get debt data:**
```bash
python -m src.cli download \
    --source eclac \
    --indicator DEUDA \
    --topic presion_fiscal
```

**Get labor participation:**
```bash
python -m src.cli download \
    --source eclac \
    --indicator PARTICIPACION \
    --topic informalidad_laboral
```

---

## 🔍 Search Across All Sources

**List all available sources:**
```bash
python -m src.cli search --list-sources
```
Output shows: ECLAC (4), ILOSTAT (3), IMF (2), OECD (7), WORLDBANK (4)

**List all topics:**
```bash
python -m src.cli search --list-topics
```
Output shows: salarios_reales, informalidad_laboral, presion_fiscal, libertad_economica

**Search for wage-related indicators:**
```bash
python -m src.cli search wage -v
```

**Filter by source:**
```bash
python -m src.cli search --source worldbank
python -m src.cli search --source eclac -v
python -m src.cli search --source oecd -v
```

**Filter by topic:**
```bash
python -m src.cli search --topic libertad_economica -v
```

---

## 📥 Download Parameters by Source

### ILOSTAT
```bash
--source ilostat
--indicator <code>              # Required: e.g., unemployment_rate, informal_employment_rate
--countries <codes>             # Optional: ARG,BRA,CHL,COL,MEX,PER,URY
--start-year <year>             # Optional: Default 2010
--end-year <year>               # Optional: Default 2024
```

### OECD
```bash
--source oecd
--dataset <id>                  # Required: e.g., ALFS, REV, LAB_STAT, PROD
--indicator <code>              # Optional: specific indicator within dataset
--countries <codes>             # Optional
--start-year <year>             # Optional
--end-year <year>               # Optional
```

### IMF
```bash
--source imf
--database <id>                 # Required: e.g., WEO, GFS
--indicator <code>              # Required: e.g., NGDP_RPCH, PCPIPCH
--countries <codes>             # Optional
--start-year <year>             # Optional
--end-year <year>               # Optional
```

### World Bank
```bash
--source worldbank
--indicator <code>              # Required: e.g., SI.POV.GINI, NE.TRD.GNRL.ZS
--countries <codes>             # Optional
--start-year <year>             # Optional
--end-year <year>               # Optional
```

### ECLAC
```bash
--source eclac
--indicator <table_id>          # Required: e.g., TFP, DESIGUALDAD, DEUDA, PARTICIPACION
--countries <codes>             # Optional
--start-year <year>             # Optional
--end-year <year>               # Optional
```

### Common for All
```bash
--topic <name>                  # Required: salarios_reales, informalidad_laboral, presion_fiscal, libertad_economica
--coverage <region>             # Optional: Default "latam" - e.g., global, latam, cono_sur
--url <source_url>              # Optional: Original source URL for documentation
--config <path>                 # Optional: Default "config.yaml"
```

---

## 📊 Complete Data Flow - Example

Download and process unemployment data from all relevant sources:

```bash
# 1. From ILOSTAT (Global labor statistics)
python -m src.cli download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --coverage latam

# 2. From IMF (Macroeconomic indicators)
python -m src.cli download \
    --source imf \
    --database WEO \
    --indicator NGDP_RPCH \
    --topic libertad_economica

# 3. From World Bank (Development data)
python -m src.cli download \
    --source worldbank \
    --indicator SI.POV.GINI \
    --topic libertad_economica

# 4. From ECLAC (Latin America specific)
python -m src.cli download \
    --source eclac \
    --indicator DEUDA \
    --topic presion_fiscal

# 5. From OECD (Economic cooperation data)
python -m src.cli download \
    --source oecd \
    --dataset REV \
    --topic presion_fiscal
```

Each command automatically:
1. 📥 Downloads from API
2. 🧹 Cleans and standardizes
3. 📊 Saves to `02_Datasets_Limpios/`
4. 📝 Generates metadata to `03_Metadata_y_Notas/`

---

## 🎯 Use Cases

### Case 1: Study Income Inequality in LAC
```bash
# Get GINI from World Bank
python -m src.cli download --source worldbank --indicator SI.POV.GINI --topic libertad_economica

# Get inequality ratio from ECLAC  
python -m src.cli download --source eclac --indicator DESIGUALDAD --topic libertad_economica

# Get wage inequality from OECD
python -m src.cli download --source oecd --dataset LAB_STAT --topic salarios_reales
```

### Case 2: Analyze Tax Pressure
```bash
# Get tax revenue from OECD
python -m src.cli download --source oecd --dataset REV --topic presion_fiscal

# Get public debt from ECLAC
python -m src.cli download --source eclac --indicator DEUDA --topic presion_fiscal
```

### Case 3: Monitor Economic Freedom
```bash
# Get GDP growth from IMF
python -m src.cli download --source imf --database WEO --indicator NGDP_RPCH --topic libertad_economica

# Get inflation from IMF
python -m src.cli download --source imf --database WEO --indicator PCPIPCH --topic libertad_economica

# Get employment from ILOSTAT
python -m src.cli download --source ilostat --indicator unemployment_rate --topic libertad_economica

# Get FDI from World Bank
python -m src.cli download --source worldbank --indicator BX.KLT.DINV.CD.WD --topic libertad_economica
```

---

## 📚 Find More Examples

See these documentation files for detailed examples:
- `SOURCES_GUIDE.md` - Complete source documentation
- `WORKFLOW_GUIDE.md` - Step-by-step workflows
- `API_SEARCH_GUIDE.md` - API search functionality
- `CHEATSHEET.md` - Quick reference

---

## ✅ Verification

Check what's available:
```bash
# Show all sources
python -m src.cli search --list-sources

# Show all topics
python -m src.cli search --list-topics

# Show project status
python -m src.cli status

# Show help for download command
python -m src.cli download --help
```

---

Generated: January 6, 2026  
Version: 1.0 - All Sources Complete
