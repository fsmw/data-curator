# Data Sources Guide

This guide explains all available data sources in the economic data curation tool.

## 📊 Available Sources

### 1. ILOSTAT (International Labour Organization)
**Website**: [ILO Statistics](https://ilostat.ilo.org/)  
**API Type**: SDMX REST  
**Coverage**: Global  
**Indicators**: 3
- Informal employment rate
- Informal workers count
- Unemployment rate

**Example Usage**:
```bash
python -m src.cli download \
    --source ilostat \
    --indicator unemployment_rate \
    --topic libertad_economica \
    --countries ARG,BRA,CHL
```

**Parameters**:
- `--indicator`: ILOSTAT indicator code (e.g., `unemployment_rate`, `informal_employment_rate`)
- `--countries`: ISO 3166-1 alpha-3 country codes (optional, defaults to: ARG,BRA,CHL,COL,MEX,PER,URY)
- `--start-year`: Starting year (default: 2010)
- `--end-year`: Ending year (default: 2024)

---

### 2. OECD (Organisation for Economic Co-operation and Development)
**Website**: [OECD Statistics](https://stats.oecd.org/)  
**API Type**: SDMX-JSON REST  
**Coverage**: OECD member countries + partners  
**Indicators**: 7
- Real wage index
- Average nominal wage
- Minimum wage
- Tax revenue as % of GDP
- Income tax rate
- Labor productivity
- Wage inequality (GINI)

**Example Usage**:
```bash
python -m src.cli download \
    --source oecd \
    --dataset ALFS \
    --indicator AVE \
    --topic salarios_reales
```

**Parameters**:
- `--dataset`: OECD dataset ID (e.g., `ALFS`, `REV`, `LAB_STAT`, `PROD`)
- `--indicator`: Indicator code within dataset (optional)
- `--countries`: Country codes (optional)
- `--start-year`: Starting year (default: 2010)
- `--end-year`: Ending year (default: 2024)

---

### 3. IMF (International Monetary Fund)
**Website**: [IMF Data](https://www.imf.org/en/Data)  
**API Type**: SDMX-JSON REST  
**Coverage**: Global  
**Indicators**: 2
- Real GDP growth rate
- Inflation rate (CPI)

**Example Usage**:
```bash
python -m src.cli download \
    --source imf \
    --database WEO \
    --indicator NGDP_RPCH \
    --topic libertad_economica
```

**Parameters**:
- `--database`: IMF database (e.g., `WEO` for World Economic Outlook, `GFS` for Government Finance Statistics)
- `--indicator`: Indicator code (required, e.g., `NGDP_RPCH`, `PCPIPCH`)
- `--countries`: Country codes (optional)
- `--start-year`: Starting year (default: 2010)
- `--end-year`: Ending year (default: 2024)

---

### 4. World Bank
**Website**: [World Bank Open Data](https://data.worldbank.org/)  
**API Type**: JSON REST  
**Coverage**: Global  
**Indicators**: 4
- GINI coefficient (income inequality)
- Poverty headcount ratio
- Trade as % of GDP
- Foreign direct investment inflows

**Example Usage**:
```bash
python -m src.cli download \
    --source worldbank \
    --indicator SI.POV.GINI \
    --topic libertad_economica
```

**Parameters**:
- `--indicator`: World Bank indicator code (required, e.g., `SI.POV.GINI`, `NY.GDP.MKTP.CD`)
- `--countries`: Country codes (optional)
- `--start-year`: Starting year (default: 2010)
- `--end-year`: Ending year (default: 2024)

**Common Indicator Codes**:
| Code | Description |
|------|-------------|
| SI.POV.GINI | GINI index |
| SI.POV.DDAY | Poverty headcount at $1.90/day |
| NE.TRD.GNRL.ZS | Trade (% of GDP) |
| BX.KLT.DINV.CD.WD | Foreign direct investment |
| NY.GDP.MKTP.CD | GDP (current USD) |
| NY.GDP.PCAP.CD | GDP per capita (current USD) |

---

### 5. ECLAC (Economic Commission for Latin America and the Caribbean)
**Website**: [ECLAC Statistics](https://data.cepal.org/)  
**API Type**: JSON REST  
**Coverage**: Latin America and Caribbean  
**Indicators**: 4
- Total Factor Productivity growth
- Income inequality ratio
- Public debt as % of GDP
- Labor force participation rate

**Example Usage**:
```bash
python -m src.cli download \
    --source eclac \
    --indicator TFP \
    --topic libertad_economica \
    --coverage latam
```

**Parameters**:
- `--indicator`: ECLAC table ID (required, e.g., `TFP`, `DESIGUALDAD`, `DEUDA`, `PARTICIPACION`)
- `--countries`: Country codes (optional)
- `--start-year`: Starting year (default: 2010)
- `--end-year`: Ending year (default: 2024)

---

### 6. Manual Upload (Instituto Nacionales)
For local data or data not available from APIs, use manual import:

```bash
python -m src.cli pipeline \
    --input datos_locales.csv \
    --topic salarios_reales \
    --source INDEC
```

---

## 🔍 Searching Available Indicators

### List all sources and their indicator counts
```bash
python -m src.cli search --list-sources
```

Output:
```
🌐 Available Sources:

  ECLAC           (4 indicators)
  ILOSTAT         (3 indicators)
  IMF             (2 indicators)
  OECD            (7 indicators)
  WORLDBANK       (4 indicators)
```

### List all topics
```bash
python -m src.cli search --list-topics
```

### Search for specific indicators
```bash
# Keyword search
python -m src.cli search wage -v

# Filter by source
python -m src.cli search --source worldbank

# Filter by topic
python -m src.cli search --topic libertad_economica
```

---

## 📈 Complete Indicator Database

Total: **20 indicators** across 5 sources

### By Topic
- **salarios_reales**: 4 indicators
  - real_wage_index (OECD)
  - average_wage_usd (OECD)
  - minimum_wage (OECD)
  - labor_productivity (OECD)

- **informalidad_laboral**: 3 indicators
  - informal_employment_rate (ILOSTAT)
  - informal_workers_count (ILOSTAT)
  - labor_participation_rate (ECLAC)

- **presion_fiscal**: 3 indicators
  - tax_revenue_gdp (OECD)
  - income_tax_rate (OECD)
  - debt_to_gdp (ECLAC)

- **libertad_economica**: 10 indicators
  - gdp_growth (IMF)
  - inflation_rate (IMF)
  - unemployment_rate (ILOSTAT)
  - gini_coefficient (World Bank)
  - poverty_headcount (World Bank)
  - trade_openness (World Bank)
  - fdi_inflows (World Bank)
  - total_factor_productivity (ECLAC)
  - inequality_ratio (ECLAC)
  - wage_inequality_gini (OECD)

---

## 🌍 Geographic Coverage

### Latin American countries supported
- Argentina (ARG)
- Brazil (BRA)
- Chile (CHL)
- Colombia (COL)
- Mexico (MEX)
- Peru (PER)
- Uruguay (URY)

### Global coverage available
- ILOSTAT: 190+ countries
- OECD: 38+ member countries
- IMF: 190+ countries
- World Bank: 190+ countries
- ECLAC: 30+ LAC countries

---

## ⚙️ API Configuration

### Setting API Keys (if required)
Create/update `.env` file:
```bash
OPENROUTER_API_KEY=your_key_here
```

All data sources used in this tool are **public and free** - no API keys required for data retrieval.

---

## 💡 Best Practices

1. **Check data availability**: Use `search` command to verify indicator exists before downloading
2. **Specify country codes**: Narrowing to specific countries reduces download time
3. **Year ranges**: Use realistic year ranges for your data source
4. **Source reliability**: World Bank and IMF data are most comprehensive for global macroeconomic data
5. **ECLAC for LAC**: Use ECLAC for region-specific Latin American analysis
6. **ILO for labor**: Use ILOSTAT for detailed labor market statistics

---

## 🔗 API Endpoints Reference

| Source | Base URL |
|--------|----------|
| ILOSTAT | `https://www.ilo.org/sdmx/rest/data` |
| OECD | `https://stats.oecd.org/sdmx-json/data` |
| IMF | `http://dataservices.imf.org/REST/SDMX_JSON.svc` |
| World Bank | `https://api.worldbank.org/v2/country` |
| ECLAC | `https://data.cepal.org/api` |

---

## 📊 Example: Multi-Source Download Workflow

Download income inequality from multiple sources:

```bash
# GINI from World Bank
python -m src.cli download --source worldbank --indicator SI.POV.GINI --topic libertad_economica

# Income ratio from ECLAC
python -m src.cli download --source eclac --indicator DESIGUALDAD --topic libertad_economica

# Wage inequality from OECD
python -m src.cli download --source oecd --dataset LAB_STAT --indicator wage_inequality_gini --topic salarios_reales
```

All datasets will be:
- ✅ Cleaned and standardized
- ✅ Saved with consistent naming convention
- ✅ Documented with automatic metadata
- ✅ Organized in topic folders
