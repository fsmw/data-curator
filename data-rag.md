# Sistema RAG para Agente OWID
## Documento de Diseño Técnico

---

## 1. PROBLEMA Y OBJETIVO

### 1.1 El problema actual

El agente Copilot opera en cada turno conversacional con contexto limitado:

**Sin memoria de datos disponibles**: Cuando el usuario pregunta "¿qué datos tengo sobre América Latina?", el agente debe llamar a `list_local_datasets` y luego a `get_metadata` para cada dataset. No "sabe" qué tiene hasta que lo consulta. Cada turno empieza desde cero.

**Sin memoria conversacional persistente**: Si en el turno 1 el usuario construyó un panel de Foreign Aid + State Capacity, en el turno 15 el agente ya no recuerda ese contexto. El window de contexto del LLM se llena y los primeros mensajes se pierden.

**Sin conocimiento profundo de los datos**: El agente sabe que existe un dataset llamado "tax-revenue-gdp", pero no sabe que Chile tiene datos desde 1990, que Perú tiene un gap en 2005-2007, o que el indicador cambió de metodología en 2014. Esa información existe en los datos y metadatos, pero no está accesible conversacionalmente.

**Sin guía metodológica contextual**: Cuando el usuario pide "correlaciona ayuda con crecimiento", el agente no tiene un corpus de mejores prácticas econométricas que le diga "para datos de panel, usa correlación within, no pooled".

### 1.2 Objetivo del sistema RAG

Dotar al agente de una **memoria estructurada y recuperable** que le permita:

1. **Saber qué datos tiene** sin consultar tools en cada turno
2. **Recordar qué se hizo** en la conversación y en conversaciones anteriores
3. **Conocer los datos en profundidad** (cobertura, calidad, limitaciones)
4. **Aplicar conocimiento metodológico** relevante al análisis solicitado
5. **Mejorar la selección y uso de tools** basándose en contexto acumulado

### 1.3 Principio de diseño

```
Sin RAG:  Usuario pregunta → LLM adivina → llama tools → prueba y error
Con RAG:  Usuario pregunta → Recupera contexto relevante → LLM decide informado → acción precisa
```

El RAG NO reemplaza las tools. Las complementa inyectando conocimiento contextual en el prompt del LLM antes de que decida qué tool invocar y con qué parámetros.

---

## 2. ARQUITECTURA GENERAL

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USUARIO (Flask UI)                           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ mensaje del usuario
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      ORQUESTADOR (Flask backend)                     │
│                                                                      │
│  1. Recibe mensaje del usuario                                       │
│  2. Invoca RAG Retriever → obtiene contexto relevante                │
│  3. Construye prompt enriquecido (mensaje + contexto RAG)            │
│  4. Envía a Copilot LLM                                              │
│  5. LLM decide: responder directamente O invocar tool(s)             │
│  6. Si invocó tool: ejecutar, obtener resultado                      │
│  7. Post-procesamiento: indexar nueva información en RAG             │
│  8. Retornar respuesta al usuario                                    │
│                                                                      │
└────────┬──────────────┬──────────────────┬──────────────────────────┘
         │              │                  │
         ▼              ▼                  ▼
┌────────────┐  ┌───────────────┐  ┌──────────────────┐
│ RAG Engine │  │ Copilot LLM   │  │ MCP Tool Server  │
│            │  │               │  │ (15 tools exist.) │
│ • Indexer  │  │ • Razona      │  │ • search_datasets │
│ • Retriever│  │ • Planifica   │  │ • download_owid   │
│ • Store    │  │ • Genera      │  │ • run_sql_query   │
│            │  │               │  │ • analyze_data    │
│            │  │               │  │ • ...             │
└────────────┘  └───────────────┘  └──────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│          VECTOR STORE (ChromaDB)          │
│   Colecciones:                            │
│   • dataset_catalog    (qué datos hay)    │
│   • dataset_profiles   (cómo son)         │
│   • tool_knowledge     (cómo usar tools)  │
│   • methodology        (mejores prácticas)│
│   • conversation_memory(qué se hizo)      │
│   • analysis_results   (qué se encontró)  │
└──────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│          SQLite (datos existentes)         │
│   • Datasets OWID descargados             │
│   • Metadatos                             │
│   • Versiones / forks                     │
└──────────────────────────────────────────┘
```

---

## 3. COLECCIONES DEL VECTOR STORE

El RAG se organiza en 6 colecciones, cada una con un propósito específico y una estrategia de indexación distinta.

### 3.1 `dataset_catalog` — Qué datos existen

**Propósito**: Que el agente "sepa" qué datasets están disponibles (locales y remotos) sin llamar a tools.

**Cuándo se indexa**: 
- Al ejecutar `download_owid` (automático post-descarga)
- Carga inicial desde catálogo OWID (batch)
- Re-indexación periódica (detectar datasets nuevos en OWID)

**Schema de cada documento:**

```python
{
    "id": "dataset_tax-revenue-gdp",
    "text": """
        Dataset: Tax revenue as share of GDP.
        Tema: Taxation, Government Revenue, Fiscal Policy.
        Fuente original: OECD Revenue Statistics, ICTD/UNU-WIDER GRD.
        Descripción: Total tax revenue collected by governments as a 
        percentage of GDP. Includes income tax, corporate tax, VAT, 
        excise duties, property taxes, and social contributions.
        Sinónimos: recaudación fiscal, presión tributaria, carga impositiva,
        tax burden, fiscal pressure, impuestos como porcentaje del PIB.
        Disponible localmente: sí.
        Tabla SQL: tax_revenue_gdp.
        Última descarga: 2025-01-15.
    """,
    "metadata": {
        "slug": "tax-revenue-gdp",
        "topic": "taxation",
        "source": "OECD/ICTD",
        "is_local": True,
        "sql_table": "tax_revenue_gdp",
        "countries_count": 157,
        "year_min": 1965,
        "year_max": 2022,
        "last_downloaded": "2025-01-15",
        "owid_url": "https://ourworldindata.org/grapher/tax-revenue-gdp"
    }
}
```

**Campo `text` — diseño para búsqueda semántica**: El texto incluye deliberadamente sinónimos en español e inglés y términos relacionados. Así, cuando el usuario pregunte "¿tengo datos de presión tributaria?", el retriever encontrará este documento aunque el nombre oficial sea "Tax revenue as share of GDP".

**Retrieval típico**:
```
Query: "datos sobre impuestos en Chile"
→ Recupera: tax-revenue-gdp, government-revenue-dataset, tax-to-gdp-oecd
→ Contexto inyectado al LLM: "Tienes 3 datasets sobre tributación descargados.
   El principal es tax_revenue_gdp con datos de 157 países (1965-2022)."
