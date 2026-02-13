# Migration Execution Checklist

**Migration:** Dataset Source-of-Truth Consolidation  
**Date Started:** _________________  
**Executed By:** _________________  

Use this checklist during actual migration execution. Check off each item as completed.

---

## Pre-Flight Checks

- [ ] Read complete plan: `design-log/12-dataset-source-of-truth-migration-plan.md`
- [ ] Review summary: `MIGRATION_SUMMARY.md`
- [ ] Understand scripts: `scripts/README.md`
- [ ] Schedule 3-4 day migration window
- [ ] Notify team of planned changes
- [ ] Prepare rollback plan communication

---

## Phase 1: Analysis & Preparation (2-4 hours)

### 1.1 Backup Current State
- [ ] Create database backup
  ```bash
  cp datasets_catalog.db datasets_catalog_pre_migration_$(date +%Y%m%d).db
  ```
- [ ] Record backup location: _________________
- [ ] Verify backup file size matches original
- [ ] Test backup can be opened
  ```bash
  sqlite3 datasets_catalog_pre_migration_*.db "SELECT COUNT(*) FROM datasets"
  ```

### 1.2 Run Ownership Audit
- [ ] Execute audit script
  ```bash
  python3 scripts/audit_dataset_ownership.py --export-csv > ownership_audit.txt
  ```
- [ ] Review audit output
- [ ] Record baseline metrics:
  - Total datasets: _______
  - NULL owners: _______
  - owner_id only: _______
  - owner_username only: _______
  - Orphaned: _______
  - Inconsistent: _______

### 1.3 Verify Test Suite
- [ ] Run existing tests
  ```bash
  pytest tests/ -v
  ```
- [ ] Record baseline: _____ passing / _____ total
- [ ] No critical failures blocking migration

### 1.4 Document ORM Write Operations
- [ ] Grep for ORM writes
  ```bash
  grep -rn "db.session.add\|db.session.commit" src/ --include="*.py" | grep -i dataset > orm_writes.txt
  ```
- [ ] Review `services/__init__.py` PermissionService
- [ ] Review `admin_views.py` actions
- [ ] Count: _____ ORM write locations found

**Phase 1 Complete:** [ ] YES  Date: _______

---

## Phase 2: Extend DatasetCatalog (4-6 hours)

### 2.1 Add RBAC Methods
- [ ] Open `src/dataset_catalog.py`
- [ ] Add `can_access(dataset_id, username, min_level)` method
- [ ] Add `grant_access(dataset_id, granter, target, level)` method
- [ ] Add `revoke_access(dataset_id, revoker, target)` method
- [ ] Add `normalize_ownership(force)` method
- [ ] Add `update_dataset_metadata(dataset_id, updates, username)` method

### 2.2 Write Unit Tests
- [ ] Create `tests/test_catalog_rbac.py`
- [ ] Test: `test_can_access_owner`
- [ ] Test: `test_can_access_public_read`
- [ ] Test: `test_grant_revoke_access`
- [ ] Test: `test_unauthorized_grant_fails`
- [ ] Test: `test_update_dataset_metadata`
- [ ] All new tests pass: `pytest tests/test_catalog_rbac.py -v`

### 2.3 Verify No Breaking Changes
- [ ] Run full test suite
  ```bash
  pytest tests/ -v
  ```
- [ ] Tests passing: _____ / _____
- [ ] No regressions vs Phase 1 baseline

**Phase 2 Complete:** [ ] YES  Date: _______

---

## Phase 3: Deprecate ORM Writes (3-5 hours)

### 3.1 Refactor PermissionService
- [ ] Open `src/services/__init__.py`
- [ ] Update `can_read()` to use catalog
- [ ] Update `can_write()` to use catalog
- [ ] Update `can_admin()` to use catalog
- [ ] Update `get_user_datasets()` to use catalog
- [ ] Update `grant_access()` to use catalog
- [ ] Update `revoke_access()` to use catalog
- [ ] Remove ORM queries from PermissionService

### 3.2 Update Flask-Admin Views
Choose approach:
- [ ] **Option A:** Make admin views read-only
  - [ ] Set `can_create = False`
  - [ ] Set `can_edit = False`
  - [ ] Set `can_delete = False`
  - [ ] Update actions to use catalog methods

