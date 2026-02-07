# Cliente web y estado de fuentes de datos

**Fecha:** 6 de febrero de 2026  
**Alcance:** Estudio del cliente web y validación de fuentes operativas para búsqueda y descarga.

---

## 1. Resumen del cliente web

### 1.1 Stack y estructura

- **Backend:** Flask (blueprints `ui_bp` y `api_bp`).
- **Frontend:** Plantillas Jinja2 + Alpine.js (en `search.html`), Bootstrap 5, iconos Bootstrap Icons.
- **Rutas UI:** Definidas en `src/web/routes.py`.
- **Rutas API:** En `src/web/api/*` (search, download, datasets, compare, copilot, etc.).

### 1.2 Páginas principales

| Ruta | Plantilla | Descripción |
|------|-----------|-------------|
| `/`, `/status` | status.html | Dashboard con estadísticas y actividad reciente (DatasetCatalog). |
| `/search` | search.html | Búsqueda de indicadores (local + remota), filtro por fuente, descarga y preview. |
| `/browse/local`, `/browse_local` | browse_local.html | Navegación de datasets locales. |
| `/browse/available` | Redirige a `/search` | Búsqueda unificada. |
| `/compare` | compare.html | Comparación/correlación de datasets. |
| `/copilot_chat` | copilot_chat.html | Chat con Copilot (IA). |
| `/visualizepg` | visualization_pygwalker.html | PyGWalker para exploración visual. |
| `/help` | help.html | Ayuda y atajos. |

### 1.3 Flujo de búsqueda y descarga (web)

1. **Búsqueda** (`GET /api/search?q=...&source=...`):
   - Si hay `query`: usa `DynamicSearcher`, que combina:
     - **Local:** `IndicatorSearcher` (indicators.yaml) y filtros por topic/source.
     - **Remoto:** OWID Search API, OECD dataflows (o lista curada), World Bank Indicators API.
   - Resultados unificados con `id`, `indicator`, `source`, `slug`, `downloaded` (vía DatasetCatalog), etc.

2. **Descarga** (`POST /api/download/start`):
   - Body: `id`, `source`, `indicator`, y campos por fuente (`slug`, `dataset`, `indicator_code`, etc.).
   - Soporta indicadores **locales** (indicators.yaml) e indicadores **remotos** (`remote: true`).
   - Para cada fuente se construyen `fetch_params` y se llama a `DataIngestionManager.ingest(source, **fetch_params)`.
   - Luego: limpieza (`DataCleaner`), metadata (`MetadataGenerator`), opcional `AIPackager` (OWID), e indexación en `DatasetCatalog`.

3. **Preview (sin guardar):**
   - OWID: `/api/chart/export-png?slug=...` (proxy al PNG de OWID).
   - World Bank: `/api/remote/worldbank/preview?indicator=...`.
   - OECD: `/api/remote/oecd/preview?dataset=...&indicator=...`.

### 1.4 Navegación y constantes

- `NAV_ITEMS` en `src/const.py`: Status, Search, Browse Local, Visualización, Compare, AI Chat, Help.
- Todas las páginas reciben `base_context(active, title, subtitle)` con `nav_items` y `active` para el menú.

---

## 2. Fuentes de datos: implementación en código

Todas las fuentes están **registradas** en `DataIngestionManager.sources` y el **download API** las contempla:

| Fuente   | Clase en `ingestion.py` | Búsqueda (DynamicSearcher)      | Descarga (download API) |
|----------|-------------------------|----------------------------------|--------------------------|
| OWID     | OWIDSource              | OWIDSearcher (API search)        | Sí (slug)                |
| ILOSTAT  | ILOSTATSource           | Solo local (indicators.yaml)    | Sí (indicator_code)      |
| OECD     | OECDSource              | OECDSearcher (dataflows + curado)| Sí (dataset + indicator_code) |
| IMF      | IMFSource               | Solo local                       | Sí (database + indicator_code) |
| World Bank | WorldBankSource       | WorldBankSearcher (API)         | Sí (indicator_code)      |
| ECLAC    | ECLACSource             | Solo local                       | Sí (table/code)           |

---

## 3. Validación realizada (descarga real)

Se ejecutó `python validate_sources.py` desde la raíz del proyecto, que llama a `DataIngestionManager.ingest()` para cada fuente con indicadores conocidos.

### 3.1 Resultados por fuente

| Fuente      | Estado        | Registros | Notas |
|-------------|---------------|-----------|--------|
| **OWID**    | **Operativa** | 189       | `gdp-per-capita-worldbank`: CSV descargado correctamente. |
| **World Bank** | **Operativa** | 37     | `SI.POV.GINI`: API responde y devuelve datos. |
| **ILOSTAT** | No operativa  | 0        | 404 en la URL de SDMX (path o dataflow incorrectos). |
| **OECD**    | No operativa  | 0        | 404 en `sdmx.oecd.org/public/rest/data/REV/...` (formato/key posiblemente desactualizado). |
| **IMF**     | No verificada | 0        | Timeout de conexión (30 s); puede ser red/firewall o servicio lento. |
| **ECLAC**   | No operativa  | 0        | Resolución DNS fallida para `data.cepal.org`; endpoint o host pueden haber cambiado. |

### 3.2 Búsqueda (sin descargar)

- **OWID (remoto):** Operativa; la búsqueda devuelve ~100 resultados desde la API de OWID.
- **World Bank (remoto):** Operativa; la API de indicadores devuelve resultados.
- **OECD (remoto):** La URL de dataflows (`stats.oecd.org/SDMX-JSON/dataflow`) devuelve 404; el fallback es una lista curada por palabras clave (p. ej. "tax", "gdp"), por lo que la búsqueda por término puede devolver pocos resultados pero no desde el API público actual.

---

## 4. Resumen ejecutivo: fuentes operativas

- **Búsqueda:**  
  - **Operativas:** OWID (remoto), World Bank (remoto).  
  - **Parcial:** OECD (solo lista curada en `dynamic_search`).  
  - **Solo local:** ILOSTAT, IMF, ECLAC (indicators.yaml).

- **Descarga (ingesta real con datos):**  
  - **Operativas:** **OWID**, **World Bank**.  
  - **No operativas con la configuración actual:** ILOSTAT (404), OECD (404), ECLAC (DNS/endpoint).  
  - **No verificada por timeout:** IMF.

Para reproducir la validación:

```bash
python validate_sources.py
```

---

## 5. Recomendaciones

1. **ILOSTAT:** Revisar documentación actual de la API SDMX (URL base, dataflow, estructura de la petición).
2. **OECD:** Comprobar la API actual en sdmx.oecd.org (paths, keys y formato de parámetros).
3. **IMF:** Reintentar en otra red o aumentar timeout; confirmar URL y códigos de base/indicador.
4. **ECLAC:** Verificar el host y la API actual de CEPAL (puede ser otro subdominio o estructura de `/api`).
5. **Cliente web:** Los endpoints de búsqueda y descarga están correctamente enlazados; las fuentes que fallan lo hacen en el backend de ingesta (APIs externas), no en la UI.
