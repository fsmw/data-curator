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
- Verificación ejecutada: `python3 -m py_compile` sobre módulos modificados ✅.
- Verificación pendiente: pruebas `pytest` bloqueadas localmente por dependencias ausentes (`click`, `pytest`) en el entorno.
