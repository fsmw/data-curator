# Design Log 16 — Run Python Analysis (Phase 3 Foundation)

## Background
Fase 1 y Fase 2 ya agregaron preparación de panel y transformaciones económicas, pero Fase 3 requiere análisis estadístico y visualización que no caben bien en wrappers SQL únicamente.

## Problem
1. Falta una capa de ejecución Python controlada para análisis avanzados (`correlation_analyzer`, `regression_engine`, visualizaciones).
2. Crear cada tool avanzada sin una base común duplicaría lógica y aumentaría deuda técnica.
3. Debemos permitir flexibilidad analítica sin abrir ejecución insegura o irrestricta.

## Questions and Answers
- Q: ¿Implementamos tools avanzadas directamente sin runtime común?
  - A: No. **DECISIÓN:** crear primero `run_python_analysis` como capa base de Fase 3.
- Q: ¿Permitir `exec` arbitrario?
  - A: **DECISIÓN:** ejecución restringida por validación AST (sin `import`, sin acceso a builtins peligrosos).
- Q: ¿Qué contexto recibe el script?
  - A: **DECISIÓN:** DataFrames cargados desde `dataset_ids` (`dfs` + `df`), más `pd` y `np`.

## Design
1. Nuevo tool `run_python_analysis` en `src/copilot_tools.py`.
2. Entradas:
   - `dataset_ids: List[int]`
   - `python_code: str`
   - `preview_rows: int` (default 25)
3. Entorno de ejecución:
   - Variables: `dfs`, `df`, `pd`, `np`
   - Builtins permitidos acotados (`len`, `min`, `max`, `sum`, `abs`, `round`, `sorted`, `range`, `print`)
4. Salidas:
   - `stdout`
   - `result_df_preview` cuando exista `result_df`
   - `result` serializable cuando exista variable `result`
5. Guardrails:
   - Rechazar AST con `Import`, `ImportFrom`, `Global`, `Nonlocal`.
   - Errores explícitos y sin silencios.

## Implementation Plan
- Fase A: helper de validación AST segura.
- Fase B: implementación de `run_python_analysis`.
- Fase C: registro en `TOOL_REGISTRY`.
- Fase D: smoke test + regresión focalizada.

## Examples
- ✅ Script que calcula correlación en `df` y deja `result = {"corr": ...}`.
- ✅ Script que construye `result_df` y retorna preview.
- ❌ Script con `import os` o acceso a runtime externo.

## Trade-offs
- Pros: base reusable para Fase 3-5 y menor duplicación.
- Contras: primera versión no soporta todo el ecosistema científico ni artefactos complejos (se extenderá por fases).

## Implementation Results
- ✅ Fase A-B-C completadas en `src/copilot_tools.py`:
  - helper `_validate_safe_analysis_code(...)` con guardrails AST (bloquea `Import`, `ImportFrom`, `Global`, `Nonlocal`)
  - tool `run_python_analysis(...)` con runtime restringido y builtins permitidos
  - registro en `TOOL_REGISTRY` con contrato `dataset_ids`, `python_code`, `preview_rows`
- ✅ Smoke test manual ejecutado:
  - carga de dataset local por ID
  - ejecución de script con `result` + `result_df`
  - retorno correcto de `status=success`, `stdout` y `result_df_preview`
- ✅ Regresión focalizada ejecutada:
  - `.venv/bin/pytest -q tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `17 passed`
- ✅ Extensión MVP de Fase 3:
  - tool `correlation_analyzer(...)` agregado en `src/copilot_tools.py` sobre `run_python_analysis`
  - métodos implementados: `pooled`, `within`, `rolling`
  - salida estructurada: `correlation_matrix`, `top_pairs`, `interpretation`, `warnings`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_correlation_analyzer.py` (pooled + rolling)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `19 passed`