```

---

### 3.2 `dataset_profiles` — Cómo son los datos en profundidad

**Propósito**: Que el agente conozca la calidad, cobertura, y limitaciones específicas de cada dataset SIN tener que ejecutar queries SQL exploratorias.

**Cuándo se indexa**:
- Post-descarga: se genera automáticamente un perfil ejecutando `get_dataset_statistics` + queries SQL adicionales
- Al ejecutar `analyze_data` o al construir un panel

**Schema de cada documento:**

```python
{
    "id": "profile_tax-revenue-gdp",
    "text": """
        Perfil del dataset tax_revenue_gdp:
        
        Cobertura: 157 países, 1965-2022. Sin embargo, la cobertura es 
        desigual: países OCDE tienen datos desde 1965, mientras que 
        la mayoría de África subsahariana empieza recién en 1990.
        Solo 89 países tienen datos para 2022 (el año más reciente).
        
        Valores: rango 0.4% (Bahréin) a 49.8% (Dinamarca). 
        Media global: 21.3%. Mediana: 19.7%. 
        Distribución ligeramente sesgada a la derecha.
        
        Datos faltantes: 18% de celdas nulas en el panel completo.
        Concentrados en: Somalia (sin datos), Eritrea (solo 2 años),
        Sudán del Sur (desde 2012). Patrón: MAR (Missing At Random
        condicionado a nivel de desarrollo).
        
        Outliers: Bahréin y Kuwait (< 2% - estados petroleros sin
        impuestos significativos). Son outliers genuinos, no errores.
        
        Cambios metodológicos: La ICTD revisó la serie en 2019,
        ajustando valores históricos para 23 países africanos.
        
        Entidades no-país incluidas: "World", "OECD", "High-income",
        "Low-income", "Sub-Saharan Africa" (12 agregados en total).
        
        Correlaciones conocidas: Alta correlación positiva con GDP per 
        cápita (r=0.68), WGI Government Effectiveness (r=0.71).
        Correlación moderada con Democracy Index (r=0.52).
        
        Chile específicamente: datos 1990-2022, valor 2022: 21.1%.
        Tendencia creciente desde 17.2% en 1990. Sin gaps.
    """,
    "metadata": {
        "dataset": "tax-revenue-gdp",
        "completeness": 0.82,
        "country_count": 157,
        "year_range": [1965, 2022],
        "mean": 21.3,
        "median": 19.7,
        "has_methodological_breaks": True,
        "break_years": [2019],
        "profile_generated": "2025-01-16",
        "non_country_entities": 12
    }
}
```

**Por qué un perfil por separado del catálogo**: El catálogo es ligero y se recupera frecuentemente para responder "¿qué datos tengo?". El perfil es denso y se recupera solo cuando el usuario quiere trabajar con un dataset específico. Separarlos optimiza la relevancia del retrieval.

**Retrieval típico**:
```
Query: "¿los datos de impuestos tienen buena cobertura en América Latina?"
→ Recupera: profile_tax-revenue-gdp
→ Contexto: "El dataset tiene 157 países, pero la cobertura es desigual.
   Chile tiene datos 1990-2022 sin gaps. Para LATAM en general, 
   la cobertura empieza en los 90s."
