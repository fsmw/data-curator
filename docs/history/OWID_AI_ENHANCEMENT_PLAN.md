# Plan de Mejoras - Integración OWID y GitHub Copilot SDK

**Fecha:** 2026-02-01  
**Versión:** 2.0  
**Estado:** En desarrollo - Fase 1

---

## Resumen Ejecutivo

Este documento detalla el plan para transformar el **Mises Data Curator** en una plataforma inteligente de curaduría de datos económicos, integrando:

1. **Our World in Data (OWID)** - Fuente de datos enriquecidos con metadatos
2. **GitHub Copilot SDK** - Motor de agentes IA production-tested

**Visión**: En lugar de construir orquestación de agentes desde cero, utilizamos el **GitHub Copilot SDK** (Technical Preview) que expone el mismo runtime de agentes que potencia Copilot CLI. Esto nos permite enfocarnos en herramientas específicas de curaduría de datos mientras el SDK maneja: planning, tool invocation, memoria persistente, y multi-turn conversations.

**Resultado Esperado**: Un asistente de datos conversacional que permite a usuarios interactuar con datos económicos usando lenguaje natural, con capacidades avanzadas de análisis, visualización y descubrimiento automatizado.

---

## Análisis de Infraestructura OWID

### APIs Disponibles
1. **Charts API**: Acceso directo a datos de gráficos individuales
2. **Tables API**: Búsqueda en catálogo ETL
3. **Indicators API**: Búsqueda semántica por similitud textual
4. **Search API**: Equivalente al buscador web (powered by Algolia)

### Formatos de Datos
- **CSV**: `/{slug}.csv?csvType=full&useColumnShortNames=true`
- **JSON Metadata**: `/{slug}.metadata.json`
- **ZIP**: CSV + metadata + README
- **Python SDK**: `owid-data` para acceso programático

### Metadatos Enriquecidos
- Descripción del indicador
- Metodología de medición
- Limitaciones conocidas
- Unidades de medida
- Fuentes originales
- Fecha de última actualización
- Licencia (CC BY 4.0)

---

## Infraestructura de Agentes - GitHub Copilot SDK

### ¿Por qué GitHub Copilot SDK?

**Problema**: Construir agentes IA desde cero requiere:
- Orquestación de herramientas (tool calling)
- Gestión de contexto y memoria
- Planning y ejecución multi-step
- Manejo de múltiples modelos LLM
- Integración con fuentes de datos
- Manejo de errores y fallbacks

**Solución**: GitHub Copilot SDK proporciona todo esto listo para usar.

### Arquitectura del SDK

```
┌─────────────────────────────────────────────────────────────┐
│                    Mises Data Curator                       │
│  (Flask Web App + CLI)                                      │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Copilot SDK (Python)                    │
│  pip install github-copilot-sdk                             │
│                                                             │
│  • Planning & Orchestration                                 │
│  • Tool Invocation (MCP Servers)                            │
│  • Multi-turn Conversations                                 │
│  • Persistent Memory                                        │
│  • Multi-Model Support (GPT-4, Claude, etc.)                │
└──────────────┬──────────────────────────────────────────────┘
               │ JSON-RPC
               ▼
┌─────────────────────────────────────────────────────────────┐
│              GitHub Copilot CLI (Server Mode)               │
│  • Production-tested agent runtime                          │
│  • Authentication & Billing                                 │
│  • Model Management                                         │
└──────────────┬──────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Provider (BYOK)                            │
│  • OpenAI API                                               │
│  • Azure OpenAI                                             │
│  • Anthropic Claude                                         │
└─────────────────────────────────────────────────────────────┘
```

### Herramientas Personalizadas (MCP Tools)

El SDK permite exponer nuestras funcionalidades como herramientas que el agente puede invocar:

