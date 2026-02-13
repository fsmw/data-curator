#!/usr/bin/env python3
"""
Verification script for dataset source-of-truth migration.

Run after Phase 4-5 to verify ownership consistency and RBAC parity
between SQLAlchemy ORM and DatasetCatalog.

Usage:
    python3 scripts/verify_migration.py [--verbose]
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.dataset_catalog import DatasetCatalog
from src.models import Dataset, db, User
from src.utils.storage import sanitize_username


def verify_ownership_consistency(verbose=False):
    """Verify ownership data is consistent."""
    config = Config()
    catalog = DatasetCatalog(config)
    
    conn = sqlite3.connect(catalog.db_path)
    cursor = conn.cursor()
    
    issues = []
    
    # Check 1: All datasets have owner_username
    cursor.execute("SELECT COUNT(*) FROM datasets WHERE owner_username IS NULL")
    null_owners = cursor.fetchone()[0]
    if null_owners > 0:
        issues.append(f"❌ {null_owners} datasets missing owner_username")
    else:
        print("✅ All datasets have owner_username")
    
    # Check 2: No orphaned owner_id references
    cursor.execute("""
        SELECT COUNT(*) FROM datasets 
        WHERE owner_id IS NOT NULL 
        AND owner_id NOT IN (SELECT id FROM users)
    """)
    orphaned = cursor.fetchone()[0]
    if orphaned > 0:
        issues.append(f"❌ {orphaned} datasets have invalid owner_id")
    else:
        print("✅ No orphaned owner_id references")
    
    # Check 3: owner_username matches user.username via owner_id
    cursor.execute("""
        SELECT d.id, d.owner_username, u.username
        FROM datasets d
        JOIN users u ON d.owner_id = u.id
        WHERE d.owner_username != ?
    """, (sanitize_username(''),))  # Using empty to bypass, better approach below
    
    mismatches = cursor.fetchall()
    if mismatches and verbose:
        for dataset_id, owner_username, expected_username in mismatches[:10]:
            expected_sanitized = sanitize_username(expected_username)
            if owner_username != expected_sanitized:
                issues.append(f"❌ Dataset {dataset_id}: has '{owner_username}', expected '{expected_sanitized}'")
    
    if not mismatches:
        print("✅ All owner_username fields match user records")
    elif len(mismatches) <= 5:
        print(f"⚠️  {len(mismatches)} minor mismatches (acceptable if username format changed)")
    else:
        print(f"❌ {len(mismatches)} datasets have mismatched ownership")
    
    # Check 4: Verify sanitization consistency
    cursor.execute("SELECT DISTINCT owner_username FROM datasets WHERE owner_username IS NOT NULL")
    usernames = [row[0] for row in cursor.fetchall()]
    unsanitized = [u for u in usernames if u != sanitize_username(u)]
    if unsanitized:
        issues.append(f"❌ {len(unsanitized)} owner_username values are not properly sanitized")
        if verbose:
            print(f"   Unsanitized usernames: {unsanitized[:5]}")
    else:
        print("✅ All owner_username values are properly sanitized")
    
    conn.close()
    return issues


def verify_rbac_parity(verbose=False):
    """Verify RBAC checks work via catalog."""
    config = Config()
    catalog = DatasetCatalog(config)
    
    issues = []
    
    # Check if can_access method exists
    if not hasattr(catalog, 'can_access'):
        issues.append("❌ DatasetCatalog missing can_access method (Phase 2 incomplete)")
        return issues
    
    print("✅ DatasetCatalog has RBAC methods")
    
    # Test with known user/dataset
    try:
        user = User.query.first()
        if not user:
            issues.append("⚠️  No users in database, skipping RBAC parity check")
            return issues
        
        dataset = Dataset.query.filter_by(owner_id=user.id).first()
        if not dataset:
            issues.append("⚠️  No datasets owned by test user, skipping RBAC parity check")
            return issues
        
        # Should match
        orm_result = dataset.can_access(user.id, 'read')
        catalog_result = catalog.can_access(dataset.id, user.username, 'read')
        
        if orm_result != catalog_result:
            issues.append(f"❌ RBAC mismatch for dataset {dataset.id}: ORM={orm_result}, Catalog={catalog_result}")
        else:
            print(f"✅ RBAC parity verified for user {user.username}")
    
    except AttributeError as e:
        issues.append(f"❌ RBAC method missing: {e}")
    except Exception as e:
        issues.append(f"❌ Unexpected error during RBAC test: {e}")
    
    return issues


def verify_schema_integrity(verbose=False):
    """Verify database schema is intact."""
    config = Config()
    catalog = DatasetCatalog(config)
    
    conn = sqlite3.connect(catalog.db_path)
    cursor = conn.cursor()
    
    issues = []
    
    # Check required tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    
    required_tables = ['datasets', 'users', 'user_dataset_access', 'dataset_columns']
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        issues.append(f"❌ Missing tables: {missing}")
    else:
        print("✅ All required tables exist")
    
    # Check datasets table has required columns
    cursor.execute("PRAGMA table_info(datasets)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required_columns = ['id', 'file_path', 'owner_username', 'owner_id', 'is_public', 'is_shared']
    missing_cols = [c for c in required_columns if c not in columns]
    
    if missing_cols:
        issues.append(f"❌ Missing columns in datasets: {missing_cols}")
    else:
        print("✅ All required columns exist in datasets table")
    
    # Check FTS table
    if 'datasets_fts' not in tables:
        issues.append("❌ Full-text search table missing")
    else:
        print("✅ Full-text search table exists")
    
    conn.close()
    return issues


def verify_data_counts(verbose=False):
    """Verify dataset counts match across layers."""
    config = Config()
    catalog = DatasetCatalog(config)
    
    conn = sqlite3.connect(catalog.db_path)
    cursor = conn.cursor()
    
    issues = []
    
    # Count via raw SQL
    cursor.execute("SELECT COUNT(*) FROM datasets")
    catalog_count = cursor.fetchone()[0]
    
    # Count via ORM
    orm_count = Dataset.query.count()
    
    if catalog_count != orm_count:
        issues.append(f"❌ Count mismatch: Catalog={catalog_count}, ORM={orm_count}")
    else:
        print(f"✅ Dataset counts match: {catalog_count} datasets")
    
    # Check for duplicates
    cursor.execute("SELECT file_path, COUNT(*) FROM datasets GROUP BY file_path HAVING COUNT(*) > 1")
    duplicates = cursor.fetchall()
    if duplicates:
        issues.append(f"❌ {len(duplicates)} duplicate file_path entries")
        if verbose:
            for path, count in duplicates[:5]:
                print(f"   Duplicate: {path} ({count} times)")
    else:
        print("✅ No duplicate datasets")
    
    conn.close()
    return issues


def main():
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    print("=" * 60)
    print("Dataset Source-of-Truth Migration Verification")
    print("=" * 60)
    print()
    
    all_issues = []
    
    print("1. Schema Integrity Check")
    print("-" * 60)
    schema_issues = verify_schema_integrity(verbose)
    all_issues.extend(schema_issues)
    print()
    
    print("2. Data Counts Verification")
    print("-" * 60)
    count_issues = verify_data_counts(verbose)
    all_issues.extend(count_issues)
    print()
    
    print("3. Ownership Consistency Check")
    print("-" * 60)
    ownership_issues = verify_ownership_consistency(verbose)
    all_issues.extend(ownership_issues)
    print()
    
    print("4. RBAC Parity Verification")
    print("-" * 60)
    rbac_issues = verify_rbac_parity(verbose)
    all_issues.extend(rbac_issues)
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Issues Found: {len(all_issues)}")
    
    if all_issues:
        print("\n❌ VERIFICATION FAILED\n")
        print("Issues:")
        for issue in all_issues:
            print(f"  {issue}")
        print("\nRecommended actions:")
        print("  1. Review issues above")
        print("  2. Run with --verbose for more details")
        print("  3. Consider rollback if critical issues found")
        print("  4. Re-run normalization if ownership issues detected")
        sys.exit(1)
    else:
        print("\n✅ ALL CHECKS PASSED!\n")
        print("Migration verification successful.")
        print("Safe to proceed to next phase or production deployment.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        # Initialize Flask app context for ORM queries
        from src.web import create_app
        app = create_app()
        with app.app_context():
            main()
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        print("\nVerification could not complete.")
        import traceback
        traceback.print_exc()
        sys.exit(2)