```

---

### 3.3 `tool_knowledge` — Cómo usar las herramientas

**Propósito**: Que el agente sepa cuándo y cómo usar cada tool, con ejemplos concretos, patrones de uso, y errores comunes a evitar.

**Cuándo se indexa**: 
- Carga inicial (manual, una vez)
- Actualización cuando se agregan nuevas tools

**Schema de cada documento:**

```python
{
    "id": "tool_run_sql_query",
    "text": """
        Tool: run_sql_query
        
        Función: Ejecuta consultas SQL arbitrarias contra la base SQLite local.
        
        Cuándo usarla:
        - Para explorar datos antes de análisis formal
        - Para cruces ad-hoc entre tablas
        - Para cálculos que no requieren tools especializadas
        - Para verificar resultados de otras tools
        
        Cuándo NO usarla:
        - Para búsqueda de datasets (usar search_datasets)
        - Para descargar datos nuevos (usar download_owid)
        - Para estadísticas básicas (usar get_dataset_statistics, es más rápido)
        
        Esquema típico de tablas OWID:
        Cada dataset descargado tiene una tabla con columnas:
        - Entity (TEXT): nombre del país o entidad
        - Code (TEXT): código ISO-3 del país (puede ser NULL para agregados)
        - Year (INTEGER): año de la observación
        - [nombre_indicador] (REAL): valor del indicador
        
        Errores comunes a evitar:
        1. No olvidar filtrar entidades no-país:
           WHERE Code IS NOT NULL (excluye "World", "High-income", etc.)
        2. Los nombres de tabla usan guiones bajos, no guiones:
           tax_revenue_gdp, NO tax-revenue-gdp
        3. Las columnas de valor tienen nombres largos. Usar:
           SELECT * FROM tax_revenue_gdp LIMIT 5
           para ver los nombres exactos antes de escribir queries complejas.
        4. Para JOINs entre datasets, usar Code + Year (no Entity, 
           porque los nombres pueden diferir ligeramente).
        
        Ejemplo de JOIN correcto:
        SELECT a.Entity, a.Year, a.value as aid, b.value as tax
        FROM foreign_aid a
        INNER JOIN tax_revenue_gdp b 
          ON a.Code = b.Code AND a.Year = b.Year
        WHERE a.Code IS NOT NULL
        
        Ejemplo de cálculo con LAG:
        SELECT Entity, Year, value,
               LAG(value, 1) OVER (PARTITION BY Code ORDER BY Year) as prev_year,
               (value - LAG(value, 1) OVER (PARTITION BY Code ORDER BY Year)) 
                 / LAG(value, 1) OVER (PARTITION BY Code ORDER BY Year) * 100 
                 as growth_pct
        FROM tax_revenue_gdp
        WHERE Code = 'CHL'
    """,
    "metadata": {
        "tool_name": "run_sql_query",
        "category": "query",
        "requires_local_data": True,
        "complexity": "advanced"
    }
}
```

**Se indexa un documento por tool** (15 documentos para las tools existentes + nuevos conforme se agreguen). También se indexan **documentos de patrones combinados**:

```python
{
    "id": "pattern_cross_dataset_analysis",
    "text": """
        Patrón: Análisis cruzado entre dos indicadores OWID
        
        Secuencia recomendada de tools:
        1. Verificar que ambos datasets estén descargados (list_local_datasets)
        2. Si no están, descargar (download_owid)
        3. Inspeccionar esquema de ambos (preview_data)
        4. Verificar cobertura cruzada (run_sql_query con COUNT + JOIN)
        5. Construir tabla cruzada (run_sql_query con JOIN)
        6. Analizar resultado (analyze_data o get_dataset_statistics)
        7. Exportar si necesario (export_preview_csv)
        
        Trampas comunes:
        - Olvidar que Entity incluye agregados regionales
        - No verificar la cobertura cruzada antes del JOIN
        - Asumir que los nombres de Entity coinciden entre datasets
        - No reportar cuántos países/años se perdieron en el JOIN
    """,
    "metadata": {
        "pattern_type": "workflow",
        "tools_involved": ["list_local_datasets", "download_owid", 
                           "preview_data", "run_sql_query", "analyze_data"]
    }
}
```

---

### 3.4 `methodology` — Conocimiento econométrico y de dominio

**Propósito**: Dotar al agente de criterio analítico para que no solo ejecute operaciones sino que las ejecute correctamente desde el punto de vista metodológico.

**Cuándo se indexa**: 
- Carga inicial (corpus curado manualmente)
- Expansión gradual con nuevas fichas temáticas

**Tipos de documentos:**

#### A) Fichas de variables OWID

```python
{
    "id": "method_foreign_aid",
    "text": """
        Variable: Foreign Aid (ODA - Official Development Assistance)
        
        Definición: Ayuda gubernamental diseñada para promover el 
        desarrollo económico y bienestar de países en desarrollo.
        Medida como desembolsos netos (grants + préstamos concesionales
        menos reembolsos).
        
        Fuente: OECD DAC (Development Assistance Committee).
        
        Unidades comunes en OWID:
        - USD corrientes (valor nominal)
        - USD constantes 2021 (ajustado por inflación)  
        - % del GNI del donante
        - Per cápita del receptor
        
        Consideraciones analíticas:
        - La ODA excluye ayuda militar y peacekeeping
        - Desde 2018, la OCDE usa "grant-equivalent" en vez de "cash basis"
          → series pre/post 2018 NO son directamente comparables
        - Incluye costos de refugiados in-donor (controverso, infla cifras)
        - La ayuda tiene alta volatilidad año a año → usar promedios
          móviles de 3-5 años para tendencias
        
        Relaciones esperadas con otras variables:
        - GDP per cápita: NEGATIVA (se da ayuda a países pobres)
        - State Capacity: AMBIGUA (debate académico activo)
        - Taxation: posible efecto sustitución (aid puede reducir
          incentivos para recaudar impuestos - "aid dependency")
        - Tourism: correlación indirecta vía infraestructura
        
        Trampas analíticas:
        1. Causalidad inversa: ¿la ayuda causa bajo crecimiento o se
           envía a países que ya tienen bajo crecimiento?
        2. Heterogeneidad: el efecto de la ayuda depende del tipo
           (bilateral vs multilateral, grants vs loans, sectorial)
        3. Lags: los efectos de la ayuda tardan 5-15 años en 
           materializarse → siempre usar variables rezagadas
    """,
    "metadata": {
        "variable": "foreign_aid",
        "domain": "development_economics",
        "related_datasets": ["foreign-aid-received", "foreign-aid-given-net",
                            "oda-as-share-of-gni"]
    }
}
```

#### B) Fichas metodológicas

```python
{
    "id": "method_panel_correlation",
    "text": """
        Método: Correlación en datos de panel
        
        REGLA FUNDAMENTAL: Nunca reportar solo correlación pooled.
        
        Los datos de panel (país × año) tienen dos fuentes de variación:
        
        1. BETWEEN (entre países): ¿los países con más X tienen más Y?
           Cálculo: correlación entre promedios por país.
           Ejemplo: r_between(Aid, Growth) = -0.4
           Interpretación: los países que reciben más ayuda crecen menos.
           PERO: esto refleja selección, no causalidad.
        
        2. WITHIN (dentro del país): ¿cuando X sube en un país, Y sube?
           Cálculo: correlación entre desviaciones del promedio del país.
           Ejemplo: r_within(Aid, Growth) = +0.1
           Interpretación: cuando un país recibe más ayuda que su promedio,
           su crecimiento es ligeramente mayor.
           Más cercano a causalidad (controla por todo lo fijo del país).
        
        3. POOLED (mezcla ambas): r_pooled puede tener cualquier signo
           dependiendo de cuál efecto domina.
        
        SQL para calcular within-correlation:
        WITH country_means AS (
            SELECT Code, AVG(x) as mean_x, AVG(y) as mean_y
            FROM panel GROUP BY Code
        ),
        demeaned AS (
            SELECT p.Code, p.Year,
                   p.x - cm.mean_x as x_within,
                   p.y - cm.mean_y as y_within
            FROM panel p JOIN country_means cm ON p.Code = cm.Code
        )
        SELECT 
            (SUM(x_within * y_within)) / 
            (SQRT(SUM(x_within * x_within)) * SQRT(SUM(y_within * y_within)))
            as within_correlation
        FROM demeaned;
        
        Recomendación para el agente:
        - Siempre calcular las tres (pooled, between, within)
        - Si between y within tienen signos opuestos → ADVERTIR al usuario
        - Considerar lags en la correlación (la causa precede al efecto)
    """,
    "metadata": {
        "method_type": "correlation",
        "data_type": "panel",
        "complexity": "intermediate",
        "prerequisite": "panel_data_merged"
    }
}
```

#### C) Fichas de advertencias contextuales (alimentan el futuro caveat_engine)

```python
{
    "id": "caveat_covid_2020",
    "text": """
        Advertencia: Efecto COVID-19 en datos 2020-2021
        
        Aplicable a: Tourism, Government Spending, GDP, Trade, 
        Foreign Aid, prácticamente cualquier indicador económico.
        
        El año 2020 representa un shock exógeno masivo que distorsiona
        tendencias de largo plazo. El turismo internacional cayó un 73%.
        El gasto público se disparó por estímulos fiscales.
        
        Recomendación: Si el periodo de análisis incluye 2020-2021:
        1. Ejecutar el análisis completo incluyendo 2020
        2. Repetir excluyendo 2020-2021
        3. Si los resultados cambian sustancialmente, reportar ambos
        4. Para tendencias de largo plazo, preferir terminar en 2019
        
        Trigger automático: si el rango de años del panel incluye 
        2020 o 2021, inyectar esta advertencia en el contexto.
    """,
    "metadata": {
        "caveat_type": "temporal_shock",
        "trigger_years": [2020, 2021],
        "severity": "high",
        "affected_topics": ["tourism", "government_spending", "gdp", 
                           "trade", "foreign_aid"]
    }
}
```

---

### 3.5 `conversation_memory` — Qué se hizo y qué se dijo

**Propósito**: Memoria conversacional persistente que sobrevive al truncamiento del context window del LLM.

**Cuándo se indexa**: 
- Al final de cada turno conversacional (automático)
- Al finalizar una sesión (resumen)

**Dos niveles de granularidad:**

#### A) Turnos individuales (corto plazo)

```python
{
    "id": "turn_2025-01-20_14:32:07_003",
    "text": """
        Sesión: 2025-01-20
        Turno: 3
        Usuario pidió: Construir panel cruzando Foreign Aid con 
        State Capacity para América Latina, periodo 2000-2020.
        
        Acciones ejecutadas:
        - download_owid("foreign-aid-received") → OK, 189 países
        - download_owid("wgi-government-effectiveness") → OK, 214 países  
        - run_sql_query(JOIN por Code + Year, filtrado LATAM) → 
          Panel resultante: 18 países, 21 años, 87% completo
        
        Resultado clave: Panel guardado como tabla "panel_aid_statecap_latam".
        Países incluidos: ARG, BOL, BRA, CHL, COL, CRI, CUB, DOM, ECU,
        GTM, HND, MEX, NIC, PAN, PER, PRY, URY, VEN.
        Países excluidos por datos insuficientes: HTI, SLV (< 5 años de datos).
        
        El usuario quedó satisfecho y pidió continuar con correlaciones.
    """,
    "metadata": {
        "session_id": "2025-01-20",
        "turn_number": 3,
        "timestamp": "2025-01-20T14:32:07",
        "tools_used": ["download_owid", "run_sql_query"],
        "datasets_involved": ["foreign-aid-received", "wgi-government-effectiveness"],
        "artifacts_created": ["panel_aid_statecap_latam"],
        "topic": "foreign_aid_state_capacity_latam"
    }
}
```

#### B) Resúmenes de sesión (largo plazo)

```python
{
    "id": "session_summary_2025-01-20",
    "text": """
        Resumen de sesión: 2025-01-20 (12 turnos, 45 minutos)
        
        Objetivo del usuario: Analizar la relación entre ayuda exterior
        y capacidad estatal en América Latina.
        
        Datasets descargados: foreign-aid-received, wgi-government-effectiveness,
        gdp-per-capita-worldbank.
        
        Artefactos creados:
        - Tabla SQL: panel_aid_statecap_latam (18 países, 2000-2020)
        - CSV exportado: panel_aid_statecap_latam_2025-01-20.csv
        
        Hallazgos principales:
        - Correlación pooled Aid-StateCapacity: -0.34 (significativa)
        - Correlación within: +0.06 (no significativa)
        - El usuario concluyó que la relación negativa refleja selección,
          no causalidad.
        
        Pendientes mencionados por el usuario:
        - Quiere repetir el análisis con lag de 5 años
        - Quiere incluir Taxation como variable de control
        - Mencionó interés en comparar LATAM vs África
    """,
    "metadata": {
        "session_id": "2025-01-20",
        "duration_minutes": 45,
        "turns": 12,
        "main_topic": "foreign_aid_state_capacity_latam",
        "pending_tasks": ["lag_analysis", "add_taxation_control", "compare_africa"]
    }
}
```

**Retrieval típico**:
```
Query del usuario: "Retomemos el análisis de ayuda exterior"
→ Recupera: session_summary_2025-01-20
→ Contexto inyectado: "En tu última sesión sobre este tema (20 enero),
   construiste un panel de 18 países LATAM (2000-2020). Encontraste que
   la correlación negativa refleja selección. Quedó pendiente: análisis
   con lag de 5 años y agregar Taxation como control."
