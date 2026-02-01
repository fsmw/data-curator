# Plan de Mejoras - Integración OWID y Preparación para Agentes IA

**Fecha:** 2026-02-01  
**Versión:** 1.0  
**Estado:** En desarrollo - Fase 1

---

## Resumen Ejecutivo

Este documento detalla el plan para potenciar el Mises Data Curator mediante una integración profunda con Our World in Data (OWID) y la preparación de la aplicación para operación con agentes IA. El objetivo es simplificar la obtención de datos de OWID y estructurarlos de manera que agentes de IA puedan analizarlos eficientemente.

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

## Fase 2: Preparación para Agentes IA

### 2.1 Chat con Contexto de Datos
**Objetivo:** Permitir conversación natural sobre datasets disponibles.

**Features:**
- [ ] Integrar chat con información de datasets locales
- [ ] Permitir consultas en lenguaje natural
- [ ] Buscar y sugerir datasets relevantes
- [ ] Generar análisis automáticos
- [ ] Crear visualizaciones desde chat

**Archivos:**
- `src/web/templates/chat.html` - Mejorar UI
- `src/ai_chat.py` - Ampliar capacidades
- `src/chat_tools.py` - Nuevas herramientas para agente

**Estimación:** 6-8 horas

### 2.2 Análisis Exploratorio Automático (EDA)
**Objetivo:** Generar análisis estadístico automático al descargar datasets.

**Features:**
- [ ] Estadísticas descriptivas
- [ ] Detección de outliers
- [ ] Identificación de tendencias
- [ ] Comparaciones regionales automáticas
- [ ] Sugerencias de correlaciones

**Archivos:**
- `src/auto_eda.py` - Nuevo módulo de análisis
- Integrar en pipeline de descarga

**Estimación:** 5-6 horas

### 2.3 Data Quality Dashboard
**Objetivo:** Proporcionar métricas de calidad de datos.

**Features:**
- [ ] Score de calidad por dataset
- [ ] Cobertura temporal por país
- [ ] Completitud de datos
- [ ] Consistencia temporal
- [ ] Flags de datos faltantes

**Archivos:**
- `src/quality_checker.py` - Nuevo módulo
- `src/web/templates/quality.html` - Vista de calidad

**Estimación:** 4-5 horas

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

## Implementación Inmediata (Próximos Pasos)

### Tarea 1: Mejorar OWIDSource con Metadata Enriquecida
**Prioridad:** Alta  
**Duración:** 2-3 horas

**Pasos:**
1. Extender `OWIDSource` para descargar metadata JSON
2. Extraer campos clave (descripción, metodología, fuentes)
3. Guardar metadata en formato estructurado
4. Actualizar pipeline de documentación

### Tarea 2: Crear Módulo AI Packager
**Prioridad:** Alta  
**Duración:** 3-4 horas

**Pasos:**
1. Crear `src/ai_packager.py`
2. Definir estructura estándar de salida
3. Generar schema.json automáticamente
4. Crear templates de prompts por tema
5. Integrar en comando `pipeline`

### Tarea 3: Extender Búsqueda Semántica
**Prioridad:** Media  
**Duración:** 3-4 horas

**Pasos:**
1. Mejorar `DynamicSearcher` para usar OWID semantic API
2. Agregar filtros por tema en UI
3. Mostrar indicador de actualización
4. Agregar preview de datos

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

## Notas

- OWID usa licencia CC BY 4.0 - requiere atribución
- APIs están en desarrollo activo - puede haber cambios
- ETL catalog se actualiza diariamente
- Rate limits: TBD (contactar info@ourworldindata.org)

---

**Última actualización:** 2026-02-01  
**Responsable:** AI Development Team
