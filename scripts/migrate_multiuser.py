#!/usr/bin/env python3
"""Migrate existing database to multi-user schema with admin management."""

import sys
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web import create_app
from src.models import db, User, Role, UserWorkspace, Dataset


def migrate_database():
    """Migrate database schema and data."""
    print("Starting database migration...")

    app = create_app()

    with app.app_context():
        # Create all new tables
        db.create_all()
        print("✓ Created new tables (UserWorkspace, UserDatasetAccess)")

        # Check if we need to add columns to existing datasets table
        from src.config import Config
        config = Config()
        db_path = config.data_root / "datasets_catalog.db"

        if db_path.exists():
            print(f"\nMigrating existing database: {db_path}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Add new columns to datasets table if they don't exist
            columns_to_add = [
                ('owner_id', 'INTEGER'),
                ('is_public', 'BOOLEAN DEFAULT 0'),
                ('is_shared', 'BOOLEAN DEFAULT 0'),
            ]

            for col_name, col_type in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE datasets ADD COLUMN {col_name} {col_type}")
                    print(f"  ✓ Added column: {col_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column" in str(e).lower():
                        print(f"  ℹ Column {col_name} already exists")
                    else:
                        print(f"  ⚠ Error adding {col_name}: {e}")

            conn.commit()
            conn.close()
            print("✓ Database schema migrated")

        # Ensure admin user exists
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator with full access')
            db.session.add(admin_role)
            print("✓ Created admin role")

        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user', description='Standard user with limited access')
            db.session.add(user_role)
            print("✓ Created user role")

        db.session.commit()

        # Check for admin user
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("\n⚠ No admin user found!")
            print("Run: python scripts/create_admin_user.py")
        else:
            print(f"\n✓ Admin user exists: {admin_user.username}")

            # Assign admin role if not already assigned
            if admin_role not in admin_user.roles:
                admin_user.roles.append(admin_role)
                db.session.commit()
                print("✓ Assigned admin role to admin user")

            # Update existing datasets to belong to admin
            datasets_without_owner = Dataset.query.filter(Dataset.owner_id.is_(None)).all()
            if datasets_without_owner:
                print(f"\n  Assigning {len(datasets_without_owner)} existing datasets to admin...")
                for dataset in datasets_without_owner:
                    dataset.owner_id = admin_user.id
                db.session.commit()
                print(f"  ✓ Assigned {len(datasets_without_owner)} datasets to admin")

        print("\n✓ Migration complete!")
        print(f"\nNext steps:")
        print(f"  1. Run: python scripts/create_admin_user.py (if not exists)")
        print(f"  2. Start the application: python -m src.web")
        print(f"  3. Access admin at: http://127.0.0.1:5000/admin")


if __name__ == '__main__':
    migrate_database()