```

---

### 3.6 `analysis_results` — Qué se encontró

**Propósito**: Almacenar resultados analíticos para reutilización. Evita recalcular lo mismo y permite construir sobre hallazgos previos.

**Cuándo se indexa**: 
- Cuando se ejecuta un análisis (correlación, regresión, estadísticas)
- Cuando se construye un panel

```python
{
    "id": "result_corr_aid_statecap_latam_2025-01-20",
    "text": """
        Resultado: Correlación Foreign Aid vs State Capacity
        Región: América Latina
        Periodo: 2000-2020
        Fecha del análisis: 2025-01-20
        
        Panel utilizado: panel_aid_statecap_latam
        N observaciones: 342 (18 países × ~19 años promedio)
        
        Resultados:
        - Pearson pooled: r = -0.34, p < 0.001
        - Spearman pooled: r = -0.31, p < 0.001  
        - Between (promedios país): r = -0.52, p = 0.03
        - Within (demeaned): r = +0.06, p = 0.28
        
        Interpretación: Relación negativa entre países pero no dentro
        de países. Sugiere selección (la ayuda va a países con baja
        capacidad), no efecto causal de la ayuda sobre la capacidad.
        
        Limitaciones: No incluye lags temporales. No controla por GDP.
        Haití y El Salvador excluidos por datos insuficientes.
    """,
    "metadata": {
        "analysis_type": "correlation",
        "variables": ["foreign_aid", "state_capacity"],
        "region": "latam",
        "period": [2000, 2020],
        "panel_table": "panel_aid_statecap_latam",
        "date": "2025-01-20",
        "is_current": True
    }
}
```

---

## 4. MOTOR DE EMBEDDINGS Y VECTOR STORE

### 4.1 Elección tecnológica

| Componente | Elección | Justificación |
|-----------|----------|---------------|
| **Vector Store** | **ChromaDB** | Embeddable en Python, sin servidor externo, persiste en disco, compatible con SQLite como storage backend. Ideal para un sistema Flask + SQLite |
| **Embedding Model** | **sentence-transformers/all-MiniLM-L6-v2** | Ligero (80MB), rápido, calidad suficiente para retrieval semántico en dominios técnicos. Gratis, corre localmente |
| **Alternativa embedding** | **OpenAI text-embedding-3-small** | Si se prefiere calidad sobre costo. Requiere API key pero produce mejores embeddings para vocabulario económico bilingüe |
| **Chunking** | Por documento completo (no chunks) | Cada documento RAG es autocontenido y diseñado para caber en un chunk (< 500 tokens). No necesitamos chunking de documentos largos |

### 4.2 Estructura de archivos

```
project/
├── app.py                      # Flask principal
├── rag/
│   ├── __init__.py
│   ├── engine.py               # RAGEngine: clase principal
│   ├── indexer.py              # Lógica de indexación por colección
│   ├── retriever.py            # Lógica de recuperación y ranking
│   ├── prompt_builder.py       # Construye el prompt enriquecido
│   ├── memory.py               # Gestión de conversation_memory
│   └── profiler.py             # Genera perfiles de datasets automáticamente
├── rag_data/
│   ├── chroma_db/              # Persistencia de ChromaDB
│   ├── seed/                   # Documentos iniciales (methodology, tool_knowledge)
│   │   ├── tools/              # Un .json por tool
│   │   ├── methods/            # Fichas metodológicas
│   │   ├── variables/          # Fichas de variables OWID
│   │   └── caveats/            # Advertencias contextuales
│   └── generated/              # Perfiles auto-generados
├── tools/                      # MCP tools existentes
├── data/                       # SQLite + CSVs
└── templates/                  # Flask templates
```

---

## 5. IMPLEMENTACIÓN DETALLADA

### 5.1 RAGEngine — Clase principal

```python
# rag/engine.py

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import json
import os