```python
# Herramientas de Mises Data Curator para Copilot

async def search_datasets(
    query: str, 
    source: Optional[str] = None,
    topic: Optional[str] = None
) -> List[Dict]:
    """Buscar datasets en el catálogo por texto, fuente o tema."""

async def preview_data(
    dataset_id: str, 
    limit: int = 10
) -> Dict:
    """Obtener vista previa de un dataset (primeras N filas)."""

async def download_owid(
    slug: str,
    countries: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None
) -> Dict:
    """Descargar datos desde Our World in Data."""

async def analyze_data(
    dataset_id: str,
    analysis_type: str  # "summary", "trends", "outliers", "correlations"
) -> Dict:
    """Ejecutar análisis automático sobre un dataset."""

async def generate_chart(
    dataset_id: str,
    chart_type: str,  # "line", "bar", "scatter", "map"
    x_column: Optional[str] = None,
    y_column: Optional[str] = None
) -> str:
    """Generar visualización desde datos."""

async def get_metadata(
    dataset_id: str
) -> Dict:
    """Obtener metadata completa de un dataset."""

async def compare_datasets(
    dataset_ids: List[str],
    metric: str
) -> Dict:
    """Comparar múltiples datasets en una métrica específica."""
```

### Flujo de Interacción con el Agente

```
Usuario: "Compara el crecimiento de PIB entre Brasil y Argentina 2010-2023"

Agente (Copilot SDK):
1. PLAN: Descompone la solicitud
   └─ Buscar datos de PIB
   └─ Filtrar Brasil y Argentina
   └─ Extraer periodo 2010-2023
   └─ Calcular comparación
   └─ Generar visualización

2. EXECUTE: Invoca herramientas
   ├─ search_datasets(query="GDP", source="owid")
   ├─ download_owid(slug="gdp-per-capita", countries=["BRA", "ARG"], ...)
   ├─ analyze_data(analysis_type="comparison")
   └─ generate_chart(chart_type="line")

3. RESPOND: Presenta resultados
   └─ "Encontré datos de PIB per cápita para Brasil y Argentina...
        Argentina mostró un crecimiento promedio de X% mientras que Brasil...
        [Gráfico generado]"
```

### Ventajas para Nuestro Sistema

1. **No reinventar la rueda**: Planning, tool orchestration, memory management incluidos
2. **Multi-turn conversations**: Contexto persistente entre mensajes
3. **BYOK (Bring Your Own Key)**: Control total sobre costos y privacidad
4. **Multi-model**: GPT-4, Claude, Azure OpenAI según necesidad
5. **Python-native**: Integración perfecta con nuestro stack Flask
6. **MCP Support**: Exponer herramientas usando Model Context Protocol
7. **Streaming**: Respuestas en tiempo real

### Requisitos

- **GitHub Copilot CLI** instalado (prerrequisito)
- **Suscripción GitHub Copilot** (o BYOK con API keys propias)
- **Python SDK**: `pip install github-copilot-sdk`

---

## Fase 1: Integración OWID Nativa Mejorada

### 1.1 OWID Smart Search
**Objetivo:** Implementar búsqueda semántica avanzada usando la API de indicadores de OWID.

**Features:**
- [ ] Autocompletado con 20,000+ datasets
- [ ] Sugerencias basadas en similitud textual
- [ ] Filtros por tema (Population, Health, Energy, Food, Poverty, Education)
- [ ] Indicador de "última actualización"
- [ ] Preview de datos antes de descargar

**Archivos a modificar:**
- `src/searcher.py` - Extender para búsqueda semántica
- `src/web/templates/search.html` - UI mejorada
- `src/web/static/js/app.js` - Lógica frontend
- `src/dynamic_search.py` - Integración API OWID

**Estimación:** 3-4 horas

### 1.2 Enriquecimiento Automático de Metadatos
**Objetivo:** Extraer automáticamente metadatos completos de OWID y guardarlos en formato AI-friendly.

