# Migration Scripts

This directory contains utility scripts for the dataset source-of-truth migration.

## Overview

These scripts support the migration plan detailed in:
- **Full Plan:** `design-log/12-dataset-source-of-truth-migration-plan.md`
- **Summary:** `MIGRATION_SUMMARY.md`

---

## Scripts

### 1. `audit_dataset_ownership.py`

**Purpose:** Analyze current ownership data state (Phase 1)

**Usage:**
```bash
python3 scripts/audit_dataset_ownership.py [--export-csv]
```

**What it checks:**
- Total datasets and ownership breakdown
- Datasets with NULL owner_id or owner_username
- Orphaned owner_id references (user deleted)
- Inconsistent ownership (owner_username doesn't match user)
- Datasets grouped by owner

**Output:**
- Human-readable report to stdout
- Optional CSV export with `--export-csv`
- Exit code 0 if no issues, 1 if issues found

**When to run:**
- Phase 1: Before starting migration
- After any ownership-related changes
- To verify data quality

---

### 2. `verify_migration.py`

**Purpose:** Verify migration completeness and correctness (Phase 5)

**Usage:**
```bash
python3 scripts/verify_migration.py [--verbose]
```

**What it checks:**
1. **Schema Integrity:** All required tables/columns exist
2. **Data Counts:** ORM and catalog counts match
3. **Ownership Consistency:** All datasets have valid owner_username
4. **RBAC Parity:** Catalog RBAC matches ORM behavior

**Output:**
- Detailed check results
- ✅/❌ status for each check
- Exit code 0 if all pass, 1 if failures, 2 if fatal error

**When to run:**
- After Phase 4 (ownership normalization)
- After Phase 5 (before declaring migration complete)
- Post-deployment health check

**Example output:**
```
1. Schema Integrity Check
----------------------------------------------------------
✅ All required tables exist
✅ All required columns exist in datasets table
✅ Full-text search table exists

2. Data Counts Verification
----------------------------------------------------------
✅ Dataset counts match: 180 datasets
✅ No duplicate datasets

3. Ownership Consistency Check
----------------------------------------------------------
✅ All datasets have owner_username
✅ No orphaned owner_id references
✅ All owner_username fields match user records
✅ All owner_username values are properly sanitized

4. RBAC Parity Verification
----------------------------------------------------------
✅ DatasetCatalog has RBAC methods
✅ RBAC parity verified for user testuser

SUMMARY
----------------------------------------------------------
Total Issues Found: 0

✅ ALL CHECKS PASSED!
```

---

### 3. `rollback_ownership.py`

**Purpose:** Rollback ownership changes if Phase 4 fails

**Usage:**
```bash
# Preview changes (recommended first)
python3 scripts/rollback_ownership.py --dry-run

# Interactive with confirmation
python3 scripts/rollback_ownership.py

# Force (no confirmation)
python3 scripts/rollback_ownership.py --force
```

**What it does:**
- Restores owner_username from owner_id by joining users table
- Creates automatic backup before making changes
- Shows preview of all changes
- Verifies final state

**Safety features:**
- Automatic backup with timestamp
- Dry-run mode to preview
- Interactive confirmation (unless --force)
- Transaction rollback on error

**When to run:**
- If Phase 4 normalization causes data corruption
- If owner_username values are incorrect after migration
- As part of full migration rollback

**Example output:**
```
CURRENT STATE
----------------------------------------------------------
Total datasets: 180
NULL owner_username: 25
NULL owner_id: 6
Has owner_id but no owner_username: 25

PROPOSED CHANGES
----------------------------------------------------------
Datasets to update: 25

Sample changes (first 10):
  ID 5: 'None' → 'admin'
  ID 12: 'None' → 'fsanmartin'
  ID 18: 'None' → 'testuser'
  ...

⚠️  WARNING: This will modify the database!
----------------------------------------------------------
Proceed with rollback? (yes/no): yes

✅ Backup created: datasets_catalog_pre_rollback_20240115_143022.db
✅ Rollback complete: 25 datasets updated
```

---

## Migration Workflow

### Phase 1: Audit
```bash
# Run audit to understand current state
python3 scripts/audit_dataset_ownership.py --export-csv

# Review output - identify issues
less ownership_audit.csv
```

### Phase 4: After Normalization
```bash
# Verify changes were successful
python3 scripts/verify_migration.py

# If issues found, rollback
python3 scripts/rollback_ownership.py --dry-run  # Preview
python3 scripts/rollback_ownership.py            # Execute
```

### Phase 5: Final Verification
```bash
# Run all checks with verbose output
python3 scripts/verify_migration.py --verbose

# Should report 0 issues
```

### Post-Migration: Health Checks
```bash
# Weekly verification during monitoring period
python3 scripts/verify_migration.py

# Export ownership report for records
python3 scripts/audit_dataset_ownership.py --export-csv
```

---

## Requirements

All scripts require:
- Python 3.7+
- Project dependencies installed: `pip install -r requirements.txt`
- Flask app context (scripts initialize automatically)
- Access to `datasets_catalog.db` in data root

---

## Exit Codes

All scripts use standard exit codes:
- `0` - Success (no issues)
- `1` - Issues found (but script completed)
- `2` - Fatal error (script could not complete)

---

## Troubleshooting

### "Database not found"
- Check `config.yaml` data_root path
- Ensure database exists: `ls -la datasets_catalog.db`

### "Flask app context required"
- Scripts initialize Flask app automatically
- Check `FLASK_SECRET_KEY` in environment
- Verify `src/web/__init__.py` is intact

### "Permission denied"
- Make scripts executable: `chmod +x scripts/*.py`
- Ensure write access to data directory

### "ImportError: No module named 'src'"
- Run from repository root: `python3 scripts/audit_dataset_ownership.py`
- Not from scripts directory: `cd .. && python3 scripts/...`

---

## See Also

- **Design Log #12:** Complete migration plan with phased approach
- **MIGRATION_SUMMARY.md:** Executive summary and quick reference
- **Design Log #11:** Original problem statement
- **src/dataset_catalog.py:** DatasetCatalog implementation
- **src/models.py:** SQLAlchemy Dataset model
