# Translate UI from Spanish to English - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Translate all Spanish UI text strings to English across the web interface templates, routes, and API files.

**Architecture:** Direct string replacement in source files. No i18n framework needed as this is a one-time translation to English-only interface. Files affected: 1 Python routes file, 5 HTML templates, and 2 API modules.

**Tech Stack:** Flask, Jinja2, Alpine.js, JavaScript

---

## Overview

The web interface currently has a mix of English and Spanish text. This plan translates all Spanish strings to English for consistency. Total ~120 text strings across 8 files.

## Files to Modify

1. src/web/routes.py - Page subtitles
2. src/web/templates/base.html - Sidebar tooltips  
3. src/web/templates/browse_local.html - UI labels and buttons
4. src/web/templates/copilot_chat.html - Chat interface (bulk of work)
5. src/web/templates/visualization_canvas.html - Dataset editor
6. src/web/templates/visualization_pygwalker.html - PyGWalker viewer
7. src/web/api/visualization.py - Chart descriptions
8. src/web/api/agent.py - Example data

---

## Tasks

### Task 1: Update Page Subtitles in routes.py

**Files:** Modify src/web/routes.py

**Changes:**
- Line 117: "Estado del proyecto" → "Project Status"
- Line 160: "Datasets disponibles localmente" → "Locally Available Datasets"
- Line 175: "Editar datasets" → "Edit Datasets"
- Line 183: "Buscar indicadores y temas" → "Search Indicators and Topics"
- Line 207: "Explorar con PyGWalker" → "Explore with PyGWalker"
- Line 305: "Atajos y guia" → "Shortcuts and Guide"

**Steps:**
1. Edit each subtitle string in the route handlers
2. Verify: python -c "from src.web.routes import *; print('Import successful')"
3. Commit: git add src/web/routes.py && git commit -m "translate: convert page subtitles from Spanish to English"

---

### Task 2: Update Sidebar Tooltips in base.html

**Files:** Modify src/web/templates/base.html

**Changes:**
- Line 46: title="sidebarCollapsed ? 'Mostrar menú' : 'Ocultar menú'" → title="sidebarCollapsed ? 'Show menu' : 'Hide menu'"

**Steps:**
1. Edit the file
2. Verify template syntax: python -c "from src.web import create_app; app = create_app(); print('Template OK')"
3. Commit: git add src/web/templates/base.html && git commit -m "translate: convert sidebar tooltips from Spanish to English"

---

### Task 3: Update Browse Local Template

**Files:** Modify src/web/templates/browse_local.html

**Changes:**
- Line 48: "Descargar todo" → "Download all"
- Line 93: title="Actualizar datasets seleccionados" → title="Update selected datasets"
- Line 95: "Actualizando..." / "Actualizar seleccionados" → "Updating..." / "Update selected"
- Lines 198, 236: title="Editar dataset" → title="Edit dataset"

**Steps:**
1. Make changes
2. Verify: python -c "from src.web import create_app; app = create_app()"
3. Commit: git add src/web/templates/browse_local.html && git commit -m "translate: convert browse_local template from Spanish to English"

---

### Task 4: Update Visualization Canvas Template

**Files:** Modify src/web/templates/visualization_canvas.html

**Changes:**
- Line 10: placeholder="Buscar dataset" → placeholder="Search dataset"
- Line 74: "Tabla SQL:" → "SQL Table:"
- Line 135: "Limpiar" → "Clear"

**Steps:**
1. Make changes
2. Commit: git add src/web/templates/visualization_canvas.html && git commit -m "translate: convert visualization canvas template from Spanish to English"

---

### Task 5: Update PyGWalker Template

**Files:** Modify src/web/templates/visualization_pygwalker.html

**Changes:**
- Line 45: placeholder="Buscar dataset" → placeholder="Search dataset"
- Line 78: "PyGWalker podría tardar en cargar o consumir mucha memoria del navegador." → "PyGWalker may take time to load or consume significant browser memory."

**Steps:**
1. Make changes
2. Commit: git add src/web/templates/visualization_pygwalker.html && git commit -m "translate: convert pygwalker template from Spanish to English"

---

### Task 6: Update Copilot Chat Template - Part 1 (Tooltips and Buttons)

**Files:** Modify src/web/templates/copilot_chat.html

