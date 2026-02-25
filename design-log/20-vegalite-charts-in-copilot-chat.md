# Design Log 20 — VegaLite Chart Generation in Copilot Chat

## Background
El copilot_chat actual permite conversar sobre datasets y ejecutar herramientas (buscar, descargar, analizar), pero no puede generar visualizaciones directamente en el chat. Los usuarios deben salir del chat para crear gráficos.

## Problem
Los usuarios quieren que el asistente de IA pueda generar y renderizar gráficos VegaLite directamente en la conversación, visualizando insights relevantes de los datasets que tienen disponibles.

## Questions and Answers
- Q: ¿Qué tecnología usar para renderizar gráficos?
  - A: **VegaLite** - Ya existe infraestructura en el proyecto (chart builder modal usa VegaLite v5.6.0)
- Q: ¿Cómo debe generar el LLM el gráfico?
  - A: Nueva herramienta `generate_chart` que recibe dataset_id y spec VegaLite en JSON
- Q: ¿Dónde se renderiza el gráfico?
  - A: Directamente en el thread del chat, como mensaje especial tipo "chart"
- Q: ¿Qué datasets puede usar?
  - A: Cualquier dataset de los datasets_catalog (local o descargado)
- Q: ¿El usuario debe escribir VegaLite manualmente?
  - A: No, el LLM genera la especificación automáticamente basado en la conversación

## Design

### 1. Nueva Herramienta: `generate_chart`

```python
{
    "name": "generate_chart",
    "description": "Genera un gráfico VegaLite a partir de un dataset",
    "parameters": {
        "dataset_id": "ID del dataset en datasets_catalog",
        "title": "Título del gráfico",
        "vegalite_spec": "Especificación VegaLite en JSON"
    }
}
```

### 2. Flujo de Trabajo

```
Usuario: "Muestrame un grafico de salarios reales por pais"
        ↓
LLM detecta intención de visualización
        ↓
LLM busca dataset de salarios (list_datasets/search)
        ↓
LLM llama generate_chart con VegaLite spec
        ↓
Backend genera chart_id, guarda metadata
        ↓
Frontend recibe respuesta tipo "chart"
        ↓
Frontend renderiza con VegaLite embed
```

### 3. Estructura de Mensaje Chart

```json
{
    "role": "assistant",
    "type": "chart",
    "content": "Aquí tienes el gráfico de salarios reales:",
    "chart_data": {
        "chart_id": "uuid",
        "dataset_id": "dataset_uuid",
        "title": "Salarios Reales por País",
        "vegalite_spec": { /* spec JSON */ }
    }
}
```

### 4. Componentes a Modificar

| Archivo | Cambios |
|---------|---------|
| `src/ai_chat.py` | Agregar herramienta `generate_chart` |
| `src/web/api/copilot.py` | Manejar mensajes tipo "chart" en responses |
| `src/web/templates/copilot_chat.html` | Renderizar mensajes chart con VegaLite |
| `src/copilot_agent.py` | Asegurar tool esté registrada en MCP tools |

### 5. VegaLite Spec Helper

Crear función helper para construir specs comunes:
- Line chart: series temporales
- Bar chart: comparaciones
- Scatter: correlaciones
- Area: tendencias acumuladas

```python
def build_line_chart_spec(x_field: str, y_field: str, color_field: str = None) -> dict:
    """Construye spec VegaLite para line chart."""
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "mark": "line",
        "encoding": {
            "x": {"field": x_field, "type": "quantitative"},
            "y": {"field": y_field, "type": "quantitative"},
            "color": {"field": color_field, "type": "nominal"} if color_field else None
        }
    }
```

## Implementation Plan

### Fase 1: Backend - Herramienta generate_chart (2 horas)
- [ ] Agregar herramienta `generate_chart` en ChatAssistant.tools
- [ ] Implementar función `execute_generate_chart()` que:
  - Busca dataset en catalog
  - Lee datos (limitado a 1000 filas para performance)
  - Valida que campos existan en el spec
  - Genera chart_id
- [ ] Agregar formato de respuesta especial "chart" en AIChat

### Fase 2: API - Manejo de mensajes chart (1 hora)
- [ ] Modificar `/copilot/chat` para incluir chart_data en responses
- [ ] Crear endpoint opcional: GET `/copilot/charts/{chart_id}` para obtener datos

### Fase 3: Frontend - Renderizado VegaLite (2 horas)
- [ ] Modificar función `renderMessage()` en copilot_chat.html para detectar type="chart"
- [ ] Usar `vegaEmbed()` (ya incluido en template) para renderizar spec
- [ ] Agregar estilos CSS para contenedores de gráficos
- [ ] Agregar botón "Descargar PNG" para exportar gráfico

