#!/usr/bin/env python3
"""Consolidate databases into single database and migrate to multi-user schema."""

import sys
from pathlib import Path
import sqlite3
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))

def consolidate_databases():
    """Merge instance database into main database and migrate schema."""
    
    main_db = Path("datasets_catalog.db")
    instance_db = Path("instance/datasets_catalog.db")
    backup_db = Path("datasets_catalog.db.backup")
    
    print("=== Database Consolidation ===\n")
    
    # Create backup
    if main_db.exists():
        shutil.copy2(main_db, backup_db)
        print(f"✓ Created backup: {backup_db}")
    
    # Connect to main database
    conn = sqlite3.connect(main_db)
    cursor = conn.cursor()
    
    # 1. Add new columns to datasets table
    print("\n1. Migrating datasets schema...")
    columns_to_add = [
        ('owner_id', 'INTEGER'),
        ('is_public', 'BOOLEAN DEFAULT 0'),
        ('is_shared', 'BOOLEAN DEFAULT 0'),
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE datasets ADD COLUMN {col_name} {col_type}")
            print(f"   ✓ Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"   ℹ Column {col_name} already exists")
            else:
                print(f"   ✗ Error: {e}")
    
    # 2. Create UserDatasetAccess table
    print("\n2. Creating UserDatasetAccess table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_dataset_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dataset_id INTEGER NOT NULL,
            access_level VARCHAR(20) DEFAULT 'read',
            granted_by INTEGER,
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            UNIQUE(user_id, dataset_id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (dataset_id) REFERENCES datasets (id),
            FOREIGN KEY (granted_by) REFERENCES users (id)
        )
    """)
    print("   ✓ UserDatasetAccess table ready")
    
    # 3. Create UserWorkspace table
    print("\n3. Creating UserWorkspace table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name VARCHAR(100) DEFAULT 'My Workspace',
            description TEXT,
            default_chart_type VARCHAR(50) DEFAULT 'line',
            theme VARCHAR(20) DEFAULT 'light',
            language VARCHAR(10) DEFAULT 'en',
            max_datasets INTEGER DEFAULT 100,
            max_storage_mb INTEGER DEFAULT 1000,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    print("   ✓ UserWorkspace table ready")
    
    # 4. Copy users from instance database if exists
    if instance_db.exists():
        print(f"\n4. Migrating users from {instance_db}...")
        instance_conn = sqlite3.connect(instance_db)
        instance_cursor = instance_conn.cursor()
        
        # Get users from instance
        instance_cursor.execute("SELECT id, username, email, password_hash, is_active, created_at, last_login FROM users")
        users = instance_cursor.fetchall()
        
        for user in users:
            user_id, username, email, password_hash, is_active, created_at, last_login = user
            
            # Check if user already exists in main
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("""
                    INSERT INTO users (id, username, email, password_hash, is_active, created_at, last_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, email, password_hash, is_active, created_at, last_login))
                print(f"   ✓ Migrated user: {username}")
            else:
                print(f"   ℹ User already exists: {username}")
        
        # Get user_roles from instance
        print("\n5. Migrating user roles...")
        instance_cursor.execute("SELECT user_id, role_id FROM user_roles")
        user_roles = instance_cursor.fetchall()
        
        for user_id, role_id in user_roles:
            cursor.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id) VALUES (?, ?)", 
                        (user_id, role_id))
        print(f"   ✓ Migrated {len(user_roles)} user-role assignments")
        
        instance_conn.close()
    
    # 5. Get admin user ID
    print("\n6. Setting up dataset ownership...")
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    admin = cursor.fetchone()
    
    if admin:
        admin_id = admin[0]
        # Update all datasets without owner to belong to admin
        cursor.execute("UPDATE datasets SET owner_id = ? WHERE owner_id IS NULL", (admin_id,))
        updated = cursor.rowcount
        print(f"   ✓ Assigned {updated} datasets to admin")
        
        # Create workspace for admin if not exists
        cursor.execute("SELECT id FROM user_workspaces WHERE user_id = ?", (admin_id,))
        workspace = cursor.fetchone()
        if not workspace:
            cursor.execute("""
                INSERT INTO user_workspaces (user_id, name, description)
                VALUES (?, 'Admin Workspace', 'Default workspace for admin user')
            """, (admin_id,))
            print("   ✓ Created workspace for admin")
    else:
        print("   ⚠ No admin user found! Run: python scripts/create_admin_user.py")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    # 6. Remove instance database
    if instance_db.exists():
        print(f"\n7. Removing instance database...")
        instance_db.unlink()
        print(f"   ✓ Removed {instance_db}")
        
        # Remove instance directory if empty
        instance_dir = Path("instance")
        if instance_dir.exists() and not any(instance_dir.iterdir()):
            instance_dir.rmdir()
            print(f"   ✓ Removed empty instance directory")
    
    print("\n=== Consolidation Complete ===")
    print(f"✓ All data consolidated into: {main_db}")
    print(f"✓ Backup saved as: {backup_db}")
    print(f"\nNext steps:")
    print(f"  1. Update config to use: {main_db.absolute()}")
    print(f"  2. Start application: python -m src.web")
    print(f"  3. Access admin at: http://127.0.0.1:5000/admin")


if __name__ == '__main__':
    consolidate_databases()