**Changes:**
- Line 592: title="Ocultar panel" → title="Hide panel"
- Line 620: title="Renombrar thread" → title="Rename thread"
- Line 628: title="Eliminar thread" → title="Delete thread"
- Line 691: "Calidad" → "Quality"
- Line 699: "Transformar" → "Transform"
- Line 706: "Reporte" → "Report"
- Line 713: "Explorar" → "Explore"
- Line 719: title="Primero ejecuta Calidad para detectar problemas" → title="First run Quality to detect issues"
- Line 721: "Limpiar" → "Clean"
- Line 727: title="Abrir canvas de visualización (con gráficos actuales si hay)" → title="Open visualization canvas (with current charts if any)"
- Line 729: "Visualizar" → "Visualize"
- Line 732: title="Gráfico de correlación con 2 datasets (cruce como Compare)" → title="Correlation chart with 2 datasets (cross as Compare)"
- Line 737: title="Derivar nuevo campo con IA" → title="Derive new field with AI"
- Line 739: "Derivar" → "Derive"

**Steps:**
1. Edit lines 587-745
2. Commit: git add src/web/templates/copilot_chat.html && git commit -m "translate: convert copilot chat action buttons and tooltips to English"

---

### Task 7: Update Copilot Chat Template - Part 2 (Quality Panel)

**Files:** Modify src/web/templates/copilot_chat.html

**Changes:**
- Line 749: "Calidad de Datos" → "Data Quality"
- Line 759: "Puntuación:" → "Score:"
- Line 779: "más problemas" → "more issues"
- Line 785: "¡Sin problemas detectados!" → "No issues detected!"
- Line 793: "Limpiar Automático" → "Automatic Clean"

**Steps:**
1. Edit lines 745-810
2. Commit: git add src/web/templates/copilot_chat.html && git commit -m "translate: convert quality panel labels to English"

---

### Task 8: Update Copilot Chat Template - Part 3 (Chart Builder)

**Files:** Modify src/web/templates/copilot_chat.html

**Changes:**
- Line 860: "Gráficos propuestos" → "Suggested Charts"
- Line 865: "Gráfico" → "Chart"
- Line 868: title="Abrir canvas y generar este gráfico" → title="Open canvas and generate this chart"
- Line 1157: "Tipo de Gráfico" → "Chart Type"
- Line 1173: "Selecciona campos:" → "Select fields:"
- Line 1275: "Instrucción (opcional)" → "Instruction (optional)"
- Line 1277: placeholder="Ej: Mostrar solo top 10 países..." → placeholder="E.g., Show only top 10 countries..."
- Line 1283: "Título" → "Title"
- Line 1285: placeholder="Título del gráfico" → placeholder="Chart title"
- Line 1296: "Selecciona campos para X e Y" → "Select fields for X and Y"
- Line 1303: "Limpiar" → "Clear"

**Steps:**
1. Edit chart builder section
2. Commit: git add src/web/templates/copilot_chat.html && git commit -m "translate: convert chart builder labels to English"

---

### Task 9: Update Copilot Chat Template - Part 4 (Derive Field Modal)

**Files:** Modify src/web/templates/copilot_chat.html

**Changes:**
- Line 1329: "Derivar Nuevo Campo" → "Derive New Field"
- Line 1339: "Nombre del Campo" → "Field Name"
- Line 1365: "Descripción (NL)" → "Description (NL)"
- Line 1367: placeholder text → English placeholder
- Line 1371: "Sugerencias:" and Spanish suggestions → "Suggestions:" with English examples
- Line 1402: "Código Generado" → "Generated Code"
- Line 1459: "Eliminar" → "Delete"

**Steps:**
1. Edit modal content
2. Commit: git add src/web/templates/copilot_chat.html && git commit -m "translate: convert derive field modal to English"

---

### Task 10: Update Copilot Chat Template - Part 5 (Chart Types)

**Files:** Modify src/web/templates/copilot_chat.html

**Changes:**
- Line 1523: name: 'Líneas' → name: 'Lines'
- Line 1525: name: 'Dispersión' → name: 'Scatter'
- Line 1528: name: 'Área' → name: 'Area'

**Steps:**
1. Edit chart templates array
2. Commit: git add src/web/templates/copilot_chat.html && git commit -m "translate: convert chart type names to English"

---

### Task 11: Update Copilot Chat Template - Part 6 (JavaScript Messages)

**Files:** Modify src/web/templates/copilot_chat.html

