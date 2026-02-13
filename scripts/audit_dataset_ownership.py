#!/usr/bin/env python3
"""
Ownership audit script for dataset source-of-truth migration.

Run during Phase 1 to understand current ownership data state
and identify inconsistencies between owner_id and owner_username.

Usage:
    python3 scripts/audit_dataset_ownership.py [--export-csv]

Options:
    --export-csv    Export results to CSV file
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config
from src.utils.storage import sanitize_username


def audit_ownership():
    """Audit current ownership state across datasets."""
    config = Config()
    db_path = config.data_root / 'datasets_catalog.db'
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return None
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'database_path': str(db_path),
        'summary': {},
        'issues': [],
        'by_user': [],
        'orphaned': [],
        'inconsistent': []
    }
    
    # Overall statistics
    cursor.execute("SELECT COUNT(*) FROM datasets")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM datasets WHERE owner_id IS NULL AND owner_username IS NULL")
    no_owner = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM datasets WHERE owner_id IS NOT NULL AND owner_username IS NULL")
    id_only = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM datasets WHERE owner_id IS NULL AND owner_username IS NOT NULL")
    username_only = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM datasets WHERE owner_id IS NOT NULL AND owner_username IS NOT NULL")
    both = cursor.fetchone()[0]
    
    results['summary'] = {
        'total_datasets': total,
        'no_owner': no_owner,
        'owner_id_only': id_only,
        'owner_username_only': username_only,
        'both_populated': both
    }
    
    # By user breakdown
    cursor.execute("""
        SELECT 
            COALESCE(d.owner_username, 'NULL') as username,
            COALESCE(d.owner_id, -1) as user_id,
            COUNT(*) as dataset_count,
            GROUP_CONCAT(d.id) as dataset_ids
        FROM datasets d
        GROUP BY d.owner_username, d.owner_id
        ORDER BY dataset_count DESC
    """)
    
    for username, user_id, count, ids in cursor.fetchall():
        ids_list = ids.split(',')[:5]  # First 5 IDs only
        results['by_user'].append({
            'username': username if username != 'NULL' else None,
            'user_id': user_id if user_id != -1 else None,
            'dataset_count': count,
            'sample_dataset_ids': ids_list
        })
    
    # Find orphaned owner_ids
    cursor.execute("""
        SELECT d.id, d.file_name, d.owner_id, d.owner_username
        FROM datasets d
        WHERE d.owner_id IS NOT NULL
        AND d.owner_id NOT IN (SELECT id FROM users)
    """)
    
    for dataset_id, file_name, owner_id, owner_username in cursor.fetchall():
        results['orphaned'].append({
            'dataset_id': dataset_id,
            'file_name': file_name,
            'owner_id': owner_id,
            'owner_username': owner_username,
            'issue': 'owner_id points to non-existent user'
        })
    
    # Find inconsistencies (owner_id user doesn't match owner_username)
    cursor.execute("""
        SELECT d.id, d.file_name, d.owner_id, d.owner_username, u.username
        FROM datasets d
        JOIN users u ON d.owner_id = u.id
        WHERE d.owner_username IS NOT NULL
    """)
    
    for dataset_id, file_name, owner_id, owner_username, actual_username in cursor.fetchall():
        expected_sanitized = sanitize_username(actual_username)
        if owner_username != expected_sanitized:
            results['inconsistent'].append({
                'dataset_id': dataset_id,
                'file_name': file_name,
                'owner_id': owner_id,
                'current_username': owner_username,
                'expected_username': expected_sanitized,
                'user_actual_username': actual_username
            })
    
    conn.close()
    
    # Identify issues
    if no_owner > 0:
        results['issues'].append(f"{no_owner} datasets have no ownership information")
    
    if id_only > 0:
        results['issues'].append(f"{id_only} datasets have owner_id but no owner_username")
    
    if username_only > 0:
        results['issues'].append(f"{username_only} datasets have owner_username but no owner_id")
    
    if results['orphaned']:
        results['issues'].append(f"{len(results['orphaned'])} datasets have orphaned owner_id")
    
    if results['inconsistent']:
        results['issues'].append(f"{len(results['inconsistent'])} datasets have mismatched ownership")
    
    return results


def print_report(results):
    """Print human-readable report."""
    print("=" * 70)
    print("DATASET OWNERSHIP AUDIT REPORT")
    print("=" * 70)
    print(f"Generated: {results['timestamp']}")
    print(f"Database: {results['database_path']}")
    print()
    
    # Summary
    summary = results['summary']
    print("SUMMARY")
    print("-" * 70)
    print(f"Total Datasets:              {summary['total_datasets']:>6}")
    print(f"No ownership:                {summary['no_owner']:>6} ({summary['no_owner']/summary['total_datasets']*100:.1f}%)")
    print(f"owner_id only:               {summary['owner_id_only']:>6} ({summary['owner_id_only']/summary['total_datasets']*100:.1f}%)")
    print(f"owner_username only:         {summary['owner_username_only']:>6} ({summary['owner_username_only']/summary['total_datasets']*100:.1f}%)")
    print(f"Both populated:              {summary['both_populated']:>6} ({summary['both_populated']/summary['total_datasets']*100:.1f}%)")
    print()
    
    # Issues
    if results['issues']:
        print("ISSUES IDENTIFIED")
        print("-" * 70)
        for i, issue in enumerate(results['issues'], 1):
            print(f"{i}. {issue}")
        print()
    else:
        print("✅ NO ISSUES IDENTIFIED")
        print()
    
    # By user
    print("DATASETS BY OWNER")
    print("-" * 70)
    print(f"{'Username':<20} {'User ID':<10} {'Count':<10} {'Sample IDs'}")
    print("-" * 70)
    for user in results['by_user'][:15]:  # Top 15
        username = user['username'] or '(null)'
        user_id = str(user['user_id']) if user['user_id'] else '(null)'
        sample = ', '.join(user['sample_dataset_ids'][:3])
        print(f"{username:<20} {user_id:<10} {user['dataset_count']:<10} {sample}")
    
    if len(results['by_user']) > 15:
        print(f"... and {len(results['by_user']) - 15} more")
    print()
    
    # Orphaned
    if results['orphaned']:
        print("ORPHANED OWNER_IDS")
        print("-" * 70)
        print(f"Found {len(results['orphaned'])} datasets with owner_id pointing to deleted users")
        for orphan in results['orphaned'][:10]:
            print(f"  Dataset {orphan['dataset_id']}: owner_id={orphan['owner_id']}, username={orphan['owner_username']}")
        if len(results['orphaned']) > 10:
            print(f"  ... and {len(results['orphaned']) - 10} more")
        print()
    
    # Inconsistent
    if results['inconsistent']:
        print("INCONSISTENT OWNERSHIP")
        print("-" * 70)
        print(f"Found {len(results['inconsistent'])} datasets where owner_username doesn't match user")
        for item in results['inconsistent'][:10]:
            print(f"  Dataset {item['dataset_id']}: '{item['current_username']}' should be '{item['expected_username']}'")
        if len(results['inconsistent']) > 10:
            print(f"  ... and {len(results['inconsistent']) - 10} more")
        print()
    
    # Recommendations
    print("RECOMMENDATIONS")
    print("-" * 70)
    
    if summary['owner_id_only'] > 0:
        print("1. Run ownership normalization to populate owner_username from owner_id")
        print("   Command: catalog.normalize_ownership(force=True)")
    
    if results['orphaned']:
        print("2. Clean up orphaned owner_id references:")
        print("   - Assign to a default 'unknown' user")
        print("   - OR set owner_id to NULL")
    
    if results['inconsistent']:
        print("3. Fix inconsistent ownership data using sanitize_username()")
    
    if summary['no_owner'] > 0:
        print("4. Assign ownership to legacy datasets without owners")
    
    if not results['issues']:
        print("✅ Data is consistent - ready for migration")
    
    print()
    print("=" * 70)


def export_csv(results, output_path='ownership_audit.csv'):
    """Export results to CSV."""
    import csv
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Summary section
        writer.writerow(['SUMMARY'])
        writer.writerow(['Metric', 'Value'])
        for key, value in results['summary'].items():
            writer.writerow([key, value])
        writer.writerow([])
        
        # By user section
        writer.writerow(['BY USER'])
        writer.writerow(['Username', 'User ID', 'Dataset Count', 'Sample IDs'])
        for user in results['by_user']:
            writer.writerow([
                user['username'] or '(null)',
                user['user_id'] or '(null)',
                user['dataset_count'],
                ', '.join(user['sample_dataset_ids'])
            ])
        writer.writerow([])
        
        # Orphaned section
        if results['orphaned']:
            writer.writerow(['ORPHANED'])
            writer.writerow(['Dataset ID', 'File Name', 'Owner ID', 'Owner Username', 'Issue'])
            for item in results['orphaned']:
                writer.writerow([
                    item['dataset_id'],
                    item['file_name'],
                    item['owner_id'],
                    item['owner_username'],
                    item['issue']
                ])
            writer.writerow([])
        
        # Inconsistent section
        if results['inconsistent']:
            writer.writerow(['INCONSISTENT'])
            writer.writerow(['Dataset ID', 'File Name', 'Current Username', 'Expected Username'])
            for item in results['inconsistent']:
                writer.writerow([
                    item['dataset_id'],
                    item['file_name'],
                    item['current_username'],
                    item['expected_username']
                ])
    
    print(f"✅ Results exported to: {output_path}")


def main():
    export = '--export-csv' in sys.argv
    
    try:
        results = audit_ownership()
        if results is None:
            sys.exit(1)
        
        print_report(results)
        
        if export:
            export_csv(results)
        
        # Exit code based on issues
        sys.exit(0 if not results['issues'] else 1)
    
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
