#!/usr/bin/env python3
"""CLI tool to create users for Mises Data Curator."""
import argparse
import sys
sys.path.insert(0, '/opt/data-curator')

from src.web import create_app
from src.models import db, User

def create_user(username, email, password, is_admin=False):
    app = create_app()
    
    with app.app_context():
        # Check if user already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"❌ Error: User '{username}' already exists!")
            print(f"   Email: {existing.email}")
            return False
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            print(f"❌ Error: Email '{email}' already exists!")
            print(f"   Username: {existing_email.username}")
            return False
        
        # Create new user
        user = User(
            username=username,
            email=email,
            is_active=True,
            is_admin=is_admin
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ User created successfully!")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Admin: {user.is_admin}")
        return True

def main():
    parser = argparse.ArgumentParser(
        description='Create users for Mises Data Curator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create admin user
  python create_user.py -u admin -e admin@almacen.digital -p Almacen.2026. --admin
  
  # Create regular user
  python create_user.py -u fernando -e fernando@example.com -p mypassword123
  
  # Short form
  python create_user.py -u admin -e admin@almacen.digital -p Almacen.2026. -a
        '''
    )
    
    parser.add_argument('-u', '--username', required=True,
                        help='Username for the new user')
    parser.add_argument('-e', '--email', required=True,
                        help='Email address for the new user')
    parser.add_argument('-p', '--password', required=True,
                        help='Password for the new user')
    parser.add_argument('-a', '--admin', action='store_true',
                        help='Make the user an administrator')
    
    args = parser.parse_args()
    
    success = create_user(args.username, args.email, args.password, args.admin)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
