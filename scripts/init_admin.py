#!/usr/bin/env python3
"""Initialize Flask-Admin database tables with RBAC."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web import create_app
from src.models import db, Role, User


def init_admin():
    """Create admin tables with RBAC."""
    app = create_app()

    with app.app_context():
        # Create tables
        db.create_all()
        print("✓ Admin tables created successfully")

        # Create default roles
        roles = ['admin', 'user']
        for role_name in roles:
            existing = Role.query.filter_by(name=role_name).first()
            if not existing:
                role = Role(
                    name=role_name,
                    description=f'{role_name.capitalize()} role'
                )
                db.session.add(role)
                print(f"✓ Created role: {role_name}")

        db.session.commit()
        print("✓ Roles initialized")

        # Check if admin user exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            print("\n⚠ No admin user found!")
            print("Run: python scripts/create_admin_user.py")
        else:
            print(f"✓ Admin user exists: {admin_user.username}")


if __name__ == '__main__':
    init_admin()
