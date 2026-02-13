# Mises Data Curation Tool

🔧 Una herramienta Python modular para automatizar la curaduria de datos económicos, con generación de metadata inteligente mediante GitHub Copilot SDK.

**Interfaces disponibles:**
- **CLI** - Interfaz de línea de comandos
- **Web API** - API REST con Flask

## 🎯 Características

- **Ingesta automatizada** de datos desde ILOSTAT, OECD, IMF y fuentes manuales
- **Limpieza estandarizada** con normalización de países, fechas y valores faltantes
- **Generación de metadata con IA** usando GitHub Copilot SDK
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

### 2. Configurar Copilot CLI y variables opcionales

Copiar `.env.example` a `.env` para variables opcionales de fuentes y modelo:

```bash
copy .env.example .env
```

Editar `.env` (opcional):

```env
# Copilot model preference (optional)
COPILOT_MODEL=gpt-5-mini

# APIs de fuentes de datos (opcional)
OECD_API_KEY=
IMF_API_KEY=

```

Autentica Copilot CLI en tu entorno con `copilot` y el comando `/login`.

### 3. Inicializar estructura

```bash
python -m src.cli init
```

Esto crea todas las carpetas necesarias automáticamente.

## 📖 Uso

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

## 🤖 Generación de Metadata con IA

La herramienta usa **GitHub Copilot SDK** para generar documentación profesional automáticamente.

### Modelos recomendados

| Modelo | Uso | Costo | Calidad |
|--------|-----|-------|---------|
| `gpt-5-mini` | Desarrollo/testing | Según plan Copilot | ⭐⭐⭐ |
| `claude-haiku-4.5` | Respuestas rápidas | Según plan Copilot | ⭐⭐⭐⭐ |
| `claude-sonnet-4.5` | Producción | Según plan Copilot | ⭐⭐⭐⭐⭐ |

### Configurar modelo

En `.env` (opcional):
```env
COPILOT_MODEL=gpt-5-mini
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
