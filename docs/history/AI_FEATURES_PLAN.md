# Plan de Funcionalidades de IA para Data Curator

**Fecha:** 8 de Enero 2026  
**Estado:** En desarrollo - Iniciando con Chat-to-Data

---

## 1. Asistente de Consulta en Lenguaje Natural sobre Datasets (Chat-to-Data)

**Estado: 🚧 EN DESARROLLO**

### Descripción
Un chat conversacional que permite a los usuarios hacer preguntas sobre sus datasets en español y obtener respuestas automáticas con análisis, visualizaciones o extracciones de datos.

**Ejemplos:**
- "¿Cuál es el país con mayor informalidad laboral en 2020?"
- "Muéstrame la evolución de salarios reales en Argentina vs Chile"
- "¿Qué dataset tiene mayor cobertura temporal sobre libertad económica?"
- "Busca y descarga datos sobre inflación de ILOSTAT"

### Evaluación
- **Utilidad para el usuario:** 9/10
- **Dificultad de implementación:** 6/10
- **Innovación:** 7/10
- **Prioridad:** 🥈 2° (implementación en curso)

### Características clave
- Chat conversacional estilo GPT/Gemini
- Búsqueda en catálogo local de datasets
- Búsqueda en fuentes externas (ILOSTAT, OECD, IMF, WorldBank, OWID)
- Descarga automática de datasets no existentes
- Análisis de datos en lenguaje natural
- Generación de visualizaciones
- Respuestas en español

---

## 2. Recomendador Inteligente de Datasets Relacionados

**Estado: 📋 PLANIFICADO**

### Descripción
Sistema que sugiere automáticamente datasets complementarios basándose en el contexto de trabajo del usuario. Usa embeddings semánticos para encontrar relaciones no obvias entre datasets.

**Ejemplos:**
- Usuario busca "salarios reales" → Sistema sugiere: "inflación", "costo de vida", "productividad laboral"
- Usuario descarga datos de Argentina → Sistema sugiere: países similares económicamente
- Detecta gaps temporales y sugiere fuentes que podrían llenarlos

### Evaluación
- **Utilidad para el usuario:** 8/10
- **Dificultad de implementación:** 4/10
- **Innovación:** 6/10
- **Prioridad:** 🥇 1° (siguiente fase)

---

## 3. Limpieza y Normalización Inteligente con Explicaciones

**Estado: 📋 PLANIFICADO**

### Descripción
Mejora el módulo de limpieza existente usando IA para detectar anomalías, sugerir transformaciones y explicar cada decisión de limpieza en lenguaje natural.

**Capacidades:**
- Detecta outliers y explica si son errores o valores legítimos
- Sugiere imputación de valores faltantes con justificación metodológica
- Identifica inconsistencias entre datasets de la misma fuente
- Genera reportes de calidad de datos con narrativa explicativa

**Ejemplo de output:**
```
⚠️ ADVERTENCIA: Detectados 3 valores atípicos en "salarios_reales":
  - Argentina 2019: $15,234 (3.2σ sobre la media)
  - Recomendación: MANTENER - Consistente con crisis económica documentada
  - Fuentes de validación: IMF WEO Database, INDEC
```

### Evaluación
- **Utilidad para el usuario:** 9/10
- **Dificultad de implementación:** 5/10
- **Innovación:** 8/10
- **Prioridad:** 🥉 3°

---

## 4. Generador de Código de Análisis Personalizado

**Estado: 📋 PLANIFICADO**

### Descripción
Genera scripts de Python/R completos y reproducibles basados en la descripción del análisis que el usuario quiere hacer. Incluye exploración, visualización, modelado estadístico y exportación.

**Flujo:**
1. Usuario describe su análisis: "Quiero comparar la correlación entre informalidad laboral y libertad económica en LATAM 2015-2020"
2. Sistema genera código Python completo con:
   - Carga de datasets relevantes
   - Merge/joins necesarios
   - Análisis estadístico (correlaciones, regresiones)
   - Visualizaciones (matplotlib/seaborn)
   - Exportación de resultados
