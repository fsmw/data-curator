# Design Log 02 — Storage, Catalog, and User Scoping

## Background
The project stores dataset files on disk and metadata in SQLite. Over time it added per-user ownership and access boundaries.

## Problem
Without clear design documentation, ownership semantics (global/local/my-data) and filename mapping behavior were difficult to reason about.

## Questions and Answers
- Q: Why both ORM models and direct SQLite access?
  - A: ORM supports admin/auth models, while `DatasetCatalog` provides fast metadata indexing/search workflows.
- Q: How is user ownership represented?
  - A: Catalog records include `owner_username` (sanitized username), and user files live in user-scoped directories.

## Design
1. **Hybrid persistence**
   - SQLAlchemy models for app/admin entities (`src/models.py`).
   - Direct SQLite metadata engine in `src/dataset_catalog.py`.
2. **Catalog schema with metadata richness**
   - File identity, source, indicator/topic, column stats, year range, countries, completeness score.
3. **User scoping**
   - `owner_username` column and filtering in catalog search/statistics.
   - Username normalization via `sanitize_username` (`src/utils/storage.py`).
4. **Real filename vs storage filename**
   - Preserve user-facing names via `display_file_name`; physical file can differ.

## Implementation Plan
- [x] Keep `owner_username` filtering in search/statistics/listing APIs.
- [x] Keep `display_file_name` for UX-facing exports/downloads.
- [x] Keep per-user directory strategy for clean datasets.

## Examples
- ✅ `DatasetCatalog.search(..., owner_username=...)` scopes results (`src/dataset_catalog.py`).
- ✅ API checks dataset ownership before detail/delete/download (`src/web/api/datasets.py`).
- ✅ Backup and single-download ZIP flows use display names for CSV entries.
- ❌ Returning cross-user datasets in `/api/datasets` responses.

## Trade-offs
- **Pros:** Strong tenant isolation, predictable user data boundaries, better UX naming.
- **Cons:** Duplicate logic across ORM and raw SQLite layers increases maintenance complexity.

