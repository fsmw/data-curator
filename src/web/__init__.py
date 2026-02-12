import os
from pathlib import Path
from flask import Flask, request
from flask_admin import Admin
from flask_login import LoginManager, current_user
from flask_babel import Babel

from .routes import ui_bp
from .api import api_bp  # New API Blueprint
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
        # Development fallback: use an ephemeral secret and warn the dev
        try:
            import secrets

            app.secret_key = secrets.token_hex(32)
            print("Warning: FLASK_SECRET_KEY not set. Using ephemeral secret key (development only). Set FLASK_SECRET_KEY in production.")
        except Exception:
            # Last resort fallback
            app.secret_key = "dev-secret"
            print("Warning: FLASK_SECRET_KEY not set and secrets unavailable. Using weak fallback key.")

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
    app.register_blueprint(api_bp)  # New: API routes under /api/*
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
            # Be permissive if current_user isn't available
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
    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.getenv("FLASK_RUN_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