- ✅ Segunda extensión MVP de Fase 3:
  - tool `group_classifier(...)` agregado en `src/copilot_tools.py`
  - clasificación soportada: `region`, `income`, `oecd`, `population_band`
  - fallback por metadata de regiones configuradas + detección de columna entidad
  - salida estructurada: grupos agregados, cobertura por grupo, warnings de clasificación desconocida
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_group_classifier.py` (region, income, metadata faltante)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `22 passed`
- ✅ Tercera extensión MVP de Fase 3:
  - tool `regression_engine(...)` agregado en `src/copilot_tools.py`
  - modelos soportados: `pooled`, `fe_entity`, `fe_two_way`
  - implementación de OLS por álgebra lineal con `numpy.linalg.lstsq` dentro de `run_python_analysis`
  - salida estructurada: `coefficients`, `r_squared`, `adj_r_squared`, `n_obs`, `warnings`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_regression_engine.py` (pooled, fe_two_way, validación de modelo inválido)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `25 passed`
- ✅ Cuarta extensión MVP de Fase 3:
  - tool `smart_visualizer(...)` agregado en `src/copilot_tools.py`
  - tipos soportados: `line`, `scatter`, `heatmap`
  - salida reproducible: `chart_spec` (Vega-Lite) + `reproducible_config`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_smart_visualizer.py` (line, heatmap, validación de tipo inválido)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `28 passed`
- ✅ Quinta extensión (orquestación):
  - tool `analysis_planner(...)` agregado en `src/copilot_tools.py`
  - genera plan secuencial tool-aware según objetivo y disponibilidad de `dataset_ids`
  - sugiere cadena de ejecución para `data_profiler`, `correlation_analyzer`, `regression_engine`, `group_classifier`, `smart_visualizer`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_analysis_planner.py` (con dataset, sin dataset, objetivo vacío)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `31 passed`
- ✅ Sexta extensión (caveats automáticos):
  - tool `caveat_engine(...)` agregado en `src/copilot_tools.py`
  - reglas implementadas: `small_sample`, `high_missingness`, `high_imputation`, `geographic_concentration`, `short_time_span`
  - salida estructurada por caveat con severidad y evidencia
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_caveat_engine.py` (detección múltiple y escenario de caveats mínimos)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `33 passed`
- ✅ Séptima extensión (robustez):
  - tool `robustness_checker(...)` agregado en `src/copilot_tools.py`
  - compara coeficiente clave entre especificaciones (`pooled`, `fe_entity`, `fe_two_way`) y reporta estabilidad
  - produce `results` por modelo + bloque `stability` con rango absoluto/relativo e indicador `is_stable`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_robustness_checker.py` (caso exitoso + validación de `key_variable` inválida)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `35 passed`
- ✅ Octava extensión (Fase 5 opcional iniciada):
  - tool `cross_source_validator(...)` agregado en `src/copilot_tools.py`
  - compara datasets por solapamiento `entity_key/year` y reporta `correlation` + `mean_abs_diff` por par
  - agrega warnings por bajo solapamiento o validación limitada en una sola fuente
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_cross_source_validator.py` (caso exitoso + validación de mínimo de datasets)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_cross_source_validator.py tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `37 passed`
- ✅ Novena extensión (Fase 5 opcional):
  - tool `assumption_checker(...)` agregado en `src/copilot_tools.py`
  - chequeos implementados: `sample_size`, `multicollinearity`, `residual_normality_proxy`, `heteroskedasticity_proxy`
  - cálculo sobre baseline OLS usando `run_python_analysis` y salida estructurada con evidencia por supuesto
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_assumption_checker.py` (caso exitoso + validación de columnas faltantes)
  - ajuste aplicado: remover uso de builtins no permitidos (`float`/`int`) dentro del script dinámico para compatibilidad con sandbox
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_assumption_checker.py tests/unit/test_cross_source_validator.py tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `39 passed`
- ✅ Décima extensión (Fase 5 opcional):
  - tool `trend_analyzer(...)` agregado en `src/copilot_tools.py`
  - cálculo de tendencia lineal global por año (`slope`, `direction`, `change_pct`) + mayor salto anual
  - desagregación por entidad con filtros `min_points` y `top_entities`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_trend_analyzer.py` (caso exitoso + fallback de `value_column` inválida al inferido)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_trend_analyzer.py tests/unit/test_assumption_checker.py tests/unit/test_cross_source_validator.py tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `41 passed`
- ✅ Undécima extensión (Fase 5 opcional):
  - tool `causality_tester(...)` agregado en `src/copilot_tools.py`
  - chequeos implementados: lead-lag `x(t-lag) -> y(t)` + placebo reverse `y(t-lag) -> x(t)`
  - señal estructurada con `best_lag`, `best_corr`, `placebo_corr_same_lag`, `passes_placebo`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_causality_tester.py` (caso exitoso + validación de columnas faltantes)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_causality_tester.py tests/unit/test_trend_analyzer.py tests/unit/test_assumption_checker.py tests/unit/test_cross_source_validator.py tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `43 passed`
