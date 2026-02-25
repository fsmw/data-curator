import os
import atexit
from pathlib import Path
from flask import Flask, request
from datetime import timedelta
from flask_admin import Admin
from flask_login import LoginManager, current_user
from flask_babel import Babel

from .routes import ui_bp
from .api import api_bp  # New API Blueprint
from .auth import auth_bp
from .jupyter_manager import JupyterManager
from .jupyter_proxy import create_jupyter_proxy_blueprint, register_jupyter_websocket_proxy

# Internationalization
babel = Babel()
SUPPORTED_LOCALES = ["es_CL", "en_US"]

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Variable global para almacenar el prefijo
_url_prefix = ''


def create_app() -> Flask:
    # Detectar si estamos detrás de un proxy con prefijo
    script_name = os.getenv('SCRIPT_NAME', '')
    
    # Configurar static_url_path si hay un prefijo
    static_url_path = '/static'
    if script_name:
        static_url_path = script_name.rstrip('/') + '/static'
    
    app = Flask(__name__, 
                static_folder="static", 
                static_url_path=static_url_path,
                template_folder="templates")

    # IMPORTANTE: Configurar para proxy inverso con prefijo
    # x_prefix=1 para confiar en 1 nivel de proxy (nginx)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)
    
    # Aplicar prefijo si está configurado
    if script_name:
        app.config['APPLICATION_ROOT'] = script_name

    # Ensure a SECRET_KEY for Flask sessions. Prefer environment variable for production.
    secret = os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY")
    if secret:
        app.secret_key = secret
    else:
        # Development fallback: use a persistent secret key from file
        secret_file = Path(__file__).parent.parent.parent / '.secret_key'
        try:
            if secret_file.exists():
                # Read existing secret key
                app.secret_key = secret_file.read_text().strip()
            else:
                # Generate new secret key and save it
                import secrets
                new_secret = secrets.token_hex(32)
                secret_file.write_text(new_secret)
                app.secret_key = new_secret
                print(f"Generated new persistent SECRET_KEY and saved to {secret_file}")
                print("Note: Set FLASK_SECRET_KEY environment variable for production.")
        except Exception as e:
            # Last resort fallback
            app.secret_key = "dev-secret-fallback"
            print(f"Warning: Could not read/write secret key file: {e}")
            print("Using weak fallback key. Sessions will not persist across restarts.")

    # Configure SQLAlchemy - use absolute path to ensure consistency
    from src.config import Config
    config = Config()
    db_path = (config.data_root / 'datasets_catalog.db').absolute()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize SQLAlchemy
    from src.models import db, User
    db.init_app(app)

    # Initialize Flask-Login
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    # Handler personalizado para redirecciones de login que respete el prefijo
    @login_manager.unauthorized_handler
    def handle_unauthorized():
        from flask import redirect, url_for, request
        # Obtener el path relativo (sin el dominio y sin el prefijo SCRIPT_NAME)
        next_path = request.path
        if request.query_string:
            next_path += '?' + request.query_string.decode('utf-8')
        login_url = url_for('auth.login', next=next_path)
        return redirect(login_url)

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
    app.register_blueprint(api_bp)  # New: API routes under /api/*
    app.register_blueprint(auth_bp)

    # Optional Jupyter integration lifecycle
    jupyter_enabled = os.getenv("JUPYTER_ENABLE", "0").strip().lower() in {"1", "true", "yes", "on"}
    jupyter_port = int(os.getenv("JUPYTER_PORT", "8888"))
    flask_port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    notebooks_dir = os.getenv(
        "JUPYTER_NOTEBOOK_DIR",
        str((config.data_root / "notebooks").absolute()),
    )
    jupyter_config_dir = os.getenv(
        "JUPYTER_CONFIG_DIR",
        str((Path(__file__).parent.parent.parent / "jupyter_config").absolute()),
    )
    jupyter_template_seed_dir = os.getenv(
        "JUPYTER_TEMPLATE_SEED_DIR",
        str((Path(jupyter_config_dir) / "notebook_templates").absolute()),
    )
    # Get app prefix for Jupyter base_url (e.g., "/misesdata" in production)
    app_prefix = app.config.get("APPLICATION_ROOT", "") or ""

    manager = JupyterManager(
        port=jupyter_port,
        notebook_dir=notebooks_dir,
        config_dir=jupyter_config_dir,
        template_seed_dir=jupyter_template_seed_dir,
        db_path=str(db_path),
        flask_port=flask_port,
        enabled=jupyter_enabled,
        app_prefix=app_prefix,
    )
    app.extensions["jupyter_manager"] = manager
    app.register_blueprint(create_jupyter_proxy_blueprint())
    jupyter_sock = register_jupyter_websocket_proxy(app)
    if jupyter_sock is not None:
        app.extensions["jupyter_sock"] = jupyter_sock
    manager.ensure_notebook_dirs()
    manager.provision_templates()
    if jupyter_enabled:
        manager.start()
        atexit.register(manager.stop)

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
        except (RuntimeError, AttributeError):
            # Be permissive if current_user isn't available yet
            pass

        # Use the request Accept-Language header to find the best match
        best = request.accept_languages.best_match(SUPPORTED_LOCALES)
        return best or "es_CL"

    # Initialize Babel after app and blueprints are registered
    # Pass the full translations directory path and locale selector to init_app
    translations_path = str(translations_dir.absolute())
    babel.init_app(app, default_translation_directories=translations_path, locale_selector=get_locale)

    # Add get_locale to template context
    @app.context_processor
    def inject_locale():
        return dict(get_locale=get_locale)

    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    app.config.setdefault("REMEMBER_COOKIE_DURATION", timedelta(days=30))
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(days=7))
    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.getenv("FLASK_RUN_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
