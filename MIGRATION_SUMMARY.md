# Dataset Source-of-Truth Migration - Executive Summary

**Status:** Ready for implementation  
**Design Log:** See `design-log/12-dataset-source-of-truth-migration-plan.md` for complete details  
**Estimated Time:** 16-25 hours (3-4 work days)

---

## The Problem

Currently, dataset metadata exists in two places:

1. **DatasetCatalog** (SQLite raw access) - Used by 99% of operations
   - 40+ API endpoints
   - CLI tools
   - Search, download, indexing
   - 180 datasets

2. **SQLAlchemy Dataset ORM** - Used minimally
   - Flask-Admin views (8 references)
   - PermissionService (11 references)
   - 2 files total

**Issue:** Ownership tracked differently:
- Catalog uses `owner_username` (string)
- ORM uses `owner_id` (int FK)
- Data is inconsistent (25 NULL owners, 6 username-only, 149 ID-only)

---

## The Solution

**Target Architecture:** DatasetCatalog as primary source-of-truth

```
ALL OPERATIONS → DatasetCatalog → datasets_catalog.db
                       ↑
                       |
              (optional read-only)
                       |
             Flask-Admin ORM Layer
```

**Why DatasetCatalog?**
- Already handles 99% of operations
- Optimized for CSV metadata workflows
- FTS5 full-text search built-in
- Simpler ownership model (username-based)
- No Flask context required (works in CLI)

---

## Migration Phases

### Phase 1: Analysis & Preparation (2-4 hours)
- Audit current ownership data
- Document all ORM write operations
- Map RBAC dependencies

**Deliverable:** `MIGRATION_AUDIT_REPORT.md`

### Phase 2: Extend DatasetCatalog (4-6 hours)
Add RBAC methods to catalog:
- `can_access(dataset_id, username, min_level)`
- `grant_access(dataset_id, granter, target, level)`
- `revoke_access(dataset_id, revoker, target)`
- `normalize_ownership()` - Migrate owner_id → owner_username
- `update_dataset_metadata()` - Safe updates with ownership check

**Deliverable:** Enhanced catalog with RBAC

### Phase 3: Deprecate ORM Writes (3-5 hours)
- Refactor PermissionService to use catalog
- Update Flask-Admin (choose: read-only OR sync listener)
- Remove db.session write operations for datasets

**Deliverable:** Zero ORM writes outside admin layer

### Phase 4: Schema Consolidation (2-3 hours)
- Run ownership normalization script
- Populate all `owner_username` fields
- Add validation checks
- Keep `owner_id` for rollback (mark deprecated)

**Deliverable:** Consistent ownership data

### Phase 5: Testing & Verification (3-4 hours)
- Run verification script (checks consistency)
- Unit tests for catalog RBAC (30+ tests)
- Integration tests (admin sync, API enforcement)
- Performance benchmarks

**Deliverable:** 100% passing tests, 0 verification issues

### Phase 6: Documentation & Cleanup (2-3 hours)
- Update ARCHITECTURE.md
- Update this migration plan with results
- Remove dead code (optional, can wait)

**Deliverable:** Complete documentation

---

## Key Changes

### Before
```python
# services/__init__.py
dataset = Dataset.query.get(dataset_id)
return dataset.can_access(user_id, 'read')
```

### After
```python
# services/__init__.py
from src.dataset_catalog import DatasetCatalog

catalog = DatasetCatalog(config)
return catalog.can_access(dataset_id, username, 'read')
```

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Ownership data corruption | 🔴 High | Backup DB before Phase 4, verification script |
| RBAC bypass vulnerability | 🔴 High | Comprehensive security tests in Phase 5 |
| Flask-Admin breaks | 🟡 Medium | Read-only mode OR sync listener option |
| Performance degradation | 🟡 Medium | Add indexes, benchmark tests |
| API format changes | 🟢 Low | No schema changes to API layer |

---

## Rollback Strategy

### Phase 2-3 (Code only)
```bash
git revert <migration-commit>
```

### Phase 4-5 (Data changes)
```bash
# Restore from backup
cp datasets_catalog.db.backup datasets_catalog.db

# OR run rollback script
python3 scripts/rollback_ownership.py
```

### Phase 6+ (Full rollback)
```bash
systemctl stop data-curator
cp datasets_catalog.db.backup datasets_catalog.db
git checkout <pre-migration-commit>
pip install -r requirements.txt
systemctl start data-curator
```

---

## Verification Checklist

Essential checks before declaring success:

**Pre-Migration:**
- [ ] Backup `datasets_catalog.db`
- [ ] Document baseline: `SELECT COUNT(*) FROM datasets`
- [ ] Export ownership state
- [ ] All tests pass

**Each Phase:**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] No breaking changes to APIs

**Final Verification:**
- [ ] Ownership normalization: 0 NULL owner_username
- [ ] Verification script: 0 issues reported
- [ ] RBAC audit: No bypass vulnerabilities
- [ ] Performance: Within 10% of baseline
- [ ] All 30+ tests passing

**Post-Migration (1 week):**
- [ ] No user permission complaints
- [ ] No data corruption incidents
- [ ] Admin workflows functional
- [ ] Error logs clean

---

## Success Metrics

### Quantitative
- ✅ Remove 50+ lines of ORM boilerplate
- ✅ Achieve 90%+ test coverage on catalog RBAC
- ✅ RBAC checks < 50ms (p95)
- ✅ 100% datasets have valid owner_username

### Qualitative
- ✅ Single source of truth for all dataset operations
- ✅ Simplified developer mental model
- ✅ Consistent RBAC pattern across codebase
- ✅ Flask-Admin remains functional

---

## Next Steps

1. **Review complete plan:** `design-log/12-dataset-source-of-truth-migration-plan.md`
2. **Schedule migration:** Block 3-4 work days
3. **Backup database:** Critical before Phase 4
4. **Execute phases sequentially:** Don't skip verification steps
5. **Monitor for 1 week:** Watch logs, user reports
6. **Document lessons learned:** Update implementation results section

---

## References

- **Full Plan:** `design-log/12-dataset-source-of-truth-migration-plan.md` (360+ lines)
- **Current State:** `design-log/11-catalog-source-of-truth-consolidation.md`
- **Related:** Design Log #02 (Storage), #08 (Ownership UX), #09 (Deletion Policy)

---

## Contact

For questions about this migration:
1. Read the full plan in Design Log #12
2. Check the Q&A section (answers 5 common questions)
3. Review existing design logs (#02, #08, #11)
4. Run verification scripts in `scripts/` directory