- ✅ Duodécima extensión (Fase 5 opcional):
  - tool `dimensionality_reducer(...)` agregado en `src/copilot_tools.py`
  - reducción tipo PCA implementada con `numpy` (estandarización, autovalores/autovectores, varianza explicada)
  - salida estructurada: `explained_variance_ratio`, `component_loadings`, `scores_preview`
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_dimensionality_reducer.py` (caso exitoso + validación por columnas no numéricas)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_dimensionality_reducer.py tests/unit/test_causality_tester.py tests/unit/test_trend_analyzer.py tests/unit/test_assumption_checker.py tests/unit/test_cross_source_validator.py tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `45 passed`
- ✅ Décima tercera extensión (Fase 5 opcional):
  - tool `convergence_analyzer(...)` agregado en `src/copilot_tools.py`
  - métricas implementadas: `beta_convergence` (regresión growth ~ ln(initial)) y `sigma_convergence` (pendiente de dispersión log anual)
  - salida estructurada con periodo, muestra, señales de convergencia y warnings
  - registro en `TOOL_REGISTRY` completado
- ✅ Prueba dedicada:
  - `tests/unit/test_convergence_analyzer.py` (caso exitoso + validación de periodo inválido)
  - validación conjunta: `python3 -m py_compile src/copilot_tools.py` + `.venv/bin/pytest -q tests/unit/test_convergence_analyzer.py tests/unit/test_dimensionality_reducer.py tests/unit/test_causality_tester.py tests/unit/test_trend_analyzer.py tests/unit/test_assumption_checker.py tests/unit/test_cross_source_validator.py tests/unit/test_robustness_checker.py tests/unit/test_caveat_engine.py tests/unit/test_analysis_planner.py tests/unit/test_smart_visualizer.py tests/unit/test_regression_engine.py tests/unit/test_group_classifier.py tests/unit/test_correlation_analyzer.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `47 passed`
- ✅ Cierre de brecha de pruebas (integración + guardrails):
  - `tests/unit/test_run_python_analysis_guardrails.py` agregado:
    - valida bloqueo AST de `import`
    - valida restricción de builtins inseguros (`__import__`)
  - `tests/unit/test_analysis_flow_integration.py` agregado:
    - escenario E2E con invocación encadenada de tools analíticas principales
    - asegura compatibilidad entre planner, análisis estadístico, robustez y tools de Fase 5
  - validación conjunta extendida:
    - `python3 -m py_compile src/copilot_tools.py`
    - `.venv/bin/pytest -q` sobre suites focales + nuevas suites de integración/guardrails
    - Resultado: `50 passed`
- ✅ Regresión funcional Copilot Chat + cobertura MCP de tools:
  - `tests/test_copilot_chat_tool_telemetry.py` agregado:
    - mock de agente en `/api/copilot/stream`
    - valida emisión de eventos `fallback_tool_use`, `tool_use`, `tool_result` y `tools_called` en chunk final
  - `tests/unit/test_tool_registry_mcp_smoke.py` agregado:
    - valida que `list_available_tools` cubre todo `TOOL_REGISTRY`
    - smoke del dispatcher `execute_tool` para todas las tools registradas
  - validación conjunta focal:
    - `.venv/bin/pytest -q` con suites nuevas + suites existentes críticas
    - Resultado: `53 passed`
