#!/usr/bin/env python3
"""Create admin user script with RBAC."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web import create_app
from src.models import db, User, Role


def create_admin_user(username='admin', password='admin123', email='admin@example.com'):
    """Create an admin user with admin role."""
    app = create_app()

    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"✓ User '{username}' already exists")
            # Ensure user has admin role
            admin_role = Role.query.filter_by(name='admin').first()
            if admin_role and admin_role not in existing_user.roles:
                existing_user.roles.append(admin_role)
                db.session.commit()
                print(f"✓ Added admin role to '{username}'")
            return

        # Get admin role
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            # Create roles if they don't exist
            admin_role = Role(name='admin', description='Administrator with full access')
            user_role = Role(name='user', description='Standard user with limited access')
            db.session.add(admin_role)
            db.session.add(user_role)
            db.session.commit()
            print("✓ Created roles: admin, user")

        # Create admin user
        user = User(
            username=username,
            email=email,
            is_active=True
        )
        user.set_password(password)
        user.roles.append(admin_role)

        db.session.add(user)
        db.session.commit()

        print(f"✓ Admin user created successfully!")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"  Email: {email}")
        print(f"  Roles: admin")
        print(f"\nYou can now log in at: http://127.0.0.1:5000/auth/login")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Create admin user')
    parser.add_argument('--username', default='admin', help='Username (default: admin)')
    parser.add_argument('--password', default='admin123', help='Password (default: admin123)')
    parser.add_argument('--email', default='admin@example.com', help='Email (default: admin@example.com)')

    args = parser.parse_args()

    create_admin_user(args.username, args.password, args.email)