class RAGEngine:
    """Motor RAG central del agente OWID."""
    
    COLLECTIONS = [
        "dataset_catalog",
        "dataset_profiles", 
        "tool_knowledge",
        "methodology",
        "conversation_memory",
        "analysis_results"
    ]
    
    def __init__(self, persist_dir: str = "rag_data/chroma_db"):
        # Inicializar ChromaDB con persistencia en disco
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Modelo de embeddings local
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Crear o recuperar colecciones
        self.collections = {}
        for name in self.COLLECTIONS:
            self.collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def index(self, collection_name: str, documents: List[Dict]):
        """
        Indexa documentos en una colección.
        
        Args:
            collection_name: Nombre de la colección target
            documents: Lista de dicts con keys: id, text, metadata
        """
        collection = self.collections[collection_name]
        
        ids = [doc["id"] for doc in documents]
        texts = [doc["text"] for doc in documents]
        metadatas = [doc.get("metadata", {}) for doc in documents]
        
        # Generar embeddings
        embeddings = self.embedder.encode(texts).tolist()
        
        # Upsert (actualiza si existe, inserta si no)
        collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )
    
    def retrieve(
        self, 
        query: str, 
        collections: Optional[List[str]] = None,
        n_results: int = 5,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recupera documentos relevantes de una o más colecciones.
        
        Args:
            query: Texto de búsqueda
            collections: Colecciones donde buscar (None = todas)
            n_results: Número de resultados por colección
            metadata_filter: Filtro de metadatos ChromaDB
            
        Returns:
            Lista de resultados ordenados por relevancia
        """
        if collections is None:
            collections = self.COLLECTIONS
        
        query_embedding = self.embedder.encode(query).tolist()
        
        all_results = []
        
        for col_name in collections:
            collection = self.collections[col_name]
            
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, collection.count()),
                    where=metadata_filter,
                    include=["documents", "metadatas", "distances"]
                )
                
                # Aplanar resultados
                for i in range(len(results["ids"][0])):
                    all_results.append({
                        "collection": col_name,
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "relevance": 1 - results["distances"][0][i]
                    })
            except Exception:
                continue  # Colección vacía
        
        # Ordenar por relevancia global
        all_results.sort(key=lambda x: x["relevance"], reverse=True)
        
        return all_results[:n_results * 2]  # Top resultados globales
    
    def retrieve_for_context(
        self, 
        user_message: str,
        session_id: str = None
    ) -> str:
        """
        Método principal: dado un mensaje del usuario, recupera 
        todo el contexto relevante y lo formatea para inyectar en el prompt.
        
        Returns:
            String formateado listo para insertar en el system prompt
        """
        context_parts = []
        
        # 1. Buscar en catálogo y perfiles de datasets
        data_results = self.retrieve(
            query=user_message,
            collections=["dataset_catalog", "dataset_profiles"],
            n_results=3
        )
        if data_results:
            context_parts.append("=== DATOS DISPONIBLES ===")
            for r in data_results:
                if r["relevance"] > 0.3:  # Umbral de relevancia
                    context_parts.append(r["text"])
        
        # 2. Buscar conocimiento de tools
        tool_results = self.retrieve(
            query=user_message,
            collections=["tool_knowledge"],
            n_results=2
        )
        if tool_results:
            context_parts.append("=== GUÍA DE HERRAMIENTAS ===")
            for r in tool_results:
                if r["relevance"] > 0.25:
                    context_parts.append(r["text"])
        
        # 3. Buscar metodología relevante
        method_results = self.retrieve(
            query=user_message,
            collections=["methodology"],
            n_results=2
        )
        if method_results:
            context_parts.append("=== CONTEXTO METODOLÓGICO ===")
            for r in method_results:
                if r["relevance"] > 0.3:
                    context_parts.append(r["text"])
        
        # 4. Buscar memoria conversacional
        memory_results = self.retrieve(
            query=user_message,
            collections=["conversation_memory"],
            n_results=3
        )
        if memory_results:
            context_parts.append("=== MEMORIA DE SESIONES PREVIAS ===")
            for r in memory_results:
                if r["relevance"] > 0.35:
                    context_parts.append(r["text"])
        
        # 5. Buscar resultados analíticos previos
        analysis_results = self.retrieve(
            query=user_message,
            collections=["analysis_results"],
            n_results=2
        )
        if analysis_results:
            context_parts.append("=== ANÁLISIS PREVIOS RELEVANTES ===")
            for r in analysis_results:
                if r["relevance"] > 0.35:
                    context_parts.append(r["text"])
        
        return "\n\n".join(context_parts)
    
    def seed_from_directory(self, seed_dir: str = "rag_data/seed"):
        """Carga inicial de documentos desde archivos JSON."""
        mapping = {
            "tools": "tool_knowledge",
            "methods": "methodology",
            "variables": "methodology",
            "caveats": "methodology"
        }
        
        for subdir, collection_name in mapping.items():
            path = os.path.join(seed_dir, subdir)
            if not os.path.exists(path):
                continue
            
            documents = []
            for filename in os.listdir(path):
                if filename.endswith(".json"):
                    with open(os.path.join(path, filename)) as f:
                        doc = json.load(f)
                        documents.append(doc)
            
            if documents:
                self.index(collection_name, documents)
                print(f"  Indexed {len(documents)} docs in {collection_name}")
```

---

### 5.2 Indexador automático post-descarga

```python
# rag/indexer.py

import sqlite3
from datetime import datetime
from typing import Dict

class DatasetIndexer:
    """Genera e indexa documentos RAG automáticamente cuando se descargan datos."""
    
    def __init__(self, rag_engine, db_path: str = "data/owid.db"):
        self.rag = rag_engine
        self.db_path = db_path
    
    def index_downloaded_dataset(
        self, 
        slug: str,              # ej: "tax-revenue-gdp"
        table_name: str,        # ej: "tax_revenue_gdp"  
        owid_metadata: Dict     # metadatos de get_metadata
    ):
        """
        Se llama automáticamente después de download_owid.
        Genera dos documentos: catálogo + perfil.
        """
        # 1. Generar documento de catálogo
        catalog_doc = self._build_catalog_doc(slug, table_name, owid_metadata)
        self.rag.index("dataset_catalog", [catalog_doc])
        
        # 2. Generar perfil ejecutando queries SQL
        profile_doc = self._build_profile_doc(slug, table_name, owid_metadata)
        self.rag.index("dataset_profiles", [profile_doc])
    
    def _build_catalog_doc(self, slug, table_name, meta) -> Dict:
        """Construye documento de catálogo."""
        
        description = meta.get("description", "")
        source = meta.get("source", "")
        topic = meta.get("topic", "")
        
        text = f"""
            Dataset: {meta.get('name', slug)}.
            Slug: {slug}.
            Tema: {topic}.
            Fuente original: {source}.
            Descripción: {description}.
            Disponible localmente: sí.
            Tabla SQL: {table_name}.
            Última descarga: {datetime.now().strftime('%Y-%m-%d')}.
        """
        
        return {
            "id": f"dataset_{slug}",
            "text": text,
            "metadata": {
                "slug": slug,
                "topic": topic,
                "source": source,
                "is_local": True,
                "sql_table": table_name,
                "last_downloaded": datetime.now().isoformat()
            }
        }
    
    def _build_profile_doc(self, slug, table_name, meta) -> Dict:
        """Construye perfil detallado ejecutando queries de diagnóstico."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtener columnas
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        value_col = [c for c in columns if c not in ('Entity', 'Code', 'Year')][0]
        
        # Estadísticas básicas
        stats = {}
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT Entity) as entities,
                COUNT(DISTINCT CASE WHEN Code IS NOT NULL THEN Code END) as countries,
                MIN(Year) as year_min,
                MAX(Year) as year_max,
                AVG(CAST("{value_col}" AS REAL)) as mean_val,
                MIN(CAST("{value_col}" AS REAL)) as min_val,
                MAX(CAST("{value_col}" AS REAL)) as max_val,
                COUNT(CASE WHEN "{value_col}" IS NULL THEN 1 END) as nulls
            FROM {table_name}
        """)
        row = cursor.fetchone()
        stats = dict(zip(
            ['total_rows', 'entities', 'countries', 'year_min', 'year_max',
             'mean', 'min', 'max', 'nulls'],
            row
        ))
        
        # Entidades no-país
        cursor.execute(f"""
            SELECT DISTINCT Entity FROM {table_name} 
            WHERE Code IS NULL
            ORDER BY Entity
        """)
        non_countries = [r[0] for r in cursor.fetchall()]
        
        # Países con mejor cobertura (top 5)
        cursor.execute(f"""
            SELECT Entity, COUNT(*) as years 
            FROM {table_name}
            WHERE Code IS NOT NULL AND "{value_col}" IS NOT NULL
            GROUP BY Entity
            ORDER BY years DESC
            LIMIT 5
        """)
        best_coverage = cursor.fetchall()
        
        # Países con peor cobertura (bottom 5)
        cursor.execute(f"""
            SELECT Entity, COUNT(*) as years 
            FROM {table_name}
            WHERE Code IS NOT NULL AND "{value_col}" IS NOT NULL
            GROUP BY Entity
            ORDER BY years ASC
            LIMIT 5
        """)
        worst_coverage = cursor.fetchall()
        
        # Completitud por década
        cursor.execute(f"""
            SELECT 
                (Year / 10) * 10 as decade,
                COUNT(DISTINCT CASE WHEN Code IS NOT NULL THEN Code END) as countries
            FROM {table_name}
            WHERE "{value_col}" IS NOT NULL
            GROUP BY decade
            ORDER BY decade
        """)
        decade_coverage = cursor.fetchall()
        
        conn.close()
        
        # Construir texto del perfil
        completeness = 1 - (stats['nulls'] / max(stats['total_rows'], 1))
        
        text = f"""
            Perfil del dataset {table_name}:
            
            Cobertura: {stats['countries']} países, {stats['year_min']}-{stats['year_max']}.
            Total de filas: {stats['total_rows']}. 
            Columna de valor: "{value_col}".
            
            Valores: rango {stats['min']:.2f} a {stats['max']:.2f}.
            Media: {stats['mean']:.2f}. 
            Completitud: {completeness:.1%}.
            Valores nulos: {stats['nulls']}.
            
            Cobertura por década: {'; '.join(f"{d[0]}s: {d[1]} países" for d in decade_coverage)}.
            
            Mejor cobertura: {', '.join(f"{c[0]} ({c[1]} años)" for c in best_coverage)}.
            Peor cobertura: {', '.join(f"{c[0]} ({c[1]} años)" for c in worst_coverage)}.
            
            Entidades no-país incluidas ({len(non_countries)}): {', '.join(non_countries[:10])}.
            Estas deben filtrarse con WHERE Code IS NOT NULL para análisis por país.
        """
        
        return {
            "id": f"profile_{slug}",
            "text": text,
            "metadata": {
                "dataset": slug,
                "sql_table": table_name,
                "completeness": round(completeness, 3),
                "country_count": stats['countries'],
                "year_range": [stats['year_min'], stats['year_max']],
                "mean": round(stats['mean'], 3),
                "non_country_count": len(non_countries),
                "profile_generated": datetime.now().isoformat()
            }
        }
```

---

### 5.3 Memoria conversacional

```python
# rag/memory.py

from datetime import datetime
from typing import Dict, List, Optional

class ConversationMemory:
    """Gestiona la indexación de memoria conversacional en RAG."""
    
    def __init__(self, rag_engine):
        self.rag = rag_engine
        self.current_session = {
            "id": datetime.now().strftime("%Y-%m-%d_%H%M"),
            "turns": [],
            "tools_used": set(),
            "datasets_involved": set(),
            "artifacts_created": [],
            "start_time": datetime.now()
        }
        self.turn_count = 0
    
    def record_turn(
        self,
        user_message: str,
        assistant_response: str,
        tools_called: List[Dict] = None,
        results: Dict = None
    ):
        """Registra un turno conversacional."""
        self.turn_count += 1
        
        turn = {
            "turn_number": self.turn_count,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message[:500],  # Truncar mensajes largos
            "assistant_summary": self._summarize_response(assistant_response),
            "tools_called": tools_called or [],
            "key_results": results
        }
        
        self.current_session["turns"].append(turn)
        
        # Actualizar metadatos de sesión
        if tools_called:
            for tc in tools_called:
                self.current_session["tools_used"].add(tc.get("name", ""))
                if tc.get("name") == "download_owid":
                    ds = tc.get("args", {}).get("dataset", "")
                    self.current_session["datasets_involved"].add(ds)
        
        # Indexar turno individual si es sustancial
        if tools_called or (results and results.get("significant")):
            self._index_turn(turn)
    
    def _index_turn(self, turn: Dict):
        """Indexa un turno individual en RAG."""
        tools_desc = ""
        if turn["tools_called"]:
            tools_desc = "Tools usadas: " + ", ".join(
                t.get("name", "") for t in turn["tools_called"]
            )
        
        text = f"""
            Sesión: {self.current_session['id']}
            Turno: {turn['turn_number']}
            Usuario pidió: {turn['user_message']}
            {tools_desc}
            Resultado: {turn['assistant_summary']}
        """
        
        doc = {
            "id": f"turn_{self.current_session['id']}_{turn['turn_number']:03d}",
            "text": text,
            "metadata": {
                "session_id": self.current_session["id"],
                "turn_number": turn["turn_number"],
                "timestamp": turn["timestamp"],
                "tools_used": [t.get("name") for t in turn["tools_called"]]
            }
        }
        
        self.rag.index("conversation_memory", [doc])
    
    def end_session(self):
        """Genera resumen de sesión e indexa."""
        session = self.current_session
        duration = (datetime.now() - session["start_time"]).total_seconds() / 60
        
        # Construir resumen
        turns_summary = "\n".join(
            f"  T{t['turn_number']}: {t['user_message'][:100]}"
            for t in session["turns"]
        )
        
        text = f"""
            Resumen de sesión: {session['id']}
            Duración: {duration:.0f} minutos, {self.turn_count} turnos.
            
            Flujo de la conversación:
            {turns_summary}
            
            Datasets involucrados: {', '.join(session['datasets_involved'])}.
            Tools utilizadas: {', '.join(session['tools_used'])}.
            Artefactos creados: {', '.join(session['artifacts_created']) or 'Ninguno'}.
        """
        
        doc = {
            "id": f"session_{session['id']}",
            "text": text,
            "metadata": {
                "session_id": session["id"],
                "turns": self.turn_count,
                "duration_minutes": round(duration),
                "datasets": list(session["datasets_involved"]),
                "tools": list(session["tools_used"])
            }
        }
        
        self.rag.index("conversation_memory", [doc])
    
    def _summarize_response(self, response: str) -> str:
        """Extrae resumen breve de la respuesta del asistente."""
        # Truncar a primeras 200 chars como fallback
        # En producción, usar el LLM para resumir
        return response[:300].replace("\n", " ")
```

---

### 5.4 Prompt Builder — Integración con Copilot

```python
# rag/prompt_builder.py

class PromptBuilder:
    """Construye el prompt enriquecido con contexto RAG para enviar al LLM."""
    
    # Presupuesto de tokens para contexto RAG
    # (ajustar según límite del modelo Copilot)
    MAX_CONTEXT_TOKENS = 3000
    
    SYSTEM_PREFIX = """Eres un analista de datos macroeconómicos especializado 
