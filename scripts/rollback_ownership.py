#!/usr/bin/env python3
"""
Rollback script for dataset source-of-truth migration.

Use this script if Phase 4 ownership normalization causes issues.
Restores owner_username from owner_id by joining with users table.

Usage:
    python3 scripts/rollback_ownership.py [--dry-run] [--force]

Options:
    --dry-run    Show what would be changed without making changes
    --force      Skip confirmation prompt
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.utils.storage import sanitize_username


def create_backup(db_path):
    """Create backup before rollback."""
    backup_path = db_path.parent / f"datasets_catalog_pre_rollback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path


def rollback_ownership(dry_run=False, force=False):
    """Rollback owner_username to values derived from owner_id."""
    config = Config()
    db_path = config.data_root / 'datasets_catalog.db'
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get current state
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN owner_username IS NULL THEN 1 ELSE 0 END) as null_username,
            SUM(CASE WHEN owner_id IS NULL THEN 1 ELSE 0 END) as null_id,
            SUM(CASE WHEN owner_id IS NOT NULL AND owner_username IS NULL THEN 1 ELSE 0 END) as id_only
        FROM datasets
    """)
    stats = cursor.fetchone()
    
    print("\n" + "=" * 60)
    print("CURRENT STATE")
    print("=" * 60)
    print(f"Total datasets: {stats[0]}")
    print(f"NULL owner_username: {stats[1]}")
    print(f"NULL owner_id: {stats[2]}")
    print(f"Has owner_id but no owner_username: {stats[3]}")
    
    # Preview changes
    cursor.execute("""
        SELECT d.id, d.file_name, d.owner_id, d.owner_username, u.username
        FROM datasets d
        LEFT JOIN users u ON d.owner_id = u.id
        WHERE d.owner_id IS NOT NULL
    """)
    
    changes = []
    for dataset_id, file_name, owner_id, current_username, user_username in cursor.fetchall():
        if user_username:
            expected_username = sanitize_username(user_username)
            if current_username != expected_username:
                changes.append({
                    'id': dataset_id,
                    'file_name': file_name,
                    'owner_id': owner_id,
                    'current': current_username,
                    'new': expected_username
                })
        else:
            # owner_id points to non-existent user
            if current_username is not None:
                changes.append({
                    'id': dataset_id,
                    'file_name': file_name,
                    'owner_id': owner_id,
                    'current': current_username,
                    'new': None,
                    'warning': 'owner_id orphaned'
                })
    
    print("\n" + "=" * 60)
    print("PROPOSED CHANGES")
    print("=" * 60)
    print(f"Datasets to update: {len(changes)}")
    
    if changes:
        print("\nSample changes (first 10):")
        for change in changes[:10]:
            warning = f" ⚠️ {change.get('warning')}" if 'warning' in change else ""
            print(f"  ID {change['id']}: '{change['current']}' → '{change['new']}'{warning}")
        
        if len(changes) > 10:
            print(f"  ... and {len(changes) - 10} more")
    else:
        print("No changes needed - all owner_username values are correct.")
        conn.close()
        return True
    
    if dry_run:
        print("\n🔍 DRY RUN - No changes made")
        conn.close()
        return True
    
    # Confirmation
    if not force:
        print("\n" + "=" * 60)
        print("⚠️  WARNING: This will modify the database!")
        print("=" * 60)
        response = input("Proceed with rollback? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Rollback cancelled")
            conn.close()
            return False
    
    # Create backup
    backup_path = create_backup(db_path)
    
    # Perform rollback
    print("\n" + "=" * 60)
    print("EXECUTING ROLLBACK")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for change in changes:
        try:
            if change.get('new') is None:
                # Clear orphaned username
                cursor.execute(
                    "UPDATE datasets SET owner_username = NULL WHERE id = ?",
                    (change['id'],)
                )
            else:
                # Update to correct username
                cursor.execute(
                    "UPDATE datasets SET owner_username = ? WHERE id = ?",
                    (change['new'], change['id'])
                )
            success_count += 1
        except Exception as e:
            print(f"❌ Error updating dataset {change['id']}: {e}")
            error_count += 1
    
    if error_count == 0:
        conn.commit()
        print(f"✅ Rollback complete: {success_count} datasets updated")
    else:
        conn.rollback()
        print(f"❌ Rollback failed: {error_count} errors, rolling back transaction")
        conn.close()
        return False
    
    # Verify final state
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN owner_username IS NULL THEN 1 ELSE 0 END) as null_username,
            SUM(CASE WHEN owner_id IS NOT NULL AND owner_username IS NULL THEN 1 ELSE 0 END) as id_only
        FROM datasets
    """)
    final_stats = cursor.fetchone()
    
    print("\n" + "=" * 60)
    print("FINAL STATE")
    print("=" * 60)
    print(f"NULL owner_username: {final_stats[0]}")
    print(f"Has owner_id but no owner_username: {final_stats[1]}")
    
    conn.close()
    
    print(f"\n✅ Rollback successful!")
    print(f"   Backup available at: {backup_path}")
    print(f"   To restore backup: cp {backup_path} {db_path}")
    
    return True


def main():
    dry_run = '--dry-run' in sys.argv
    force = '--force' in sys.argv
    
    print("=" * 60)
    print("Dataset Ownership Rollback Script")
    print("=" * 60)
    
    if dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    elif force:
        print("Mode: FORCE (no confirmation prompt)")
    else:
        print("Mode: INTERACTIVE (will prompt for confirmation)")
    
    try:
        success = rollback_ownership(dry_run=dry_run, force=force)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