**Changes:**
- Line 1743: "No puedes eliminar el último thread. Crea uno nuevo primero." → "You cannot delete the last thread. Create a new one first."
- Line 1753: "Eliminar thread" → "Delete Thread"
- Line 1754: "¿Eliminar este thread? Esta acción no se puede deshacer." → "Delete this thread? This action cannot be undone."
- Line 1777: "Nuevo nombre para el thread:" → "New name for the thread:"
- Line 2154: "Análisis de Calidad Completado" → "Quality Analysis Completed"
- Line 2155: "Puntuación:" → "Score:"
- Line 2248: "Transformación de Datos" → "Data Transformation"
- Lines 2249-2252: Update example texts to English
- Line 2277: "Análisis de Datos" → "Data Analysis"
- Line 2282: "Reporte completado" → "Report completed"
- Line 2284: "Reporte Generado" → "Report Generated"
- Line 2306: "Sugerencias de Exploración" → "Exploration Suggestions"
- Line 2313: "Exploración Completada" → "Exploration Completed"
- Line 2323: "No hay problemas de calidad para limpiar. Ejecuta primero el análisis de calidad." → "No quality issues to clean. Run the quality analysis first."
- Line 2341: "Limpieza de Datos" → "Data Cleaning"
- Line 2344: "Código generado para limpiar:" → "Generated code to clean:"
- Line 2349: "Datos limpiados:" and "filas resultantes" → "Data cleaned:" and "resulting rows"
- Line 2531: "Error generando gráfico:" → "Error generating chart:"
- Line 2555: "Error renderizando gráfico" → "Error rendering chart"
- Line 2657: "¿Eliminar todos los gráficos del canvas?" → "Delete all charts from the canvas?"
- Line 2801: "Error generando campo" → "Error generating field"
- Line 3026: "No se pudieron guardar los gráficos para el canvas:" → "Could not save charts for the canvas:"
- Line 3245: title="Ver código" → title="View code"
- Line 3276: title="Copiar código" → title="Copy code"
- Line 3280: title="Ejecutar código" → title="Execute code"
- Line 3419: "Error: No se pudo acceder al estado de la aplicación" → "Error: Could not access application state"
- Line 3472: "Datos" and "filas × columnas" → "Data" and "rows × columns"

**Steps:**
1. Edit all JavaScript string literals
2. Commit: git add src/web/templates/copilot_chat.html && git commit -m "translate: convert copilot chat JavaScript messages to English"

---

### Task 12: Update Visualization API

**Files:** Modify src/web/api/visualization.py

**Changes:**
- Line 317: "Mapa geográfico de USA" → "USA geographic map"
- Line 362: "Mapa geográfico mundial" → "World geographic map"
- Line 407: "Regresión lineal y tendencia" → "Linear regression and trend"
- Line 527: "Líneas con atributos personalizados" → "Lines with custom attributes"
- Line 553: "Rectángulos con rango X-Y" → "Rectangles with X-Y range"
- Line 566: "Áreas con atributos personalizados" → "Areas with custom attributes"
- Line 592: "Detectar automaticamente el mejor tipo de gráfico" → "Automatically detect the best chart type"
- Line 1253: "mostrar solo top 5 países" → "show only top 5 countries"
- Line 1246: "PIB por País" → "GDP by Country"

**Steps:**
1. Edit file
2. Commit: git add src/web/api/visualization.py && git commit -m "translate: convert visualization API descriptions to English"

---

### Task 13: Update Agent API

**Files:** Modify src/web/api/agent.py

**Changes:**
- Line 309: "Análisis PIB LATAM" → "LATAM GDP Analysis"
- Line 327: "Análisis de Datos" → "Data Analysis"
- Note: Keep example data field names (pais, año) as they represent actual data

**Steps:**
1. Edit file
2. Commit: git add src/web/api/agent.py && git commit -m "translate: convert agent API default topics to English"

---

### Task 14: Final Verification

**Step 1: Verify all templates load correctly**
Run: python -c "from src.web import create_app; app = create_app(); print('All templates loaded successfully')"

**Step 2: Search for remaining Spanish strings**
Run: grep -rn "[áéíóúñÁÉÍÓÚÑ]" src/web/templates/ src/web/routes.py src/web/api/
Expected: Only example data field names (pais, año) should remain.

**Step 3: Test the web interface**
Run: python -m src.web
Visit http://127.0.0.1:5000 and verify all UI text is in English.

**Step 4: Final commit**
git commit -m "translate: complete UI translation from Spanish to English

- Translated all page subtitles in routes.py
- Translated sidebar tooltips in base.html
- Translated browse_local.html labels and buttons
- Translated visualization_canvas.html and visualization_pygwalker.html
- Translated copilot_chat.html (largest file with 100+ strings)
  - Action buttons and tooltips
  - Quality panel labels
  - Chart builder labels
  - Derive field modal
  - Chart type names
  - All JavaScript messages and alerts
- Translated visualization API descriptions
- Translated agent API default topics

All UI text is now in English for consistency."

---

## Summary

**Total files modified:** 8
**Total text strings translated:** ~120
**Estimated time:** 30-45 minutes
**Testing required:** Load web app and verify all pages render correctly

**Key considerations:**
- Keep example data field names (pais, año) as they represent actual data
- Test thoroughly after each file group
- Verify no syntax errors in Jinja2 templates
- Ensure Alpine.js expressions remain valid
