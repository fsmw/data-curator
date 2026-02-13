#!/usr/bin/env python3
"""
Comprehensive translation updater script.
This script:
1. Updates HTML templates to wrap text with {{ _('...') }}
2. Updates the messages.po file with Spanish translations
"""

import re
from pathlib import Path

# All UI strings and their Spanish translations
ALL_TRANSLATIONS = {
    # Search page
    "Search Indicators": "Buscar Indicadores",
    "Search by keyword (e.g., GDP, inflation, unemployment)": "Buscar por palabra clave (ej. PIB, inflación, desempleo)",
    "Data Source": "Fuente de Datos",
    "All Sources": "Todas las Fuentes",
    "Searching...": "Buscando...",
    "Quick Filters": "Filtros Rápidos",
    "LATAM + Spain": "LATAM + España",
    "Inflation > 10%": "Inflación > 10%",
    "Poverty": "Pobreza",
    "Results": "Resultados",
    "Download selected": "Descargar seleccionados",
    "Downloading...": "Descargando...",
    "Indicator": "Indicador",
    "Description": "Descripción",
    "Source": "Fuente",
    "Actions": "Acciones",
    "Downloaded": "Descargado",
    "Update": "Actualizar",
    "Preview chart": "Vista previa del gráfico",
    "Preview data": "Vista previa de datos",
    "Download CSV data": "Descargar datos CSV",
    "Update dataset (re-download)": "Actualizar dataset (re-descargar)",
    "Page": "Página",
    "of": "de",
    "Prev": "Anterior",
    "Next": "Siguiente",
    
    # Browse Local
    "Search local datasets": "Buscar datasets locales",
    "All topics": "Todos los temas",
    "Refresh": "Actualizar",
    "Download all": "Descargar todo",
    "Total datasets": "Total de datasets",
    "Database size": "Tamaño de base de datos",
    "Completeness": "Completitud",
    "Update selected": "Actualizar seleccionados",
    "Table": "Tabla",
    "Cards": "Tarjetas",
    "No datasets in the catalog": "No hay datasets en el catálogo",
    "Index datasets": "Indexar datasets",
    "Rows": "Filas",
    "Years": "Años",
    "Countries": "Países",
    "Edit dataset": "Editar dataset",
    "View dataset details": "Ver detalles del dataset",
    "Delete dataset": "Eliminar dataset",
    "0 datasets found": "0 datasets encontrados",
    "datasets found": "datasets encontrados",
    
    # Edit/Visualization
    "Concept Shelf": "Estante de Conceptos",
    "Search dataset": "Buscar dataset",
    "Select a dataset": "Seleccionar un dataset",
    "SmoothCSV URL": "URL de SmoothCSV",
    "Select a dataset to generate the URL.": "Selecciona un dataset para generar la URL.",
    "Data Grid": "Grilla de Datos",
    "Fork name (optional)": "Nombre del fork (opcional)",
    "Save as": "Guardar como",
    "Reload": "Recargar",
    "SQL Row Filter": "Filtro de Filas SQL",
    "e.g. country = 'Chile' AND year >= 2000": "ej. country = 'Chile' AND year >= 2000",
    "Apply": "Aplicar",
    "Clear": "Limpiar",
    "Use SQL WHERE syntax (without SELECT).": "Usa sintaxis SQL WHERE (sin SELECT).",
    "SQL Console": "Consola SQL",
    "Execute": "Ejecutar",
    "Reset": "Reiniciar",
    "Delimiter": "Delimitador",
    "Quote": "Comilla",
    "Quote mode": "Modo de comilla",
    "Encoding": "Codificación",
    "comma/tab": "coma/tab",
    "double/single": "doble/simple",
    "minimal/always": "mínimo/siempre",
    "UTF-8": "UTF-8",
    "Location (e.g. 10:3-20:5)": "Ubicación (ej. 10:3-20:5)",
    "first": "primeros",
    "Sample": "Muestra",
    "PyGWalker": "PyGWalker",
    "Edited": "Editado",
    "No datasets": "No hay datasets",
    "Load PyGWalker": "Cargar PyGWalker",
    
    # Copilot Chat
    "Data Threads": "Hilos de Datos",
    "Data Workbench": "Banco de Trabajo de Datos",
    "New Thread": "Nuevo Hilo",
    "Rename thread": "Renombrar hilo",
    "Delete thread": "Eliminar hilo",
    "Quality": "Calidad",
    "Transform": "Transformar",
    "Report": "Reporte",
    "Explore": "Explorar",
    "Clean": "Limpiar",
    "Visualize": "Visualizar",
    "Derive": "Derivar",
    "Data Quality": "Calidad de Datos",
    "Score": "Puntuación",
    "First run Quality to detect issues": "Primero ejecuta Calidad para detectar problemas",
    "Open visualization canvas (with current charts if any)": "Abrir lienzo de visualización (con gráficos actuales si hay)",
    "Correlation chart with 2 datasets (cross as Compare)": "Gráfico de correlación con 2 datasets (cruzar como Comparar)",
    "Derive new field with AI": "Derivar nuevo campo con IA",
    "Welcome to AI Data Assistant": "Bienvenido al Asistente de Datos con IA",
    "I can help you explore datasets, analyze data, and download from OWID.": "Puedo ayudarte a explorar datasets, analizar datos y descargar de OWID.",
    'Try asking: "Show me GDP data for Brazil" or "What datasets do we have about health?"': 'Prueba preguntando: "Muéstrame datos de PIB de Brasil" o "¿Qué datasets tenemos sobre salud?"',
    "Thinking...": "Pensando...",
    "Suggested Charts": "Gráficos Sugeridos",
    "Open canvas and generate this chart": "Abrir lienzo y generar este gráfico",
    "An error occurred": "Ocurrió un error",
    "Thinking Process": "Proceso de Pensamiento",
    "Suggested Actions": "Acciones Sugeridas",
    "Visual Encoding": "Codificación Visual",
    "Color": "Color",
    "Visualization Canvas": "Lienzo de Visualización",
    "Exit Fullscreen": "Salir de Pantalla Completa",
    "Fullscreen": "Pantalla Completa",
    "Export PNG": "Exportar PNG",
    "Clear All": "Limpiar Todo",
    "Remove": "Eliminar",
    "Toggle Visual Builder": "Alternar Constructor Visual",
    "Ask or drag fields here...": "Pregunta o arrastra campos aquí...",
    "Load a dataset to unlock visual tools.": "Carga un dataset para desbloquear herramientas visuales.",
    "Chart Builder": "Constructor de Gráficos",
    "Chart Type": "Tipo de Gráfico",
    "Encodings": "Codificaciones",
    "Select fields": "Seleccionar campos",
    "Select...": "Seleccionar...",
    "Size": "Tamaño",
    "Optional...": "Opcional...",
    "Instruction (optional)": "Instrucción (opcional)",
    "E.g., Show only top 10 countries...": "Ej., Mostrar solo top 10 países...",
    "Title": "Título",
    "Chart title": "Título del gráfico",
    "Preview": "Vista previa",
    "Select fields for X and Y": "Selecciona campos para X e Y",
    "Derive New Field": "Derivar Nuevo Campo",
    "Field Name": "Nombre del Campo",
    "ej: growth_rate": "ej: tasa_crecimiento",
    "Source Fields": "Campos Fuente",
    "Description (NL)": "Descripción (NL)",
    "Describe what this field should calculate. E.g., Calculate annual GDP percentage growth": "Describe qué debe calcular este campo. Ej., Calcular crecimiento porcentual anual del PIB",
    "Generated Code": "Código Generado",
    "View code": "Ver código",
    "Agregar al canvas": "Agregar al canvas",
    "Copy": "Copiar",
    "Copy code": "Copiar código",
    "Execute code": "Ejecutar código",
    "Error rendering chart": "Error al renderizar gráfico",
    "Error rendering": "Error al renderizar",
    
    # Help page
    "Shortcuts and Guide": "Atajos y Guía",
    "Getting Started": "Primeros Pasos",
    "Mises Data Curator is a comprehensive tool for discovering, downloading, and managing economic data from major international sources.": "Mises Data Curator es una herramienta integral para descubrir, descargar y gestionar datos económicos de fuentes internacionales principales.",
    "Basic Workflow": "Flujo de Trabajo Básico",
    "Find indicators using keywords or browse by source.": "Encuentra indicadores usando palabras clave o navega por fuente.",
    "Click download to fetch data from the source API.": "Haz clic en descargar para obtener datos de la API fuente.",
    "Use the AI Copilot to explore and analyze your data.": "Usa el AI Copilot para explorar y analizar tus datos.",
    "Available Data Sources": "Fuentes de Datos Disponibles",
    "BCCH (Chile Central Bank)": "BCCH (Banco Central de Chile)",
    "FRED": "FRED",
    "ILOSTAT": "ILOSTAT",
    "Keyboard Shortcuts": "Atajos de Teclado",
    "Quick Navigation": "Navegación Rápida",
    "Quick Links": "Enlaces Rápidos",
    "Search Data": "Buscar Datos",
    "About Instituto Mises Cono Sur": "Acerca del Instituto Mises Cono Sur",
    "Mises Cono Sur is an academic center that, inspired by the Austrian School of Economics, trains leaders and citizens committed to building free, prosperous, and democratic societies.": "Mises Cono Sur es un centro académico que, inspirado en la Escuela Austriaca de Economía, forma líderes y ciudadanos comprometidos con construir sociedades libres, prósperas y democráticas.",
    "Visit Website": "Visitar Sitio Web",
    
    # Auth pages
    "Current Password": "Contraseña Actual",
    "New Password": "Nueva Contraseña",
    "Confirm New Password": "Confirmar Nueva Contraseña",
    "Cancel": "Cancelar",
    "Login": "Iniciar sesión",
    "Remember me": "Recordarme",
    "Sign In": "Iniciar sesión",
    "Username Label": "Nombre de usuario",
    "Password Label": "Contraseña",
    "N/A": "N/D",
    
    # Generic
    "Local": "Local",
    "Close": "Cerrar",
    "Loading chart from Our World in Data...": "Cargando gráfico de Our World in Data...",
    "Loading data from World Bank...": "Cargando datos de World Bank...",
    "Loading data from OECD...": "Cargando datos de OECD...",
    "Could not load chart": "No se pudo cargar el gráfico",
    "Average by year (preview)": "Promedio por año (vista previa)",
    "Country": "País",
    "Code": "Código",
    "Year": "Año",
    "Value": "Valor",
    "Chart Preview": "Vista Previa del Gráfico",
    "Data Preview": "Vista Previa de Datos",
    "Download PNG": "Descargar PNG",
    "all": "todos",
    "Show": "Mostrar",
    "Hide panel": "Ocultar panel",
    "New Analysis": "Nuevo Análisis",
    "Thread": "Hilo",
    "Hide": "Ocultar",
    "Show menu": "Mostrar menú",
    "Hide menu": "Ocultar menú",
    "Export CSV": "Exportar CSV",
    "Save": "Guardar",
}

def update_po_file():
    """Update the messages.po file with all translations."""
    po_path = Path("translations/es_CL/LC_MESSAGES/messages.po")
    
    # Read existing content
    if po_path.exists():
        content = po_path.read_text(encoding='utf-8')
    else:
        content = ""
    
    # Generate new entries
    new_entries = []
    for en, es in sorted(ALL_TRANSLATIONS.items()):
        # Escape quotes
        en_escaped = en.replace('"', '\\"')
        es_escaped = es.replace('"', '\\"')
        
        entry = f'''msgid "{en_escaped}"
msgstr "{es_escaped}"

'''
        new_entries.append(entry)
    
    # Write back
    with open(po_path, 'a', encoding='utf-8') as f:
        f.write(''.join(new_entries))
    
    print(f"Added {len(ALL_TRANSLATIONS)} translations to {po_path}")

if __name__ == "__main__":
    update_po_file()
    print("\nDone! Now run: pybabel compile -d translations")
