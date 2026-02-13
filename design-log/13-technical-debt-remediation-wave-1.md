# Design Log 13 — Technical Debt Remediation (Wave 1)

## Background
El informe de deuda técnica identificó riesgos altos en tres áreas: autenticación inconsistente en APIs, deriva entre gobernanza de modelos en UI/API/backend, y dualidad ORM/catalog para permisos.

## Problem
1. Endpoints sensibles sin `@login_required` permitían acceso no autenticado a datos y operaciones de edición.
2. La allowlist de modelos no estaba alineada entre vista, endpoint `/llm/models` y fallbacks del agente.
3. `PermissionService` seguía validando permisos desde ORM (`Dataset.can_access`) en vez de `DatasetCatalog`, contradiciendo el plan source-of-truth.

## Questions and Answers
- Q: ¿Corregimos toda la deuda en una sola iteración?
  - A: No. **DECISIÓN:** ejecutar en olas priorizadas; Wave 1 aborda seguridad y convergencia de permisos.
- Q: ¿Qué capa define el acceso a datasets?
  - A: **DECISIÓN:** `DatasetCatalog` es la autoridad para `can_read/can_write/can_admin/grant/revoke`.
- Q: ¿Qué modelos quedan habilitados para Copilot Chat?
  - A: **DECISIÓN:** `gpt-5-mini`, `claude-haiku-4.5`, `gemini-3-flash-preview`, `gpt-4o`, `gpt-4.1`.

## Design
1. Proteger rutas críticas (`datasets` avanzadas y chat Copilot) con `@login_required`.
2. Aplicar chequeos de acceso por dataset usando `catalog.can_access(...)` en endpoints que leen/escriben datos.
3. Alinear `/llm/models` y fallbacks backend con la allowlist aprobada.
4. Completar métodos RBAC en `DatasetCatalog` (owner/public/shared) y redirigir `PermissionService` a catálogo.

## Implementation Plan
- Fase A: Hardening de autenticación/autorización en endpoints.
- Fase B: Unificación de allowlist de modelos en API y agente.
- Fase C: Puente de `PermissionService` hacia catálogo.
- Fase D: Pruebas y seguimiento de deuda residual (migraciones, módulos grandes, manejo de excepciones).

## Examples
- ✅ `GET /api/datasets/<id>/fields` valida sesión y ownership por catálogo.
- ✅ `POST /api/edit/sql/query` valida sesión y acceso de lectura al dataset.
- ❌ Exponer versiones/campos/fork de datasets sin sesión.

## Trade-offs
- Pros: menor superficie de ataque y semántica de permisos más consistente.
- Contras: cambios de comportamiento para clientes no autenticados; parte de deuda estructural (modularización, manejo fino de excepciones) queda para Wave 2.

## Implementation Results
- Se inició Wave 1 con cambios de autenticación, control de acceso por catálogo, unificación de modelos permitidos y refactor inicial de `PermissionService` hacia `DatasetCatalog`.
- Se extendió el hardening: endpoints de preview/export/refresh/redownload y capacidades Copilot (`health/models/cache`) ahora requieren sesión autenticada.
- Se mitigó un riesgo crítico en `redownload`: la ruta ya no elimina archivos/dataset antes de responder `501`.
- Se consolidó la allowlist backend en `src/model_governance.py` y se reutiliza en API y agente para evitar deriva.
- Se completó la convergencia del status page a catálogo: `src/web/routes.py` ahora usa `DatasetCatalog.list_accessible_datasets(...)` y `PermissionService.get_user_datasets` dejó de usar consultas ORM directas.
- Se eliminó duplicación de endpoint `GET /api/datasets/<id>` para mantener una sola ruta canónica.
- Se endurecieron endpoints de análisis y comparación con auth + RBAC (`/api/analyze/*`, `/api/compare/data`) y se registró explícitamente el módulo `compare` en el blueprint API.
- Se endurecieron endpoints de búsqueda/descarga con auth (`/api/search`, `/api/download/start`, `/api/progress/stream`, `/api/progress/poll`).
- Se redujo deuda de SQLAlchemy legacy en puntos críticos (`db.session.get(...)` en `web/__init__.py`, `services`, `admin_views`).
- Se avanzó en normalización de imports hacia `src.*` en módulos API críticos (datasets/copilot/analysis/compare/search/download/data_formulator).
- Se corrigió robustez de arranque sin SDK Copilot en `src/copilot_agent.py` (fallback de tipos para evitar `NameError` en import).
- Verificación focalizada ejecutada: `tests/test_api_auth_hardening.py` + `tests/test_copilot_threads_api.py` (**17 passed**).
- Wave 2 (parcial): en `src/web/api/datasets.py` se reemplazaron varios `except Exception` por errores tipados en rutas de lectura/metadata/tags/chat/historial/tópicos, y en `src/web/api/arancel.py` se tipificaron errores de carga de CSV (evitando capturas genéricas en rutas críticas).
- Se encapsuló la resolución de rutas de tópicos CSV en helper dedicado (`_build_topic_csv_path`) para mejorar mantenibilidad y reducir duplicación.
- Verificación posterior a Wave 2 parcial: `tests/test_api_auth_hardening.py` + `tests/test_copilot_threads_api.py` (**17 passed**).
- Pendiente en siguientes olas: modularización de archivos grandes, reducción sistemática de `except Exception`, y migración formal de esquema fuera de runtime.