en datos de Our World in Data (OWID). Tienes acceso a herramientas (tools) 
para buscar, descargar, consultar y analizar datos de panel (país × año).

A continuación se te proporciona contexto recuperado automáticamente 
que es relevante para la consulta actual del usuario. Usa este contexto 
para dar respuestas más precisas, elegir las tools correctas, y advertir 
sobre limitaciones de los datos.

REGLAS DE USO DEL CONTEXTO:
- Si el contexto menciona datasets disponibles localmente, no necesitas 
  descargarlos de nuevo
- Si el contexto incluye advertencias metodológicas, inclúyelas en tu respuesta
- Si el contexto muestra resultados de análisis previos, referencialos 
  en lugar de recalcular
- Si el contexto muestra conversaciones previas con tareas pendientes, 
  menciónalo al usuario
"""

    def __init__(self, rag_engine):
        self.rag = rag_engine
    
    def build_prompt(
        self, 
        user_message: str,
        conversation_history: list = None,
        session_id: str = None
    ) -> dict:
        """
        Construye el payload completo para enviar al LLM.
        
        Returns:
            dict con 'system' y 'messages' listos para la API
        """
        # 1. Recuperar contexto relevante del RAG
        rag_context = self.rag.retrieve_for_context(
            user_message=user_message,
            session_id=session_id
        )
        
        # 2. Truncar si excede presupuesto
        rag_context = self._truncate_to_budget(rag_context)
        
        # 3. Construir system prompt
        system_prompt = self.SYSTEM_PREFIX
        if rag_context:
            system_prompt += f"\n\n--- CONTEXTO RECUPERADO ---\n{rag_context}\n--- FIN CONTEXTO ---"
        
        # 4. Construir mensajes
        messages = []
        if conversation_history:
            # Incluir últimos N turnos del historial directo
            for msg in conversation_history[-10:]:
                messages.append(msg)
        
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return {
            "system": system_prompt,
            "messages": messages
        }
    
    def _truncate_to_budget(self, text: str) -> str:
        """Trunca el contexto RAG para respetar el presupuesto de tokens."""
        # Estimación gruesa: 1 token ≈ 4 chars
        max_chars = self.MAX_CONTEXT_TOKENS * 4
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[... contexto truncado por límite ...]"
        return text
```

---

### 5.5 Integración en Flask

```python
# app.py (fragmento de integración)

from flask import Flask, request, jsonify
from rag.engine import RAGEngine
from rag.indexer import DatasetIndexer
from rag.memory import ConversationMemory
from rag.prompt_builder import PromptBuilder

app = Flask(__name__)

# Inicializar RAG
rag = RAGEngine(persist_dir="rag_data/chroma_db")
rag.seed_from_directory("rag_data/seed")  # Carga inicial

indexer = DatasetIndexer(rag)
prompt_builder = PromptBuilder(rag)

# Sesiones activas
sessions = {}

def get_or_create_session(session_id: str) -> ConversationMemory:
    if session_id not in sessions:
        sessions[session_id] = ConversationMemory(rag)
    return sessions[session_id]


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data["message"]
    session_id = data.get("session_id", "default")
    conversation_history = data.get("history", [])
    
    memory = get_or_create_session(session_id)
    
    # 1. Construir prompt enriquecido con RAG
    prompt_payload = prompt_builder.build_prompt(
        user_message=user_message,
        conversation_history=conversation_history,
        session_id=session_id
    )
    
    # 2. Enviar a Copilot LLM (con tools disponibles)
    response = copilot_client.chat(
        system=prompt_payload["system"],
        messages=prompt_payload["messages"],
        tools=registered_tools  # Las 15 MCP tools
    )
    
    # 3. Si el LLM invocó tools, ejecutarlas
    tools_called = []
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            tools_called.append({
                "name": tool_call.name,
                "args": tool_call.arguments,
                "result_summary": str(result)[:200]
            })
            
            # 3a. Si se descargó un dataset, indexarlo en RAG
            if tool_call.name == "download_owid":
                indexer.index_downloaded_dataset(
                    slug=tool_call.arguments["dataset"],
                    table_name=tool_call.arguments["dataset"].replace("-", "_"),
                    owid_metadata=get_metadata(tool_call.arguments["dataset"])
                )
    
    # 4. Registrar turno en memoria
    memory.record_turn(
        user_message=user_message,
        assistant_response=response.content,
        tools_called=tools_called
    )
    
    # 5. Retornar respuesta
    return jsonify({
        "response": response.content,
        "tools_used": [t["name"] for t in tools_called],
        "rag_context_used": bool(prompt_payload["system"] != PromptBuilder.SYSTEM_PREFIX)
    })


@app.route("/session/end", methods=["POST"])
def end_session():
    session_id = request.json.get("session_id", "default")
    if session_id in sessions:
        sessions[session_id].end_session()
        del sessions[session_id]
    return jsonify({"status": "session_ended"})
```

---

## 6. ESTRATEGIA DE RETRIEVAL INTELIGENTE

### 6.1 Retrieval selectivo por tipo de query

No todas las queries necesitan buscar en todas las colecciones. El retriever clasifica la intención y busca solo donde es relevante:

```python
# rag/retriever.py

class SmartRetriever:
    """Retrieval selectivo basado en clasificación de intención."""
    
    INTENT_COLLECTION_MAP = {
        "data_question": ["dataset_catalog", "dataset_profiles"],
        "how_to":        ["tool_knowledge"],
        "analysis":      ["methodology", "analysis_results", "dataset_profiles"],
        "continuation":  ["conversation_memory", "analysis_results"],
        "general":       ["dataset_catalog", "tool_knowledge", "methodology"]
    }
    
    # Palabras clave simples para clasificación rápida
    INTENT_SIGNALS = {
        "data_question": [
            "qué datos", "tengo datos", "hay datos", "dataset",
            "descargado", "disponible", "qué información"
        ],
        "how_to": [
            "cómo", "cómo se usa", "cómo puedo", "ayuda con",
            "ejemplo de", "tutorial", "qué tool"
        ],
        "analysis": [
            "correlación", "correlaciona", "regresión", "analiza",
            "compara", "relación entre", "efecto de", "impacto",
            "tendencia", "crece", "evolución"
        ],
        "continuation": [
            "continuemos", "retomemos", "la vez pasada",
            "el análisis anterior", "lo que hicimos",
            "quedó pendiente", "seguimos con"
        ]
    }
    
    def classify_intent(self, query: str) -> str:
        """Clasifica la intención de la query del usuario."""
        query_lower = query.lower()
        
        scores = {}
        for intent, signals in self.INTENT_SIGNALS.items():
            scores[intent] = sum(
                1 for signal in signals if signal in query_lower
            )
        
        if max(scores.values()) == 0:
            return "general"
        
        return max(scores, key=scores.get)
    
    def get_target_collections(self, query: str) -> list:
        """Determina en qué colecciones buscar."""
        intent = self.classify_intent(query)
        return self.INTENT_COLLECTION_MAP[intent]
```

### 6.2 Re-ranking por relevancia temporal

Documentos más recientes de `conversation_memory` deben priorizarse:

```python
def rerank_with_recency(results: list, recency_weight: float = 0.3) -> list:
    """Re-rankea resultados combinando relevancia semántica + recencia."""
    from datetime import datetime
    
    now = datetime.now()
    
    for r in results:
        base_score = r["relevance"]
        
        # Bonus por recencia (solo para memory y results)
        if r["collection"] in ("conversation_memory", "analysis_results"):
            timestamp = r["metadata"].get("timestamp", "")
            if timestamp:
                age_days = (now - datetime.fromisoformat(timestamp)).days
                recency_score = max(0, 1 - (age_days / 90))  # Decay en 90 días
                r["final_score"] = (1 - recency_weight) * base_score + recency_weight * recency_score
            else:
                r["final_score"] = base_score
        else:
            r["final_score"] = base_score
    
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results
```

---

## 7. DATOS SEED: Contenido Inicial del RAG

### 7.1 Estructura de archivos seed

```
rag_data/seed/
├── tools/
│   ├── search_datasets.json
│   ├── semantic_search_datasets.json
│   ├── download_owid.json
│   ├── run_sql_query.json         # Incluye patrones SQL para OWID
│   ├── get_metadata.json
│   ├── analyze_data.json
│   ├── preview_data.json
│   ├── fork_dataset.json
│   ├── get_dataset_statistics.json
│   ├── recommend_datasets.json
│   ├── list_local_datasets.json
│   ├── list_datasets_with_filters.json
│   ├── get_dataset_versions.json
│   ├── export_preview_csv.json
│   └── list_available_tools.json
├── variables/
│   ├── foreign_aid.json           # Ficha de Foreign Aid
│   ├── government_spending.json   # Ficha de Government Spending
│   ├── state_capacity.json        # Ficha de State Capacity
│   ├── taxation.json              # Ficha de Taxation
│   └── tourism.json               # Ficha de Tourism
├── methods/
│   ├── panel_correlation.json     # Correlación en panel (within/between)
│   ├── time_lags.json             # Uso de variables rezagadas
│   ├── fixed_effects.json         # Regresión con efectos fijos
│   ├── data_panel_basics.json     # Fundamentos de datos de panel
│   ├── normalization.json         # Per cápita, log, deflación
│   └── missing_data.json          # Tratamiento de datos faltantes
├── caveats/
│   ├── covid_2020.json            # Efecto COVID en datos
│   ├── oda_methodology_2018.json  # Cambio ODA 2018
│   ├── small_states_bias.json     # Micro-estados distorsionan promedios
│   ├── reverse_causality.json     # Causalidad inversa en aid-growth
│   └── survivorship_bias.json     # Sesgo de supervivencia en paneles
└── workflows/
    ├── cross_dataset_analysis.json   # Patrón de cruce de datasets
    ├── first_exploration.json        # Patrón de exploración inicial
    └── build_analytical_panel.json   # Patrón de construcción de panel
```

### 7.2 Volumen estimado de documentos seed

| Colección | Documentos seed | Generados auto | Total estimado |
|-----------|-----------------|----------------|----------------|
| `dataset_catalog` | 0 (se generan al descargar) | ~50-200 | 50-200 |
| `dataset_profiles` | 0 (se generan al descargar) | ~50-200 | 50-200 |
| `tool_knowledge` | 15 (tools) + 3 (workflows) | 0 | 18 |
| `methodology` | 5 (variables) + 6 (métodos) + 5 (caveats) | Expandible | 16+ |
| `conversation_memory` | 0 (crece con uso) | Ilimitado | Crece |
| `analysis_results` | 0 (crece con uso) | Ilimitado | Crece |

---

## 8. MANTENIMIENTO Y CICLO DE VIDA

### 8.1 Auto-limpieza de memoria

```python
def cleanup_old_memory(rag: RAGEngine, max_age_days: int = 180):
    """Elimina turnos individuales antiguos, preservando resúmenes de sesión."""
    collection = rag.collections["conversation_memory"]
    
    cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
    
    # Obtener IDs de turnos antiguos (no resúmenes)
    results = collection.get(
        where={
            "$and": [
                {"timestamp": {"$lt": cutoff}},
                {"session_id": {"$exists": True}}
            ]
        }
    )
    
    # Eliminar turnos individuales, mantener resúmenes
    turn_ids = [id for id in results["ids"] if id.startswith("turn_")]
    if turn_ids:
        collection.delete(ids=turn_ids)
```

### 8.2 Re-indexación de perfiles

```python
def refresh_profiles(rag: RAGEngine, db_path: str):
    """Re-genera perfiles de datasets que pueden haber cambiado."""
    indexer = DatasetIndexer(rag, db_path)
    
    # Obtener datasets locales
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    tables = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    for table in tables:
        slug = table.replace("_", "-")
        indexer.index_downloaded_dataset(slug, table, {})
```

---

## 9. MÉTRICAS Y EVALUACIÓN

### 9.1 Métricas de calidad del RAG

| Métrica | Cómo medir | Target |
|---------|-----------|--------|
| **Retrieval Precision** | % de documentos recuperados que son relevantes para la query | > 70% |
| **Retrieval Recall** | % de documentos relevantes que fueron recuperados | > 60% |
| **Context Utilization** | % de respuestas del LLM que referencian el contexto RAG | > 50% |
| **Tool Selection Accuracy** | ¿El LLM eligió la tool correcta con contexto RAG vs sin él? | Mejora > 20% |
| **Redundant Tool Calls** | ¿Cuántas veces llama a list_local_datasets cuando ya sabe la respuesta? | Reducción > 50% |
| **Conversation Continuity** | ¿El agente recuerda contexto de sesiones previas? | > 80% de los casos |

### 9.2 Logging para evaluación

```python
# Agregar a cada request
rag_log = {
    "query": user_message,
    "intent_classified": retriever.classify_intent(user_message),
    "collections_searched": target_collections,
    "documents_retrieved": len(results),
    "top_relevance_score": results[0]["relevance"] if results else 0,
    "context_tokens_used": len(rag_context) // 4,
    "tools_called_by_llm": [t["name"] for t in tools_called],
    "timestamp": datetime.now().isoformat()
}
```

---

## 10. RESUMEN DE IMPLEMENTACIÓN

```
FASE DE IMPLEMENTACIÓN
═══════════════════════════════════════════════

Fase 1: Infraestructura base
  ├── Instalar ChromaDB + sentence-transformers
  ├── Implementar RAGEngine (engine.py)
  ├── Implementar PromptBuilder (prompt_builder.py)
Fase 2: Integración inicial:
  ├── Crear documentos seed para tool_knowledge (15 JSONs)
  └── Integrar en Flask (punto de inyección en /chat)

Fase 3: Indexación automática
  ├── Implementar DatasetIndexer (indexer.py)
  ├── Hook post-download_owid para indexar automáticamente
  ├── Crear documentos seed para methodology (16 JSONs)
  └── Re-indexar datasets ya descargados (batch)

Fase 4: Memoria conversacional
  ├── Implementar ConversationMemory (memory.py)
  ├── Hook en /chat para registrar turnos
  ├── Implementar resúmenes de sesión
  └── Implementar SmartRetriever con clasificación de intención

Fase 5: Refinamiento
  ├── Ajustar umbrales de relevancia
  ├── Ajustar presupuesto de tokens por colección
  ├── Implementar re-ranking temporal
  ├── Implementar auto-limpieza de memoria
  └── Testing y métricas

DEPENDENCIAS PIP:
  chromadb >= 0.4.0
  sentence-transformers >= 2.2.0
  (Flask y SQLite ya existen)

IMPACTO ESPERADO:
  - 50% menos tool calls redundantes (el agente "sabe" qué datos tiene)
  - Continuidad conversacional entre sesiones
  - Respuestas metodológicamente informadas sin prompting manual
  - Base para implementar caveat_engine y analysis_planner
```
