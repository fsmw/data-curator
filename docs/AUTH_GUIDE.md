# Sistema de Autenticación RBAC

## Resumen

Sistema completo de autenticación y autorización basado en roles (RBAC) implementado con Flask-Login y Flask-Admin.

## Estructura de Roles

### Roles disponibles:
1. **admin** - Acceso total al sistema y panel de administración
2. **user** - Acceso a la aplicación web pero no al panel admin

## Usuarios

### Usuario Admin por defecto:
- **Username**: admin
- **Password**: admin123
- **Roles**: admin

## Accesos

### Requieren autenticación:
- Todas las páginas de la aplicación (`/`, `/search`, `/browse_local`, etc.)
- Panel de administración (`/admin`)

### Público:
- Página de login (`/auth/login`)
- Página de logout (`/auth/logout`)

## Gestión de Usuarios

### Crear usuarios desde línea de comandos:
```bash
python scripts/create_admin_user.py --username nuevo_usuario --password contraseña --email usuario@ejemplo.com
```

### Asignar roles en Flask-Admin:
1. Ir a `/admin`
2. Hacer login con usuario admin
3. Ir a "User" en el menú
4. Crear/editar usuario
5. Seleccionar roles (admin y/o user)

### Gestionar roles:
En Flask-Admin > "Role" se pueden:
- Ver roles existentes
- Crear nuevos roles
- Asignar descripciones

## Seguridad

- Contraseñas hasheadas con bcrypt
- Sesiones manejadas por Flask-Login
- Redirección automática a login si no autenticado
- Solo usuarios con rol 'admin' pueden acceder a `/admin`

## URLs importantes

- **Login**: `/auth/login`
- **Logout**: `/auth/logout`
- **Admin**: `/admin` (requiere rol admin)
- **App**: `/` (requiere autenticación)

## Comandos útiles

```bash
# Inicializar base de datos (crea tablas y roles)
python scripts/init_admin.py

# Crear usuario admin
python scripts/create_admin_user.py

# Crear usuario normal
python scripts/create_admin_user.py --username usuario --password pass123 --email user@example.com
# Luego asignar rol 'user' desde Flask-Admin
```