OR

- [ ] **Option B:** Add ORM sync listener
  - [ ] Add `@event.listens_for(Dataset, 'after_update')` in `models.py`
  - [ ] Sync changes to catalog on ORM updates
  - [ ] Test admin edits propagate to catalog

### 3.3 Verify No ORM Writes
- [ ] Grep for remaining ORM writes
  ```bash
  grep -rn "db.session.add.*Dataset\|db.session.commit" src/ --include="*.py" | grep -v "# Migration:"
  ```
- [ ] Only admin_views.py OR models.py sync listener should remain
- [ ] Run integration tests

**Phase 3 Complete:** [ ] YES  Date: _______

---

## Phase 4: Schema Consolidation (2-3 hours)

### 4.1 Backup Before Normalization
- [ ] Create pre-normalization backup
  ```bash
  cp datasets_catalog.db datasets_catalog_pre_norm_$(date +%Y%m%d_%H%M%S).db
  ```
- [ ] Record backup location: _________________

### 4.2 Run Normalization (DRY RUN)
- [ ] Test normalization dry-run
  ```python
  from src.config import Config
  from src.dataset_catalog import DatasetCatalog
  
  config = Config()
  catalog = DatasetCatalog(config)
  result = catalog.normalize_ownership(force=False)
  print(f"Would update: {result['updated']} datasets")
  ```
- [ ] Review proposed changes
- [ ] Verify changes look correct

### 4.3 Run Normalization (EXECUTE)
- [ ] Execute normalization
  ```python
  result = catalog.normalize_ownership(force=True)
  print(f"Updated: {result['updated']} datasets")
  print(f"Details: {result['details'][:10]}")  # First 10
  ```
- [ ] Record: _____ datasets updated

### 4.4 Verify Normalization
- [ ] Check NULL counts
  ```sql
  sqlite3 datasets_catalog.db "SELECT COUNT(*) FROM datasets WHERE owner_username IS NULL"
  ```
- [ ] Result: _____ (should be 0 or very low)
- [ ] Spot-check 5-10 datasets manually

**Phase 4 Complete:** [ ] YES  Date: _______

---

## Phase 5: Testing & Verification (3-4 hours)

### 5.1 Run Verification Script
- [ ] Execute verification
  ```bash
  python3 scripts/verify_migration.py --verbose > verification_results.txt
  ```
- [ ] Schema integrity: [ ] PASS
- [ ] Data counts: [ ] PASS
- [ ] Ownership consistency: [ ] PASS
- [ ] RBAC parity: [ ] PASS
- [ ] Overall result: [ ] PASS (0 issues)

### 5.2 Run Full Test Suite
- [ ] Execute all tests
  ```bash
  pytest tests/ -v --tb=short
  ```
- [ ] Tests passing: _____ / _____
- [ ] Compare to Phase 1 baseline
- [ ] No regressions: [ ] YES

### 5.3 Integration Tests
- [ ] Test Flask-Admin dataset list loads
- [ ] Test Flask-Admin dataset edit (if enabled)
- [ ] Test API `/api/datasets` endpoint
- [ ] Test API `/api/datasets/{id}` detail
- [ ] Test API dataset deletion with RBAC
- [ ] Test API dataset sharing with RBAC
- [ ] Test public dataset access
- [ ] Test owner-only dataset access

### 5.4 Performance Benchmarks
- [ ] Measure RBAC check time
  ```python
  import time
  start = time.time()
  catalog.can_access(1, 'testuser', 'read')
  print(f"Time: {(time.time()-start)*1000:.2f}ms")
  ```
- [ ] Average time: _____ ms (target: <50ms)
- [ ] Compare to ORM baseline
- [ ] Acceptable performance: [ ] YES

### 5.5 Security Audit
- [ ] Test non-owner cannot delete dataset
- [ ] Test non-owner cannot modify dataset
- [ ] Test public datasets are readable by all
- [ ] Test private datasets are owner-only
- [ ] Test shared datasets respect access levels
- [ ] No RBAC bypasses found: [ ] YES

**Phase 5 Complete:** [ ] YES  Date: _______

---

