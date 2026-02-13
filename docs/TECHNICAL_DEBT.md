# Technical Debt Report & Refactoring Plan

**Date**: 2026-02-03
**Scope**: `src/` directory (Core logic, Web, CLI, Ingestion)
**Status**: Analysis Complete

## Executive Summary

The project has a solid functional foundation but exhibits significant "growing pains" common in rapid prototypes moving to production. The primary sources of technical debt are the **monolithic web controller** (`routes.py`), **lack of automated testing**, and **inconsistent error handling/logging**. Addressing these now will prevent velocity slowdowns in future phases.

---

## 1. Architecture & Design 🔴 (High Severity)

### 1.1 The "God Controller" (`src/web/routes.py`)
*   **Issue**: The file `src/web/routes.py` is ~1,900 lines long and handles mixed responsibilities:
    *   Routing (Flask)
    *   Data Transformation (cleaning NaNs, parsing JSON)
    *   Business Logic (Search orchestration)
    *   View Logic (Context building)
*   **Impact**: Hard to maintain, test, and read. High risk of breaking features when modifying unrelated endpoints.
*   **Recommendation**:
    *   Refactor into Blueprints: `src/web/routes/api.py`, `src/web/routes/views.py`.
    *   Move transformation logic (like `clean_nan_recursive`) to `src/utils/serialization.py`.
    *   Move business logic to service layer (e.g., `src/services/catalog_service.py`).

### 1.2 Leaky Abstractions in Ingestion
*   **Issue**: `src/ingestion.py` defines a `DataSource` interface, but implementations (like `OWIDSource` vs `OECDSource`) have inconsistent instantiation and parameter handling.
*   **Impact**: Adding a new source requires changes in multiple places (`cli.py`, `routes.py`).
*   **Recommendation**: strict Factory Pattern for DataSource creation and a unified `fetch` interface that abstracts underlying API differences more rigorously.

---

## 2. Code Quality & Standards 🟠 (Medium Severity)

### 2.1 "Print" Logging
*   **Issue**: The application relies almost exclusively on `print()` for logging (in `ingestion.py`, `cli.py`, `routes.py`).
*   **Impact**:
    *   No timestamps or log levels (INFO vs ERROR).
    *   Cannot pipe logs to files/cloud aggregators easily.
    *   Debug prints clutter production output.
*   **Recommendation**: Implement a centralized `src/logger.py` using Python's `logging` module. Replace all `print()` calls with `logger.info()`, `logger.error()`, etc.

### 2.2 Hardcoded Constants
*   **Issue**:
    *   Country mappings (ISO codes) are hardcoded inside `OECDSource` and `IMFSource` classes in `ingestion.py`.
    *   List of "default countries" (ARG, BRA, etc.) is repeated in `ingestion.py` and `cli.py`.
*   **Impact**: Updating a country code requires editing multiple source files.
*   **Recommendation**: Move all constants (Country mappings, default lists) to `src/const.py` or `config.yaml`.

### 2.3 Error Handling
*   **Issue**: Widespread use of `except Exception as e:` which prints the error and returns empty data or 500 responses.
*   **Impact**: Swallows critical bugs; makes debugging difficult; UI fails silently or generically.
*   **Recommendation**:
    *   Create specific exception classes (e.g., `DataSourceError`, `ParsingError`).
    *   Catch specific exceptions where possible.
    *   Log full stack traces (via `logger.exception`) only for unexpected errors.

---

## 3. Testing & Reliability 🔴 (High Severity)

### 3.1 Missing Unit Tests
*   **Issue**: `tests/` contains scripts (`test_api.py`, `test_web.py`) that act as manual or E2E smoke tests. There are **zero** true unit tests for:
    *   `DataCleaner` (Complex logic, prone to regressions).
    *   `MetadataGenerator`.
    *   individual `DataSource` parsers.
*   **Impact**: High risk of regressions when refactoring code.
*   **Recommendation**:
    *   Install `pytest`.
    *   Write pure unit tests for `src/cleaning.py` and `src/ingestion.py` (mocking network requests).

### 3.2 Dependency Management
*   **Issue**: `src/analysis.py` contains `try-except` blocks for importing `statsmodels` and `linearmodels`.
*   **Impact**: Logic is obscured by import guards; unclear if these are hard or soft dependencies.
*   **Recommendation**: Define explicit extras in `pyproject.toml` or `requirements.txt` (e.g., `pip install .[analysis]`) and remove import guards if the core app depends on them.

---

## 4. Prioritized Remediation Plan

### Phase A: Architecture & Stability (Immediate)
1.  [ ] **Setup Logging**: Replace `print` with `logger` throughout `src/`.
2.  [ ] **Split generic utils**: Extract static helpers (cleaning, serialization) from `routes.py` to `src/utils`.
3.  [ ] **Extract API Routes**: Move `/api/*` endpoints from `routes.py` to `src/web/api/`.

### Phase B: Reliability (Short Term)
1.  [ ] **Scaffold Pytest**: Create `tests/unit` and write first tests for `cleaning.py`.
2.  [ ] **Config Consistency**: Move country codes/mappings to `src/const.py`.

### Phase C: Refactoring (Medium Term)
1.  [ ] **Modularize Routes**: Complete splitting of `routes.py` into feature-based blueprints.
2.  [ ] **Service Layer**: Extract business logic from routes into `src/services/`.
