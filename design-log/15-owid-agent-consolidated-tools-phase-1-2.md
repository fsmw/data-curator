# Design Log 15 — OWID Agent Consolidated Tools (Phase 1 + Phase 2)

## Background
El agente actual resuelve descubrimiento/ingesta y consultas básicas, pero no tiene flujo robusto para análisis de panel ni transformaciones económicas sobre múltiples datasets.

## Problem
1. Cruces entre datasets dependen de SQL manual y de nombres de país inconsistentes.
2. No existe diagnóstico de cobertura previo al merge para evitar sesgos silenciosos.
3. Falta una base operativa para Fase 2 (transformaciones económicas y manejo de missing).

## Questions and Answers
- Q: ¿Implementamos Fase 1 y Fase 2 completas en una sola iteración?
  - A: No. **DECISIÓN:** implementar incrementalmente, empezando por el núcleo de Fase 1 con interfaces compatibles para expandir Fase 2.
- Q: ¿Dónde viven las nuevas tools?
  - A: **DECISIÓN:** integrar primero en `src/copilot_tools.py` para minimizar riesgo y aprovechar `TOOL_REGISTRY` actual.
- Q: ¿Cómo evitar conclusiones engañosas por baja cobertura?
  - A: **DECISIÓN:** `coverage_analyzer` obligatorio como diagnóstico explícito con warnings de representatividad.

## Design
1. Agregar `country_harmonizer` para normalizar entidad país y clasificar agregados no-país.
2. Agregar `coverage_analyzer` para medir intersección país-año entre datasets y detectar sesgo.
3. Mantener outputs estructurados para futura composición con `panel_builder`.
4. Diseñar las firmas de Fase 2 (`economic_transformer`, `missing_data_handler`, `data_profiler`) sobre el mismo contrato de metadatos.

## Implementation Plan
- Fase A: Helpers internos de carga/detección de columnas de entidad/año.
- Fase B: Tool `country_harmonizer` + registro en `TOOL_REGISTRY`.
- Fase C: Tool `coverage_analyzer` + registro en `TOOL_REGISTRY`.
- Fase D: Validación técnica (`py_compile` + pruebas focalizadas existentes).

## Examples
- ✅ `country_harmonizer(dataset_id=42)` retorna `iso3` sugerido, filas no-país y no reconocidas.
- ✅ `coverage_analyzer(dataset_ids=[10, 42])` retorna intersección usable y cobertura por dataset.
- ❌ Ejecutar panel joins sin reporte explícito de pérdidas/cobertura.

## Trade-offs
- Pros: desbloquea flujo analítico incremental sin refactor masivo.
- Contras: primera versión usa heurísticas simples para país/ISO3 y no resuelve aún casos históricos complejos.

## Implementation Results
- Se agregaron helpers de armonización y detección de columnas en `src/copilot_tools.py` (`_detect_entity_column`, `_detect_year_column`, `_harmonize_entity`, `_load_catalog_dataset_frame`).
- Se implementó tool `country_harmonizer` (normalización de entidad, clasificación no-país, reporte de match y opción `persist`).
- Se implementó tool `coverage_analyzer` (intersección país/año por datasets, overlap ratio, dataset limitante, warnings).
- Se implementó tool `panel_builder` (merge multi-dataset por `entity_key, year`, soporte `join_type`, `lags`, filtro temporal, `countries_only`, reporte y persistencia opcional).
- Se implementó tool `economic_transformer` con operaciones iniciales (`lag`, `lead`, `growth_rate`, `first_diff`, `moving_avg`, `log`, `zscore`, `min_max`) y persistencia opcional.
- Se implementó tool `missing_data_handler` con estrategias (`linear`, `forward_fill`, `backward_fill`, `drop`, `regional_mean`) y marca `_is_imputed`.
- Se implementó tool `data_profiler` para diagnóstico de calidad/cobertura (global, por columna, por país, por año).
- Se registraron ambas tools en `TOOL_REGISTRY` para exposición automática en `copilot_agent.py`.
- Se registró `panel_builder` en `TOOL_REGISTRY` para exposición automática en `copilot_agent.py`.
- Se registraron `economic_transformer`, `missing_data_handler` y `data_profiler` en `TOOL_REGISTRY`.
- Verificación ejecutada: `python3 -m py_compile src/copilot_tools.py src/copilot_agent.py` ✅.
- Smoke test ejecutado con `.venv/bin/python` invocando tools nuevas ✅.
- Verificación de regresión ejecutada: `.venv/bin/pytest -q tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py` ✅ (**17 passed**).