3. Usuario puede ejecutar directamente o modificar

### Evaluación
- **Utilidad para el usuario:** 10/10
- **Dificultad de implementación:** 7/10
- **Innovación:** 9/10
- **Prioridad:** 4°

---

## 5. Auditor de Sesgo y Calidad Metodológica

**Estado: 📋 PLANIFICADO**

### Descripción
Analiza datasets y análisis propuestos para detectar sesgos metodológicos, problemas de causalidad, variables omitidas y limitaciones de los datos. Actúa como "peer reviewer" automatizado.

**Capacidades:**
- Detecta sesgos de selección (ej: solo países desarrollados)
- Identifica problemas de causalidad inversa
- Sugiere variables de control faltantes
- Valida rangos temporales (ej: incluir pre/post crisis)
- Chequea consistencia entre fuentes
- Genera sección de "Limitaciones" para papers

**Ejemplo:**
```
📊 AUDITORÍA DE CALIDAD - salarios_reales_analysis

✅ Fortalezas:
  - Cobertura temporal adecuada (12 años)
  - Fuente confiable (ILOSTAT)

⚠️ Limitaciones detectadas:
  1. SESGO DE SELECCIÓN: Solo países con datos completos (survivor bias)
     → Recomendación: Usar panel desbalanceado o reportar attrition
  
  2. VARIABLE OMITIDA: No se controla por inflación
     → Datasets sugeridos: inflation_cpi_worldbank_latam_2010_2022
  
  3. CAUSALIDAD: Correlación salarios-informalidad no implica causalidad
     → Considerar: IV estimation, diff-in-diff, RDD si aplica
```

### Evaluación
- **Utilidad para el usuario:** 10/10
- **Dificultad de implementación:** 8/10
- **Innovación:** 10/10
- **Prioridad:** 5°

---

## Matriz de Decisión

| Propuesta | Utilidad | Dificultad | Innovación | ROI | Prioridad |
|-----------|----------|------------|------------|-----|-----------|
| #1 Chat-to-Data | 9 | 6 | 7 | **Alto** | 🥈 2° (EN DESARROLLO) |
| #2 Recomendador | 8 | 4 | 6 | **Muy Alto** | 🥇 1° |
| #3 Limpieza IA | 9 | 5 | 8 | **Alto** | 🥉 3° |
| #4 Gen. Código | 10 | 7 | 9 | **Medio** | 4° |
| #5 Auditor | 10 | 8 | 10 | **Medio** | 5° |

---

## Roadmap de Implementación

### Fase 1: Chat-to-Data (EN CURSO)
**Tiempo estimado:** 2-3 semanas  
**Componentes:**
- Backend de chat con OpenRouter
- Sistema de herramientas (búsqueda, descarga, análisis)
- Interfaz web de chat
- Integración con catálogo y fuentes de datos

### Fase 2: Recomendador de Datasets
**Tiempo estimado:** 1-2 semanas  
**Dependencias:** Catálogo completo

### Fase 3: Limpieza Inteligente
**Tiempo estimado:** 3-4 semanas  
**Dependencias:** Pipeline de limpieza estable

### Fase 4: Generador de Código o Auditor
**Tiempo estimado:** 6-8 semanas  
**Decisión basada en:** Feedback de usuarios de Fases 1-3

---

## Notas Técnicas

### Stack Tecnológico
- **LLM:** OpenRouter (Claude 3.5 Sonnet por defecto)
- **Backend:** Flask + Python
- **Frontend:** HTML/CSS/JS vanilla
- **Embeddings:** OpenAI embeddings via OpenRouter
- **Database:** SQLite con FTS5

### Consideraciones de Costos
- OpenRouter: ~$3-5 por 1M tokens (Claude)
- Cache de respuestas comunes para reducir costos
- Embeddings: ~$0.10 por 1M tokens

### Seguridad
- Sandbox para ejecución de código generado
- Validación de inputs
- Rate limiting en endpoints
- No exponer API keys al frontend
