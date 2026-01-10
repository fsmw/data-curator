# Mises Data Curation Tool

🔧 Una herramienta Python modular para automatizar la curaduria de datos económicos, con generación de metadata inteligente mediante LLM (OpenRouter).

## 🎯 Características

- **Ingesta automatizada** de datos desde ILOSTAT, OECD, IMF y fuentes manuales
- **Limpieza estandarizada** con normalización de países, fechas y valores faltantes
- **Generación de metadata con IA** usando OpenRouter (Claude, GPT-4, etc.)
- **Convenciones de nomenclatura** automáticas siguiendo el patrón `{topic}_{source}_{coverage}_{years}.csv`
- **Estructura de directorios** organizada para datos crudos, limpios, metadata y gráficos
- **CLI intuitiva** para orquestar todo el pipeline de curaduria

## 📁 Estructura del Proyecto

```
mises/
├── 01_Raw_Data_Bank/          # Datos crudos por fuente
│   ├── ILOSTAT/
│   ├── OECD/
│   ├── IMF/
│   └── Institutos_Nacionales/
│
├── 02_Datasets_Limpios/        # Datos procesados por tema
│   ├── salarios_reales/
│   ├── informalidad_laboral/
│   ├── presion_fiscal/
│   └── libertad_economica/
│
├── 03_Metadata_y_Notas/        # Documentación generada
│   ├── salarios_reales.md
│   ├── informalidad_laboral.md
│   └── ...
│
├── 04_Graficos_Asociados/      # Visualizaciones
│
├── src/                         # Código fuente
│   ├── cli.py                  # Interfaz de línea de comandos
│   ├── config.py               # Gestión de configuración
│   ├── ingestion.py            # Módulo de ingesta
│   ├── cleaning.py             # Pipeline de limpieza
│   └── metadata.py             # Generador de metadata con LLM
│
├── config.yaml                  # Configuración del proyecto
├── .env                         # API keys (no versionado)
├── .env.example                 # Plantilla de configuración
└── requirements.txt             # Dependencias Python
```

## 🚀 Instalación

### 1. Clonar y configurar entorno

```bash
cd c:\dev\mises
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

### 2. Configurar API keys

Copiar `.env.example` a `.env` y agregar tus claves:

```bash
copy .env.example .env
```

Editar `.env`:

```env
# OpenRouter API para metadata con LLM
OPENROUTER_API_KEY=tu_clave_openrouter_aqui
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# APIs de fuentes de datos (opcional)
OECD_API_KEY=
IMF_API_KEY=
```

**Obtener clave de OpenRouter**: https://openrouter.ai/keys

### 3. Inicializar estructura

```bash
python -m src.cli init
```

Esto crea todas las carpetas necesarias automáticamente.

## 📖 Uso

### Comando básico

```bash
python -m src.cli [comando] [opciones]
```

### Comandos disponibles

#### 1. `init` - Inicializar proyecto

```bash
python -m src.cli init
```

Crea la estructura de directorios completa.

#### 2. `ingest` - Importar datos

**Cargar archivo manual:**
```bash
python -m src.cli ingest --source manual --filepath datos_brutos.csv
```

**Desde ILOSTAT/OECD/IMF (en desarrollo):**
```bash
python -m src.cli ingest --source ilostat --indicator LAB_INF
python -m src.cli ingest --source oecd --dataset PRICES
```

Note: The Textual-based TUI has been removed from this distribution. Use the CLI (`python -m src.cli`) or the Web server (`python -m src.web`) instead.

#### 3. `clean` - Limpiar datos

```bash
python -m src.cli clean datos_brutos.csv \
    --topic salarios_reales \
    --source owid \
    --coverage latam \
    --start-year 2000 \
    --end-year 2024
```

**Parámetros:**
- `--topic`: Tema del dataset (ej: salarios_reales, informalidad_laboral)
- `--source`: Fuente de datos (ej: owid, ilostat, imf)
- `--coverage`: Cobertura geográfica (ej: latam, global, europa)
- `--start-year/--end-year`: Se autodetectan si no se especifican

**Salida:** `02_Datasets_Limpios/{topic}/{topic}_{source}_{coverage}_{start}_{end}.csv`

#### 4. `document` - Generar metadata

```bash
python -m src.cli document 02_Datasets_Limpios/salarios_reales/salarios_reales_owid_latam_2000_2024.csv \
    --topic salarios_reales \
    --source owid \
    --url https://ourworldindata.org/grapher/real-wages