**Features:**
- [ ] Descargar JSON metadata automáticamente
- [ ] Extraer y estructurar:
  - Descripción del indicador
  - Metodología
  - Limitaciones
  - Unidades
  - Fuentes
- [ ] Guardar como `context.md` en carpeta de dataset
- [ ] Crear schema.json para estructura de datos

**Estructura de salida:**
```
02_Datasets_Limpios/{topic}/
├── {topic}_{source}_{coverage}_{start}_{end}.csv
├── metadata.md          # Generado por LLM
├── context_owid.md      # Extraído de OWID
├── schema.json          # Estructura para IA
└── prompts.json         # Prompts sugeridos
```

**Archivos a modificar:**
- `src/ingestion.py` - OWIDSource mejorado
- `src/metadata.py` - Enriquecer con contexto OWID
- `src/cleaning.py` - Generar schema automáticamente

**Estimación:** 4-5 horas

### 1.3 AI-Ready Dataset Packaging
**Objetivo:** Estructurar datasets para consumo óptimo por agentes IA.

**Features:**
- [ ] Crear paquete estandarizado por dataset
- [ ] Incluir contexto completo para prompts
- [ ] Definir schema JSON con tipos y descripciones
- [ ] Generar prompts sugeridos por tipo de dataset
- [ ] Normalizar nombres de columnas

**Archivos a crear:**
- `src/ai_packager.py` - Nuevo módulo para packaging
- Templates de prompts por categoría temática

**Estimación:** 3-4 horas

---

## Fase 2: Integración GitHub Copilot SDK - Core

### 2.1 Setup y Configuración del SDK
**Objetivo:** Instalar y configurar GitHub Copilot SDK.

**Pasos:**
- [ ] Instalar GitHub Copilot CLI
- [ ] Instalar Python SDK: `pip install github-copilot-sdk`
- [ ] Configurar conexión SDK ←→ CLI
- [ ] Configurar BYOK (traer nuestras propias API keys)
- [ ] Crear módulo `src/copilot_agent.py`
- [ ] Implementar cliente básico

**Archivos:**
- `src/copilot_agent.py` - Cliente del SDK
- `config.yaml` - Configuración del agente
- `.env` - API keys para BYOK

**Estimación:** 3-4 horas

### 2.2 Crear Herramientas MCP (Model Context Protocol)
**Objetivo:** Exponer funcionalidades de Mises como herramientas invocables.

**Herramientas a implementar:**
- [ ] `search_datasets` - Búsqueda en catálogo
- [ ] `preview_data` - Vista previa de datos
- [ ] `download_owid` - Descarga desde OWID
- [ ] `get_metadata` - Obtener metadata
- [ ] `analyze_data` - Análisis automático

**Archivos:**
- `src/copilot_tools.py` - Definiciones de herramientas MCP
- `src/copilot_registry.py` - Registro de herramientas

**Estimación:** 6-8 horas

### 2.3 Endpoint de Chat con Agente
**Objetivo:** Crear endpoint para conversación con el agente Copilot.

**Features:**
- [ ] WebSocket endpoint `/api/chat/copilot`
- [ ] Soporte streaming de respuestas
- [ ] Manejo de sesiones (session_id)
- [ ] Integración con herramientas MCP
- [ ] Fallback a chat anterior si SDK falla

**Archivos:**
- `src/web/routes.py` - Nuevo endpoint
- `src/web/static/js/copilot-chat.js` - Frontend
- `src/web/templates/copilot-chat.html` - UI

**Estimación:** 4-6 horas

### 2.4 Análisis Exploratorio Automático (EDA) via Agente
**Objetivo:** Usar el agente para generar análisis automáticos.

**Features:**
- [ ] Herramienta `analyze_data` con múltiples modos:
  - `summary` - Estadísticas descriptivas
  - `trends` - Análisis de tendencias
  - `outliers` - Detección de anomalías
  - `correlations` - Matriz de correlación
- [ ] Prompts optimizados para cada análisis
- [ ] Cache de resultados de análisis

