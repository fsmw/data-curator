# Design Log 14 — Technical Debt Remediation (Wave 2, Increment 1)

## Background
Wave 1 resolvió hardening de auth/RBAC y convergencia crítica de permisos/modelos. Quedó deuda estructural en modularización, migraciones de esquema y mantenimiento.

## Problem
1. La lógica SmoothCSV (cache SQL por dataset) está duplicada en `src/copilot_tools.py` y `src/web/api/datasets.py`.
2. El esquema de `DatasetCatalog` depende de `ALTER TABLE` en runtime en lugar de migraciones explícitas operables.
3. Se requiere mantener compatibilidad mientras se avanza por incrementos pequeños.

## Questions and Answers
- Q: ¿Hacemos una modularización completa en una sola iteración?
  - A: No. **DECISIÓN:** extraer utilidades compartidas de mayor duplicación primero (SmoothCSV cache), sin reorganizar todo el API.
- Q: ¿Se elimina de golpe toda migración en runtime?
  - A: **DECISIÓN:** definir migraciones formales por versión y comando CLI dedicado; mantener inicialización base no destructiva.
- Q: ¿Cómo minimizamos riesgo de regresión?
  - A: **DECISIÓN:** cambios acotados, reuso de funciones puras y verificación con pruebas focalizadas existentes.

## Design
1. Crear módulo `src/smoothcsv_cache.py` con helpers compartidos:
   - `get_smoothcsv_db_path(data_root)`
   - `ensure_smoothcsv_table(conn, dataset, sample_limit)`
   - `prepare_smoothcsv_sql(sql, limit)`
2. Reemplazar implementaciones duplicadas en `copilot_tools.py` y `web/api/datasets.py` por imports desde el módulo compartido.
3. Crear `src/dataset_catalog_migrations.py` con migraciones versionadas (`schema_migrations` + `MIGRATIONS`).
4. Exponer comando CLI `migrate-catalog` para aplicar migraciones de esquema de forma explícita.

## Implementation Plan
- Fase A: Extraer módulo compartido SmoothCSV y cablear consumidores.
- Fase B: Introducir migraciones formales para catálogo y comando CLI.
- Fase C: Ejecutar pruebas focalizadas y registrar resultados.

## Examples
- ✅ API datasets y Copilot SQL usan el mismo helper para preparar SQL con `LIMIT`.
- ✅ `curate migrate-catalog` aplica migraciones pendientes y reporta resumen.
- ❌ Mantener lógica de mapeo/cache SQL duplicada en dos módulos.

## Trade-offs
- Pros: menor duplicación, mejor mantenibilidad, camino explícito para evolución de esquema.
- Contras: introduce más archivos/módulos y requiere ejecutar comando de migración en despliegues legacy.

## Implementation Results
- Se creó `src/smoothcsv_cache.py` para centralizar cache SQL (`get_smoothcsv_db_path`, `ensure_smoothcsv_table`, `prepare_smoothcsv_sql`) y se eliminó duplicación en `src/copilot_tools.py` y `src/web/api/datasets.py`.
- Se creó `src/dataset_catalog_migrations.py` con migraciones versionadas y tabla `schema_migrations`.
- Se agregó comando `migrate-catalog` en `src/cli.py` para ejecutar migraciones de catálogo fuera de runtime.
- En `src/dataset_catalog.py` se reemplazó la captura genérica en `_extract_metadata` por errores tipados de I/O y parseo CSV.
- Se eliminaron capturas genéricas restantes en `src/dataset_catalog.py` (`index_dataset`, `get_preview_data`) usando excepciones tipadas.
- En `src/web/api/visualization.py` se reemplazaron capturas genéricas por `VISUALIZATION_API_ERRORS` y se tipificó un `except` interno en autodetección de categorías.
- Se extrajo tipado semántico/encodings a `src/web/api/visualization_types.py` (`detect_semantic_type`, `get_semantic_hints`, `infer_field_type`, `auto_detect_encodings`) para reducir tamaño y acoplamiento de `visualization.py`.
- En `src/web/api/download.py` se eliminaron capturas genéricas y se centralizó manejo tipado con `DOWNLOAD_API_ERRORS`.
- En `src/web/api/search.py` se eliminaron capturas genéricas y se centralizó manejo tipado con `SEARCH_API_ERRORS`.
- En `src/web/api/analysis.py` se eliminaron capturas genéricas y se centralizó manejo tipado con `ANALYSIS_API_ERRORS`.
- Se retiró el registro de `data_formulator` del blueprint API (`src/web/api/__init__.py`) por falta de uso activo en frontend/rutas internas del proyecto.
- En `src/web/api/agent.py` se reemplazaron capturas genéricas por `AGENT_API_ERRORS` y se endureció parseo JSON con `request.get_json() or {}` para evitar fallos por payload vacío.
- En `src/web/api/compare.py` se reemplazó captura genérica por `COMPARE_API_ERRORS` y se tipificó el fallback de `year_range`.
- En `src/web/api/data_formulator.py` se reemplazaron capturas genéricas por `DATA_FORMULATOR_API_ERRORS`; el parseo de `raw_data` ahora captura errores tipados de JSON, y el borrado de archivo captura `OSError`.
- En `src/dataset_catalog.py` se añadió ejecución de migraciones formales al arranque (`migrate_dataset_catalog`) antes de crear índices, para mantener compatibilidad con catálogos legacy y evitar fallos por columnas faltantes.
- Se corrigió compatibilidad con prefijo base (`/misesdata`) en navegación PyGWalker: `visualization_pygwalker.html`, `visualization_canvas.html` y `copilot_chat.html` dejaron de usar rutas hardcodeadas `/visualizepg*` y ahora usan `apiUrl(...)`.
- En `src/copilot_tools.py::list_local_datasets` se redujo payload (sin `columns`), se agregó `returned_count/is_truncated`, y `total_cataloged` ahora refleja conteo real para evitar respuestas ambiguas al “contar datasets”.
- En `src/copilot_agent.py` se añadió guard de bucles de herramientas (límite de llamadas por respuesta + reutilización de cache en invocaciones repetidas) para mitigar timeouts por tool-calling repetitivo.
- Verificación ejecutada: `python3 -m py_compile` sobre módulos modificados ✅.
- Verificación ejecutada: `.venv/bin/pytest -q tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py` ✅ (**17 passed**).
