#!/usr/bin/env python3
"""CLI tool to create or update users for Mises Data Curator."""
import argparse
import sys
sys.path.insert(0, '/opt/data-curator')

from src.web import create_app
from src.models import db, User

def create_or_update_user(username, email, password, is_admin=False):
    """Create a new user or update existing user."""
    app = create_app()
    
    with app.app_context():
        # Verificar si el usuario ya existe
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        
        if existing_user and existing_email and existing_user.id != existing_email.id:
            print(f"❌ Error: El usuario '{username}' y el email '{email}' pertenecen a diferentes usuarios!")
            return False
        
        if existing_user:
            # Actualizar usuario existente
            print(f"ℹ️  El usuario '{username}' ya existe. Actualizando...")
            existing_user.email = email
            existing_user.set_password(password)
            # is_admin se maneja mediante roles, no directamente
            db.session.commit()
            print(f"✅ Usuario actualizado exitosamente!")
            print(f"   Username: {existing_user.username}")
            print(f"   Email: {existing_user.email}")
            print(f"   Nota: La contraseña ha sido actualizada")
            return True
        
        if existing_email:
            print(f"❌ Error: El email '{email}' ya está registrado por el usuario '{existing_email.username}'")
            print(f"   Use un email diferente o actualice el usuario existente.")
            return False
        
        # Crear nuevo usuario
        try:
            user = User(
                username=username,
                email=email
            )
            user.set_password(password)
            # is_admin se maneja mediante roles en el modelo
            
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ Usuario creado exitosamente!")
            print(f"   Username: {user.username}")
            print(f"   Email: {user.email}")
            print(f"   Password: {'*' * len(password)}")
            
            if is_admin:
                print(f"   ⚠️  Nota: Para asignar rol de administrador, use el panel de administración de Flask")
            
            return True
            
        except Exception as e:
            print(f"❌ Error al crear usuario: {e}")
            db.session.rollback()
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Create or update users for Mises Data Curator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Crear nuevo usuario
  python create_user.py -u admin -e admin@almacen.digital -p Almacen.2026.
  
  # Actualizar usuario existente (cambia contraseña y email)
  python create_user.py -u admin -e admin@almacen.digital -p NuevaPass123
  
  # Crear usuario normal
  python create_user.py -u fernando -e fernando@example.com -p miPassword123

Notes:
  - Si el usuario ya existe, se actualizará la contraseña y el email
  - Si el email ya está en uso por otro usuario, mostrará error
  - El rol de administrador se asigna desde el panel de admin de Flask
        '''
    )
    
    parser.add_argument('-u', '--username', required=True,
                        help='Nombre de usuario (requerido)')
    parser.add_argument('-e', '--email', required=True,
                        help='Email del usuario (requerido)')
    parser.add_argument('-p', '--password', required=True,
                        help='Contraseña del usuario (requerido)')
    parser.add_argument('-a', '--admin', action='store_true',
                        help='Intentar asignar rol de administrador (nota: requiere configuración adicional)')
    
    args = parser.parse_args()
    
    # Validaciones básicas
    if len(args.password) < 6:
        print("❌ Error: La contraseña debe tener al menos 6 caracteres")
        sys.exit(1)
    
    if '@' not in args.email:
        print("❌ Error: El email no parece válido (falta @)")
        sys.exit(1)
    
    success = create_or_update_user(args.username, args.email, args.password, args.admin)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