**Archivos:**
- `src/copilot_tools.py` - Agregar herramienta analyze_data
- `src/analysis_prompts.py` - Prompts especializados

**Estimación:** 4-5 horas

---

## Fase 3: Capacidades Avanzadas con Copilot SDK

### 3.1 Natural Language Queries
**Objetivo:** Permitir consultas complejas en lenguaje natural.

**Ejemplos a soportar:**
```
"Población de Brasil vs Argentina últimos 10 años"
"Correlación entre PIB y esperanza de vida en LATAM"
"Datasets sobre desigualdad disponibles"
"Análisis de tendencias de inflación"
```

**Implementación:**
- [ ] Usar planning loop del SDK para descomponer queries
- [ ] Multi-step execution automático
- [ ] Confirmación intermedia para operaciones destructivas
- [ ] Manejo de ambigüedad ("¿Te refieres a X o Y?")

**Archivos:**
- `src/copilot_agent.py` - Mejorar handling de queries
- `src/query_parser.py` - Parser de intenciones (opcional)

**Estimación:** 8-10 horas

### 3.2 Personas del Agente
**Objetivo:** Crear especialidades del agente para diferentes tareas.

**Personas:**
- **Data Explorer**: Enfocado en descubrimiento
  - "¿Qué datasets interesantes tenemos sobre...?"
  - "Sugiéreme análisis interesantes para este dataset"
  
- **Data Analyst**: Enfocado en análisis estadístico
  - "Calcula la correlación entre estas variables"
  - "Identifica tendencias significativas"
  
- **Data Curator**: Enfocado en gestión de datos
  - "Verifica la calidad de este dataset"
  - "Documenta las fuentes y metodología"

**Implementación:**
- [ ] System prompts especializados por persona
- [ ] Herramientas disponibles varían por persona
- [ ] Switch de persona en UI

**Archivos:**
- `src/copilot_personas.py` - Definición de personas
- `src/system_prompts/` - Prompts por persona

**Estimación:** 6-8 horas

### 3.3 Contexto Persistente (Work IQ Style)
**Objetivo:** El agente recuerda contexto entre sesiones.

**Features:**
- [ ] Memoria de datasets descargados por el usuario
- [ ] Historial de análisis previos
- [ ] Preferencias del usuario (formatos, temas favoritos)
- [ ] "Basándome en tu trabajo anterior..."

**Implementación:**
- [ ] Usar memoria persistente del SDK
- [ ] Integrar con base de datos de usuarios (si aplica)
- [ ] Context injection en cada conversación

**Archivos:**
- `src/copilot_memory.py` - Gestión de contexto
- Base de datos SQLite para memoria (opcional)

**Estimación:** 4-6 horas

### 3.4 Multi-Agent Workflows (Microsoft 365 SDK)
**Objetivo:** Integrar con Microsoft 365 Agents SDK para flujos complejos.

**Escenarios:**
- Reporte de investigación automatizado:
  1. Data Explorer (busca datos)
  2. Data Analyst (analiza)
  3. Report Writer (genera documento)
  4. Teams Agent (comparte en canal)

**Implementación:**
- [ ] Integración M365 Agents SDK
- [ ] Definición de workflows
- [ ] Handoff entre agentes

**Archivos:**
- `src/multi_agent.py` - Orquestación multi-agente

**Estimación:** 8-10 horas (futuro)

---

## Fase 3: Capacidades Avanzadas

### 3.1 Natural Language Queries
**Objetivo:** Permitir consultas en lenguaje natural que se traduzcan a operaciones de datos.

**Ejemplo:**
```
Input: "Población de Brasil vs Argentina últimos 10 años"
↓
Agente:
1. Identifica dataset: population
2. Filtra países: BRA, ARG
3. Rango: 2014-2024
4. Genera comparación
```

**Archivos:**
- `src/nlq_engine.py` - Motor de procesamiento NL
- Integración con LLM para parsing

