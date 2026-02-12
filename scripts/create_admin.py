#!/usr/bin/env python3
"""Script to create admin user"""
import sys
sys.path.insert(0, '/opt/data-curator')

from src.web import create_app
from src.models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Check if user already exists
    existing = User.query.filter_by(username='admin').first()
    if existing:
        print("User 'admin' already exists!")
        print(f"Username: {existing.username}")
        print(f"Email: {existing.email}")
        sys.exit(0)
    
    # Create new admin user
    admin = User(
        username='admin',
        email='admin@almacen.digital',
        is_active=True,
        is_admin=True
    )
    admin.set_password('Almacen.2026.')
    
    db.session.add(admin)
    db.session.commit()
    
    print("✅ Admin user created successfully!")
    print(f"Username: {admin.username}")
    print(f"Email: {admin.email}")
    print(f"Is Admin: {admin.is_admin}")
