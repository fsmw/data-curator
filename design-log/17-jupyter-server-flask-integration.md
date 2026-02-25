# Design Log 17 — Integración de Jupyter Server en Flask

## Background
La aplicación web Flask ya concentra búsqueda, análisis y Copilot Chat, pero no tiene una superficie de notebooks interactivos integrada en la misma UI.

## Problem
1. Falta un runtime notebook accesible desde la app para análisis exploratorio avanzado.
2. Necesitamos mantener un único punto de entrada (`:5000`) y no depender de navegación manual a puertos internos.
3. El kernel de Jupyter requiere WebSocket funcional para ejecutar celdas; un proxy HTTP incompleto rompe la experiencia.

## Questions and Answers
- Q: ¿Implementar iframe directo o proxy Flask completo?
  - A: **DECISIÓN (usuario):** implementar proxy Flask completo desde el inicio.
- Q: ¿Activar Jupyter siempre o permitir modo opt-in para no romper entornos sin Jupyter?
  - A: **DECISIÓN:** habilitar por configuración (`JUPYTER_ENABLE=1`) y exponer estado claro cuando esté deshabilitado.
- Q: ¿Multiusuario/JupyterHub entra en alcance?
  - A: No. Se mantiene alcance local/single-tenant.

## Design
1. Agregar `src/web/jupyter_manager.py` para lifecycle de subprocess (`start/stop/restart/health` + monitor).
2. Agregar `src/web/jupyter_proxy.py` como blueprint para proxy `/jupyter/*` (HTTP + ruta WS explícita).
3. Integrar manager/proxy en `create_app()` mediante `app.extensions["jupyter_manager"]`.
4. Agregar endpoints API de soporte (`/api/jupyter/health`, `/api/notebooks*`) y vista UI `/notebooks`.
5. Mantener comportamiento seguro por defecto: si Jupyter no está habilitado, endpoints devuelven estado controlado.

## Implementation Plan
- Fase A: Design log + wiring de configuración y lifecycle manager.
- Fase B: Proxy blueprint y registro en app.
- Fase C: UI + endpoints notebooks mínimos.
- Fase D: pruebas unitarias/integración focalizadas.

## Examples
- ✅ `GET /api/jupyter/health` retorna `{"status":"disabled"}` cuando `JUPYTER_ENABLE=0`.
- ✅ `/notebooks` renderiza iframe apuntando a `/jupyter/lab`.
- ❌ Arrancar dos procesos Jupyter por efecto del reloader sin control de lifecycle.

## Trade-offs
- Pros: integración consistente bajo el mismo origen y mejor UX operacional.
- Contras: proxy con WebSocket agrega complejidad técnica y sensibilidad a dependencias del servidor WSGI.

## Implementation Results
- ✅ Se implementó `src/web/jupyter_manager.py` con lifecycle (`start/stop/restart/is_alive/health_check`), polling de readiness y monitor de reinicio.
- ✅ Se implementó `src/web/jupyter_proxy.py` para proxy HTTP de `/jupyter/*` y registro en `create_app()`.
- ✅ Se integró wiring en `src/web/__init__.py`:
  - manager en `app.extensions["jupyter_manager"]`
  - activación por `JUPYTER_ENABLE=1`
  - shutdown hook via `atexit`.
- ✅ Se agregaron UI/API mínimas:
  - `GET /notebooks` (`src/web/routes.py`, `src/web/templates/notebooks.html`, `src/web/static/css/jupyter_embed.css`)
  - `/api/jupyter/health`, `/api/notebooks`, `/api/notebooks/create`, `/api/notebooks/provision`, `/api/notebooks/data-path` (`src/web/api/jupyter.py`).
- ✅ Se añadió opción de navegación en sidebar izquierdo (`Notebooks`) vía `src/const.py` + `src/web/templates/base.html`.
- ✅ Se agregó configuración base: `jupyter_config/jupyter_lab_config.py`.
- ✅ Se agregaron templates semilla y provisión automática:
  - `jupyter_config/notebook_templates/01_exploracion.ipynb`
  - `jupyter_config/notebook_templates/02_pygwalker_explorer.ipynb`
  - `jupyter_config/notebook_templates/README.md`
  - provisión en startup con `JupyterManager.provision_templates()`.
- ✅ Se implementó passthrough WebSocket real para kernels:
  - `register_jupyter_websocket_proxy(app)` en `src/web/jupyter_proxy.py`.
  - relay bidireccional `downstream <-> upstream` con `flask-sock` + `websocket-client`.
  - registro en app factory (`src/web/__init__.py`) junto al proxy HTTP.
- ✅ Se ajustó runtime de arranque web para compatibilidad WS cuando Jupyter está activo:
  - `src/web/__main__.py` usa `gevent.pywsgi.WSGIServer` + `WebSocketHandler` si `JUPYTER_ENABLE=1`.
  - fallback a `waitress` si dependencias gevent no están instaladas.
- ✅ Se actualizaron dependencias de proxy WS en `requirements.txt`:
  - `flask-sock`, `websocket-client`, `gevent`, `gevent-websocket`.
- ✅ Pruebas nuevas:
  - `tests/unit/test_jupyter_manager.py`
  - `tests/test_jupyter_integration_api.py`
- ✅ Cobertura de navegación:
  - `test_sidebar_contains_notebooks_option` en `tests/test_jupyter_integration_api.py`.
- ✅ Cobertura WS proxy:
  - `tests/unit/test_jupyter_proxy_websocket.py`.

Resultados de validación:
- `python -m py_compile src/web/jupyter_proxy.py src/web/__init__.py src/web/__main__.py tests/unit/test_jupyter_proxy_websocket.py` ✅
- `pytest -q tests/unit/test_jupyter_proxy_websocket.py tests/test_jupyter_integration_api.py tests/unit/test_jupyter_manager.py` → `10 passed` ✅
- ✅ Validación técnica ejecutada:
  - `python3 -m py_compile src/web/jupyter_manager.py src/web/jupyter_proxy.py src/web/api/jupyter.py src/web/routes.py src/web/__init__.py`
  - `.venv/bin/pytest -q tests/unit/test_jupyter_manager.py tests/test_jupyter_integration_api.py tests/test_api_auth_hardening.py tests/test_copilot_threads_api.py`
  - Resultado: `23 passed`.
- ⚠️ Pendiente de fase siguiente: passthrough WebSocket real para `/jupyter/api/kernels/*/channels` (hoy responde `501` en upgrade request).