```

**Opciones:**
- `--force`: Regenerar metadata (ignorar cache)
- `--url`: URL de la fuente original

**Salida:** `03_Metadata_y_Notas/{topic}.md`

#### 5. `pipeline` - Pipeline completo

Ejecuta limpieza + documentación en un solo comando:

```bash
python -m src.cli pipeline datos_brutos.csv \
    --topic informalidad_laboral \
    --source ilostat \
    --coverage latam \
    --url https://ilostat.ilo.org/data/
```

#### 6. `status` - Ver estado del proyecto

```bash
python -m src.cli status
```

Muestra:
- Estado de directorios
- Cantidad de datasets procesados
- Archivos de metadata generados
- Configuración de API keys

## 🤖 Generación de Metadata con LLM

La herramienta usa **OpenRouter** (API compatible con OpenAI) para generar documentación profesional automáticamente.

### Modelos recomendados

| Modelo | Uso | Costo | Calidad |
|--------|-----|-------|---------|
| `openai/gpt-4o-mini` | Desarrollo/testing | 💰 Muy bajo | ⭐⭐⭐ |
| `anthropic/claude-3.5-sonnet` | Producción | 💰💰 Medio | ⭐⭐⭐⭐⭐ |
| `google/gemini-pro-1.5` | Alternativa | 💰 Bajo | ⭐⭐⭐⭐ |

### Configurar modelo

En `.env`:
```env
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

O en `config.yaml` (temperatura, max_tokens, system prompt).

### Cache de metadata

Por defecto, la metadata generada se cachea para evitar costos duplicados. Para regenerar:

```bash
python -m src.cli document archivo.csv --topic tema --source fuente --force
```

### Fallback sin LLM

Si no hay API key o falla la conexión, usa plantilla automática basada en reglas.

## ⚙️ Configuración Avanzada

### `config.yaml`

```yaml
# Personalizar directorios
directories:
  raw: "01_Raw_Data_Bank"
  clean: "02_Datasets_Limpios"
  metadata: "03_Metadata_y_Notas"
  graphics: "04_Graficos_Asociados"

# Agregar temas/fuentes
topics:
  - salarios_reales
  - informalidad_laboral
  - mi_nuevo_tema

sources:
  - ILOSTAT
  - OECD
  - Mi_Fuente_Custom

# Reglas de limpieza
cleaning:
  drop_empty_rows: true
  standardize_country_codes: true
  normalize_dates: true

# Configuración LLM
llm:
  max_tokens: 2000
  temperature: 0.3
  system_prompt: |
    Tu prompt personalizado aquí...
```

## 📊 Ejemplos de Uso Completo

### Ejemplo 1: Dataset manual de salarios

```bash
# 1. Importar archivo Excel manualmente descargado
python -m src.cli ingest --source manual --filepath salarios_latam_raw.xlsx

# 2. Pipeline completo: limpia + documenta
python -m src.cli pipeline 01_Raw_Data_Bank/Institutos_Nacionales/salarios_latam_raw_*.csv \
    --topic salarios_reales \
    --source indec \
    --coverage argentina \
    --url https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-31-61
```

### Ejemplo 2: Procesar múltiples datasets

```bash
# Limpiar datasets
python -m src.cli clean datos1.csv --topic informalidad_laboral --source ilostat --coverage latam
python -m src.cli clean datos2.csv --topic presion_fiscal --source oecd --coverage oecd_members

# Ver estado
python -m src.cli status
```

## 🛠️ Desarrollo Futuro (Roadmap)

- [ ] Implementar clientes API completos (ILOSTAT SDMX, OECD, IMF)
- [ ] Soporte para actualizaciones incrementales
- [ ] Dashboard web con Streamlit/Dash
- [ ] Validación de esquemas con Pydantic
- [ ] Tests automatizados
- [ ] Exportación a formatos adicionales (Parquet, Feather)
- [ ] Integración con dbt para pipelines de datos

## 🤝 Contribuir

Este es un proyecto en desarrollo activo. Sugerencias y PRs bienvenidos!

## 📄 Licencia

MIT License - Ver LICENSE para detalles

---

**Mises Data Curation Tool v0.1.0** - Automatizando la curaduria de datos económicos 📊✨