### Fase 4: Prompt Engineering (1 hora)
- [ ] Mejorar system prompt para:
  - Explicar cuándo usar generate_chart
  - Proporcionar ejemplos de specs VegaLite
  - Instruir sobre buenas prácticas de visualización

### Fase 5: Testing (1 hora)
- [ ] Test: "Muestra un gráfico de PIB por país"
- [ ] Test: "Comparar inflación entre Argentina y Brasil"
- [ ] Test: "Tendencia de desempleo últimos 10 años"

## Examples

### Ejemplo 1: Gráfico de líneas (series temporales)

**Usuario:** "Muéstrame la evolución del PIB per cápita en LATAM"

**LLM Action:**
```
[TOOL_CALL]generate_chart{
  "dataset_id": "gdp_per_capita_owid_latam",
  "title": "Evolución del PIB per Cápita - LATAM",
  "vegalite_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "mark": "line",
    "encoding": {
      "x": {"field": "Year", "type": "temporal", "title": "Año"},
      "y": {"field": "GDP_per_capita", "type": "quantitative", "title": "PIB per cápita (USD)"},
      "color": {"field": "Country", "type": "nominal", "title": "País"}
    }
  }
}[/TOOL_CALL]
```

**Output:** Gráfico renderizado en el chat

### Ejemplo 2: Gráfico de barras (comparación)

**Usuario:** "Compara la tasa de desempleo entre países latinoamericanos en 2023"

**LLM Action:**
```
[TOOL_CALL]generate_chart{
  "dataset_id": "unemployment_latam_2023",
  "title": "Tasa de Desempleo por País (2023)",
  "vegalite_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "mark": "bar",
    "encoding": {
      "x": {"field": "Unemployment_Rate", "type": "quantitative", "title": "% Desempleo"},
      "y": {"field": "Country", "type": "nominal", "title": "País", "sort": "-x"}
    }
  }
}[/TOOL_CALL]
```

### Ejemplo 3: Scatter plot (correlación)

**Usuario:** "Hay correlación entre inflación y desempleo?"

**LLM Action:**
```
[TOOL_CALL]generate_chart{
  "dataset_id": "economic_indicators",
  "title": "Correlación: Inflación vs Desempleo",
  "vegalite_spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "mark": "point",
    "encoding": {
      "x": {"field": "Inflation_Rate", "type": "quantitative", "title": "Inflación (%)"},
      "y": {"field": "Unemployment_Rate", "type": "quantitative", "title": "Desempleo (%)"},
      "color": {"field": "Country", "type": "nominal"}
    }
  }
}[/TOOL_CALL]
```

## Trade-offs

### Pros:
- ✅ VegaLite ya está disponible en el proyecto
- ✅ No requiere librerías adicionales
- ✅ Gráficos interactivos (tooltip, zoom)
- ✅ Exportable a PNG/SVG
- ✅ Permite conversación contextual sobre visualizaciones

### Cons:
- ⚠️ Dataset limitado a 1000 filas (performance)
- ⚠️ LLM debe generar JSON válido (puede fallar)
- ⚠️ Campos deben existir exactamente en el dataset

### Mitigaciones:
- Validación de campos antes de generar chart
- Fallback a tabla si spec es inválido
- Sugerir campos disponibles si el usuario usa uno incorrecto

## Archivos a Modificar

1. `src/ai_chat.py` - Agregar herramienta generate_chart (líneas ~150-250)
2. `src/web/api/copilot.py` - Manejar chart_data en responses (líneas ~100-150)
3. `src/web/templates/copilot_chat.html` - Renderizado de charts (líneas ~200-300)
4. `src/copilot_agent.py` - Asegurar tool registration (líneas ~180-200)

## Success Criteria

- [ ] Usuario puede pedir "grafico de X" y el asistente genera visualización
- [ ] Gráfico se renderiza correctamente en el chat thread
- [ ] Gráfico es interactivo (hover, tooltip)
- [ ] Se puede descargar como PNG
- [ ] Si el dataset no existe, el asistente lo busca primero
- [ ] Si el campo es inválido, se da mensaje de error claro

## Notas de Implementación

- Usar `vegaEmbed` ya disponible en el template (cargado desde CDN)
- Los chart_ids se generan con UUID para tracking
- Guardar spec JSON en el mensaje para reproducibilidad
- Considerar agregar botón "Editar en Chart Builder" para refinamiento manual

## Questions for Future Iterations

- Q: ¿Soportar múltiples gráficos en una sola respuesta?
- Q: ¿Agregar tipo "chart_comparison" para comparar dos datasets?
- Q: ¿Permitir usuario especificar tipo de gráfico ("como barras", "de lineas")?
- Q: ¿Cache de gráficos generados para reutilizar?

---

*Created: 2026-02-16*
*Feature: Copilot Chat VegaLite Integration*
*Est. Effort: 7 hours*