**Estimación:** 8-10 horas

### 3.2 Cross-Source Data Fusion
**Objetivo:** Combinar automáticamente datasets de múltiples fuentes.

**Features:**
- [ ] Identificar datasets relacionados
- [ ] Pre-calcular joins comunes
- [ ] Enriquecer datasets con variables complementarias
- [ ] Generar vistas consolidadas

**Archivos:**
- `src/data_fusion.py` - Nuevo módulo
- `src/fusion_rules.yaml` - Reglas de combinación

**Estimación:** 6-8 horas

### 3.3 Versionado y Lineage
**Objetivo:** Tracking de versiones y notificaciones de actualización.

**Features:**
- [ ] Versionado de datasets
- [ ] Notificación de actualizaciones en fuentes
- [ ] Comparación entre versiones
- [ ] Rollback capabilities

**Archivos:**
- `src/versioning.py` - Nuevo módulo
- Extender catálogo para versiones

**Estimación:** 5-6 horas

---

## Sinergia OWID + Copilot SDK

### Flujo de Trabajo Integrado

```
┌────────────────────────────────────────────────────────────┐
│  1. DISCOVER (OWID Smart Search)                          │
│     Usuario busca "crecimiento poblacional américa latina" │
│     ↓                                                       │
│  2. DOWNLOAD (OWID API + AI Packager)                     │
│     Descarga datos + crea AI package (schema, context)      │
│     ↓                                                       │
│  3. EXPLORE (Copilot SDK + Herramientas)                  │
│     Usuario: "Analiza tendencias 2010-2023"                │
│     Agente:                                                 │
│       • Usa tool analyze_data()                            │
│       • Lee context_owid.md para metodología              │
│       • Interpreta schema.json para estructura            │
│       • Genera insights y visualizaciones                 │
│     ↓                                                       │
│  4. COLLABORATE (Copilot SDK Chat)                        │
│     Conversación iterativa con memoria persistente         │
│     "¿Cómo se compara con Europa?" → Agente busca datos    │
└────────────────────────────────────────────────────────────┘
```

### Ventajas de la Integración

1. **OWID proporciona**: Datos de alta calidad + metadatos ricos + contexto metodológico
2. **AI Packager convierte**: Datos + metadata → Package estructurado para IA
3. **Copilot SDK habilita**: Interacción conversacional + tool calling + planning

---

## Implementación Inmediata (Próximos Pasos)

### Sprint 1: Fundamentos (Semana 1)

#### Tarea 1.1: Setup GitHub Copilot SDK
**Duración:** 3-4 horas

**Pasos:**
1. Instalar GitHub Copilot CLI
2. Instalar Python SDK: `pip install github-copilot-sdk`
3. Configurar BYOK con OpenRouter API key
4. Crear `src/copilot_agent.py` con cliente básico
5. Verificar conexión SDK → CLI

**Entregable:** Cliente SDK funcional con "hello world"

#### Tarea 1.2: Mejorar OWIDSource (Completado ✓)
**Duración:** 2-3 horas (ya implementado)

**Estado:** ✅ Métodos `fetch_metadata()` y `fetch_with_metadata()` agregados

### Sprint 2: Herramientas MCP (Semana 2)

#### Tarea 2.1: Crear 5 Herramientas Core
**Duración:** 6-8 horas

**Herramientas:**
1. `search_datasets` - Buscar en catálogo
2. `preview_data` - Vista previa
3. `download_owid` - Descargar datos
4. `get_metadata` - Obtener metadata
5. `analyze_data` - Análisis básico

**Entregable:** `src/copilot_tools.py` funcional

#### Tarea 2.2: AI Packager (Completado ✓)
**Duración:** 3-4 horas (ya implementado)

**Estado:** ✅ Módulo `src/ai_packager.py` creado con:
- Generación de schema.json
- Creación de context_owid.md
- Generación de prompts.json