## Phase 6: Documentation & Cleanup (2-3 hours)

### 6.1 Update Documentation
- [ ] Update `docs/ARCHITECTURE.md` with source-of-truth decision
- [ ] Update `README.md` if dataset operations mentioned
- [ ] Add migration notes to this design log (Implementation Results section)

### 6.2 Design Log Updates
- [ ] Fill in Phase 1-6 completion dates in Design Log #12
- [ ] Document deviations from plan
- [ ] Record test results
- [ ] Add lessons learned
- [ ] Mark Design Log #11 as superseded

### 6.3 Code Cleanup (Optional)
- [ ] Mark `owner_id` column as deprecated (comment in schema)
- [ ] Add deprecation warnings to ORM Dataset methods
- [ ] Remove or archive old scripts
- [ ] Update type hints if needed

### 6.4 Final Verification
- [ ] Run verification script one more time
  ```bash
  python3 scripts/verify_migration.py
  ```
- [ ] Result: [ ] PASS
- [ ] Create final audit report
  ```bash
  python3 scripts/audit_dataset_ownership.py --export-csv
  mv ownership_audit.csv ownership_audit_post_migration.csv
  ```

**Phase 6 Complete:** [ ] YES  Date: _______

---

## Post-Migration Monitoring (1 week)

### Daily Checks (Days 1-7)
For each day, check:

**Day 1:** Date: _______
- [ ] Verify script passes: `python3 scripts/verify_migration.py`
- [ ] Check error logs for permission issues
- [ ] Monitor user reports/complaints
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

**Day 2:** Date: _______
- [ ] Verify script passes
- [ ] Check error logs
- [ ] Monitor user reports
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

**Day 3:** Date: _______
- [ ] Verify script passes
- [ ] Check error logs
- [ ] Monitor user reports
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

**Day 4:** Date: _______
- [ ] Verify script passes
- [ ] Check error logs
- [ ] Monitor user reports
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

**Day 5:** Date: _______
- [ ] Verify script passes
- [ ] Check error logs
- [ ] Monitor user reports
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

**Day 6:** Date: _______
- [ ] Verify script passes
- [ ] Check error logs
- [ ] Monitor user reports
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

**Day 7:** Date: _______
- [ ] Verify script passes
- [ ] Check error logs
- [ ] Monitor user reports
- [ ] Performance metrics acceptable
- [ ] Issues found: _________________

### Week Summary
- [ ] 0 critical issues during monitoring period
- [ ] 0 data corruption incidents
- [ ] Admin workflows functional
- [ ] API endpoints stable
- [ ] User feedback positive/neutral
- [ ] Performance within 10% of baseline

---

## Migration Sign-Off

### Success Criteria
All must be checked:
- [ ] All 6 phases completed successfully
- [ ] Verification script reports 0 issues
- [ ] All tests passing (90%+ coverage on new code)
- [ ] 1 week monitoring period complete
- [ ] No critical issues found
- [ ] Documentation updated
- [ ] Team trained on new architecture

### Final Approval

**Migration Status:** [ ] SUCCESSFUL  [ ] REQUIRES ROLLBACK

**Completed By:** _________________  
**Date:** _______  
**Approved By:** _________________  
**Date:** _______

### Follow-Up Tasks
- [ ] Schedule `owner_id` column removal for v2.0 (3+ months)
- [ ] Archive pre-migration backups after 30 days
- [ ] Share lessons learned with team
- [ ] Update onboarding docs for new developers

---

## Emergency Rollback

If critical issues arise:

1. **Stop services:**
   ```bash
   systemctl stop data-curator
   ```

2. **Restore backup:**
   ```bash
   cp datasets_catalog_pre_migration_*.db datasets_catalog.db
   ```

3. **Revert code:**
   ```bash
   git checkout <pre-migration-commit>
   pip install -r requirements.txt
   ```

4. **Restart services:**
   ```bash
   systemctl start data-curator
   ```

5. **Verify rollback:**
   ```bash
   python3 scripts/audit_dataset_ownership.py
   ```

6. **Document incident:**
   - What triggered rollback: _________________
   - Impact: _________________
   - Next steps: _________________

---

## Notes & Observations

Use this space for any additional notes during migration:

```





```
