# Configuración Nginx con Prefijo /misesdata

## Configuración de Nginx

Edita tu archivo de configuración de nginx:

```bash
sudo nano /etc/nginx/sites-available/tu-sitio
```

Añade la siguiente configuración dentro del bloque `server`:

```nginx
# Redirigir /misesdata (sin slash final) a /misesdata/
location = /misesdata {
    return 301 /misesdata/;
}

# Proxy inverso para la aplicación
location /misesdata/ {
    # Remover el prefijo /misesdata antes de enviar a Flask
    rewrite ^/misesdata/(.*) /$1 break;
    
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    
    # Headers esenciales para Flask
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Prefix /misesdata;
    
    # Soporte para websockets (si los usas)
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Timeouts
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
}

# Archivos estáticos (opcional - mejora rendimiento)
location /misesdata/static/ {
    alias /opt/data-curator/src/web/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## Configuración de Flask

Necesitas modificar la aplicación Flask para que entienda que está detrás del prefijo /misesdata.

Edita el archivo `src/web/__init__.py`:

```python
import os
from pathlib import Path
from flask import Flask, request
from flask_admin import Admin
from flask_login import LoginManager, current_user
from flask_babel import Babel

from .routes import ui_bp
from .api import api_bp
from .auth import auth_bp

# Internationalization
babel = Babel()
SUPPORTED_LOCALES = ["es_CL", "en_US"]

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    
    # IMPORTANTE: Configurar para proxy inverso con prefijo
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
    
    # Configuración de SECRET_KEY
    secret = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY")
    if secret:
        app.secret_key = secret
    else:
        import secrets
        app.secret_key = secrets.token_hex(32)
        print("Warning: FLASK_SECRET_KEY not set. Using ephemeral secret key.")
    
    # Configurar SQLAlchemy
    from src.config import Config
    config = Config()
    db_path = (config.data_root / 'datasets_catalog.db').absolute()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Aplicar prefijo si está configurado
    script_name = os.getenv('SCRIPT_NAME', '')
    if script_name:
        app.config['APPLICATION_ROOT'] = script_name
    
    # Initialize SQLAlchemy
    from src.models import db, User
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize Flask-Admin
    from src.admin_views import (
        SecureAdminIndexView, DatasetAdminView,
        DatasetColumnAdminView, IndicatorAdminView,
        UserAdminView, RoleAdminView,
        UserDatasetAccessAdminView, UserWorkspaceAdminView
    )
    from src.models import (
        Dataset, DatasetColumn, Indicator, Role,
        UserDatasetAccess, UserWorkspace
    )
    
    admin = Admin(
        app,
        name='Data Curator Admin',
        index_view=SecureAdminIndexView()
    )
    
    # Add admin views
    admin.add_view(DatasetAdminView(Dataset, db.session))
    admin.add_view(DatasetColumnAdminView(DatasetColumn, db.session))
    admin.add_view(IndicatorAdminView(Indicator, db.session))
    admin.add_view(UserAdminView(User, db.session))
    admin.add_view(RoleAdminView(Role, db.session))
    admin.add_view(UserDatasetAccessAdminView(UserDatasetAccess, db.session,
                                             name='Permissions',
                                             category='Access Control'))
    admin.add_view(UserWorkspaceAdminView(UserWorkspace, db.session,
                                         name='Workspaces'))
    
    # Register blueprints
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    
    # Get the parent directory of src/web (i.e., repository root)
    app_root = Path(__file__).parent.parent.parent
    translations_dir = app_root / 'translations'
    
    # Locale selector: prefer user workspace setting, then Accept-Language header, then fallback
    def get_locale():
        try:
            if current_user and getattr(current_user, 'is_authenticated', False):
                ws = getattr(current_user, 'workspace', None)
                if ws and getattr(ws, 'language', None):
                    return ws.language
        except Exception:
            pass
        
        # Use the request Accept-Language header to find the best match
        best = request.accept_languages.best_match(SUPPORTED_LOCALES)
        return best or "es_CL"
    
    # Initialize Babel after app and blueprints are registered
    translations_path = str(translations_dir.absolute())
    babel.init_app(app, default_translation_directories=translations_path, locale_selector=get_locale)
    
    # Add get_locale to template context
    @app.context_processor
    def inject_locale():
        return dict(get_locale=get_locale)
    
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.getenv("FLASK_RUN_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
```

## Configuración del Servicio Systemd

Edita el archivo de servicio para agregar el prefijo:

```bash
sudo nano /etc/systemd/system/mises-data.service
```

Añade esta variable de entorno:

```ini
[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/data-curator
Environment="PATH=/opt/data-curator/.venv/bin"
Environment="FLASK_APP=src.web"
Environment="FLASK_ENV=production"
Environment="FLASK_SECRET_KEY=tu-clave-secreta-aqui"
Environment="FLASK_RUN_PORT=5000"
# IMPORTANTE: Configurar el prefijo para la aplicación
Environment="SCRIPT_NAME=/misesdata"
ExecStart=/opt/data-curator/.venv/bin/python -m src.web
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

## Aplicar Cambios

```bash
# 1. Recargar systemd
sudo systemctl daemon-reload

# 2. Reiniciar el servicio
sudo systemctl restart mises-data

# 3. Verificar configuración de nginx
sudo nginx -t

# 4. Recargar nginx
sudo systemctl reload nginx

# 5. Verificar estado
sudo systemctl status mises-data
sudo journalctl -u mises-data -f
```

## Verificar Funcionamiento

La aplicación debería estar disponible en:
- `http://tu-dominio.com/misesdata/`
- `http://tu-dominio.com/misesdata/status`
- `http://tu-dominio.com/misesdata/search`
- etc.

## Solución de Problemas

### Error: URLs no funcionan correctamente

Verifica que `ProxyFix` esté configurado:
```bash
curl -I http://127.0.0.1:5000/status
```

Debería redirigir correctamente.

### Error: Archivos estáticos no cargan

Verifica la ruta en nginx:
```bash
ls -la /opt/data-curator/src/web/static/
```

Y verifica los logs:
```bash
sudo tail -f /var/log/nginx/error.log
```

### Error: Redirecciones incorrectas

Si Flask redirige a `/login` en lugar de `/misesdata/login`, verifica que:
1. `ProxyFix` esté importado y configurado
2. La variable `SCRIPT_NAME` esté definida en el servicio
3. El header `X-Forwarded-Prefix` esté configurado en nginx

## Configuración Alternativa (Más Simple)

Si prefieres no modificar el código Python, puedes usar solo nginx con `sub_filter`:

```nginx
location /misesdata/ {
    proxy_pass http://127.0.0.1:5000/;
    
    # Reescribir URLs en el HTML (experimental)
    sub_filter 'href="/' 'href="/misesdata/';
    sub_filter 'src="/' 'src="/misesdata/';
    sub_filter_once off;
    
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Nota**: Esta opción es menos robusta y puede no funcionar con todo el contenido dinámico.