### Sprint 3: Chat Interface (Semana 3)

#### Tarea 3.1: WebSocket Chat Endpoint
**Duración:** 4-6 horas

**Pasos:**
1. Crear endpoint `/api/chat/copilot`
2. Implementar streaming de respuestas
3. Manejo de sesiones
4. Integrar herramientas MCP
5. Fallback a chat anterior si falla

**Entregable:** Endpoint funcional con testing

#### Tarea 3.2: UI de Chat
**Duración:** 4-6 horas

**Pasos:**
1. Crear `src/web/templates/copilot-chat.html`
2. Implementar `copilot-chat.js` con WebSocket
3. Diseño tipo ChatGPT/Copilot
4. Indicadores de tool calling
5. Visualización de datos en chat

**Entregable:** UI funcional integrada

### Sprint 4: Features Avanzadas (Semana 4)

#### Tarea 4.1: Natural Language Queries
**Duración:** 8-10 horas

**Pasos:**
1. Soportar queries complejas
2. Multi-step planning
3. Manejo de ambigüedad
4. Confirmación intermedia

#### Tarea 4.2: Personas del Agente
**Duración:** 6-8 horas

**Pasos:**
1. Crear 3 personas (Explorer, Analyst, Curator)
2. System prompts especializados
3. Selector de persona en UI
4. Herramientas por persona

---

## Especificaciones Técnicas

### API Endpoints OWID a Integrar

```python
# Búsqueda semántica
POST https://api.ourworldindata.org/v1/indicators/search
{
  "query": "poverty rate",
  "similarity_threshold": 0.8,
  "limit": 20
}

# Datos de gráfico
GET https://ourworldindata.org/grapher/{slug}.csv?csvType=full&useColumnShortNames=true

# Metadatos
GET https://ourworldindata.org/grapher/{slug}.metadata.json
```

### Estructura AI-Ready

```json
{
  "dataset_info": {
    "id": "population-growth-rates",
    "name": "Population Growth Rate",
    "description": "Annual population growth rate including births, deaths, and migration",
    "source": "UN World Population Prospects (2024)",
    "last_updated": "2024-11-15",
    "coverage": {
      "countries": 256,
      "time_range": "1950-2100",
      "granularity": "annual"
    }
  },
  "schema": {
    "columns": [
      {
        "name": "entity",
        "type": "string",
        "description": "Country or region name"
      },
      {
        "name": "year",
        "type": "integer",
        "description": "Year of observation"
      },
      {
        "name": "growth_rate",
        "type": "float",
        "description": "Annual population growth rate (%)",
        "unit": "percentage"
      }
    ]
  },
  "context": {
    "methodology": "Calculated from UN World Population Prospects...",
    "limitations": ["Projections based on medium scenario", "Excludes some territories"],
    "units": {
      "growth_rate": "percentage of total population"
    }
  },
  "suggested_prompts": [
    "Analyze population growth trends in Latin America",
    "Compare growth rates between high and low income countries",
    "Identify countries with declining populations"
  ]
}
```

---

## Métricas de Éxito

1. **Tiempo de descarga OWID**: < 15 segundos por dataset
2. **Cobertura de metadatos**: 100% de datasets con contexto completo
3. **Calidad de búsqueda**: Top 5 resultados relevantes en 90% de consultas
4. **Preparación IA**: Todos los datasets con schema.json y prompts
5. **Satisfacción usuario**: Capacidad de encontrar y descargar datos en < 3 clicks

---

## Recursos

- **OWID API Docs**: https://docs.owid.io/projects/etl/api/
- **OWID Python SDK**: https://github.com/owid/owid-grapher-py
- **Metadatos y reutilización**: https://ourworldindata.org/easier-to-reuse-our-data
- **Catálogo ETL**: https://github.com/owid/etl

---

## Resumen Ejecutivo de la Arquitectura Integrada

### Transformación del Sistema

