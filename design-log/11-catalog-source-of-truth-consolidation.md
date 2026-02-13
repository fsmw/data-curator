# Design Log 11 — Catalog Source-of-Truth Consolidation

## Status
**SUPERSEDED by Design Log #12** - See `12-dataset-source-of-truth-migration-plan.md` for complete implementation-ready migration plan.

## Background
The codebase currently uses both SQLAlchemy `Dataset` model and `DatasetCatalog` SQLite access patterns.

## Problem
Dual data access paths can diverge in ownership semantics (`owner_id` vs `owner_username`) and behavior across routes.

## Questions and Answers
- Q: What is the current contradiction?
  - A: Some flows rely on ORM-style dataset entities while most active dataset APIs rely on catalog rows.
- Q: What should be the canonical source for web dataset operations?
  - A: **DECISION:** `DatasetCatalog` as primary source-of-truth (99% of operations already use it).

## Design
1. Define single source-of-truth for dataset metadata and ownership checks.
2. Keep compatibility bridge only where required (e.g., admin/reporting).
3. Ensure consistent ownership key strategy across all dataset endpoints.

## Implementation Plan
✅ Detailed migration plan created in Design Log #12:
- Phase 1: Analysis & Preparation (2-4 hours)
- Phase 2: Extend DatasetCatalog with RBAC (4-6 hours)
- Phase 3: Deprecate ORM writes (3-5 hours)
- Phase 4: Schema consolidation (2-3 hours)
- Phase 5: Testing & verification (3-4 hours)
- Phase 6: Documentation (2-3 hours)

**Total:** 16-25 hours over 3-4 work days

## Examples
- ✅ All dataset APIs enforce ownership using one canonical layer.
- ❌ Mixed endpoint behavior depending on ORM vs catalog path.

## Trade-offs
- **Pros:** Consistent security semantics and simpler maintenance.
- **Cons:** Requires migration work and possible admin-view adjustments.

## References
See **Design Log #12** for:
- Target architecture diagrams
- Phased migration steps with code samples
- Rollback procedures
- Risk assessment
- Verification checklist