**Enfoque Anterior (Sin Copilot SDK):**
- Construir orquestación de agentes desde cero
- Implementar tool calling manualmente
- Gestión de contexto y memoria propia
- **Tiempo estimado**: 3-4 meses
- **Riesgo**: Alto (nuevo código, bugs, mantenimiento)

**Enfoque Nuevo (Con Copilot SDK):**
- Usar runtime production-tested de GitHub
- Foco en herramientas de dominio (datos económicos)
- BYOK para control de costos y privacidad
- **Tiempo estimado**: 4-6 semanas
- **Riesgo**: Bajo (SDK probado, comunidad activa)

### Componentes de la Solución

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA DE PRESENTACIÓN                                        │
│  • Web UI (Flask + WebSocket)                               │
│  • CLI (Click)                                              │
│  • Chat Interface (Copilot SDK + Streaming)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ORQUESTACIÓN DE AGENTES                                     │
│  GitHub Copilot SDK (Python)                                │
│  • Planning & Multi-step Execution                          │
│  • Tool Invocation (MCP)                                    │
│  • Memory & Context Management                              │
│  • Multi-Model Support (GPT-4, Claude, Azure)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  HERRAMIENTAS DE DOMINIO (MCP Tools)                        │
│  • search_datasets() - Buscar en catálogo                   │
│  • download_owid() - Descargar de OWID                      │
│  • analyze_data() - Análisis automático                     │
│  • generate_chart() - Visualizaciones                       │
│  • get_metadata() - Contexto enriquecido                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  DATOS ESTRUCTURADOS (AI-Ready)                             │
│  • CSV (datos limpios)                                      │
│  • schema.json (estructura)                                 │
│  • context_owid.md (metodología)                            │
│  • prompts.json (sugerencias)                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  FUENTES DE DATOS                                           │
│  • OWID (Our World in Data) - Principal                     │
│  • World Bank, OECD, ILOSTAT - Complementarias              │
└─────────────────────────────────────────────────────────────┘
```

### Diferenciadores Clave

1. **Datos Premium (OWID)**: Metadatos completos (metodología, limitaciones, fuentes)
2. **Runtime Probado (Copilot SDK)**: Usado por millones en GitHub Copilot CLI
3. **Estructura AI-Native**: AI Packager prepara datos específicamente para consumo por agentes
4. **Control Total (BYOK)**: Traer nuestras propias API keys (OpenRouter, Azure, etc.)
5. **Multi-Persona**: Explorer, Analyst, Curator según necesidad del usuario

### Roadmap de 4 Sprints

| Sprint | Enfoque | Entregable Principal |
|--------|---------|---------------------|
| **1** | Fundamentos | Cliente Copilot SDK funcionando |
| **2** | Herramientas | 5 MCP tools + AI Packager integrado |
| **3** | Interface | Chat WebSocket con streaming |
| **4** | Avanzado | Natural language queries + Personas |

### Recursos Adicionales

- **Análisis Detallado Copilot SDK**: `docs/GITHUB_COPILOT_SDK_ANALYSIS.md`
- **Repositorio SDK**: https://github.com/github/copilot-sdk
- **Getting Started**: https://github.com/github/copilot-sdk/blob/main/docs/getting-started.md
- **Cookbook**: https://github.com/github/copilot-sdk/tree/main/cookbook/python

---

## Notas

- **OWID**: Usa licencia CC BY 4.0 - requiere atribución
- **Copilot SDK**: Technical Preview - posibles cambios API (mantener abstracción)
- **BYOK**: Recomendado para control de costos y privacidad
- **MCP**: Model Context Protocol estándar para tool calling
- **ETL catalog**: Se actualiza diariamente

---

**Versión del Plan**: 2.0  
**Última actualización**: 2026-02-01  
**Estado**: ✅ Integración Copilot SDK completada en documentación  
**Próximo paso**: Implementación Sprint 1 (Setup SDK)  
**Responsable**: AI Development Team
