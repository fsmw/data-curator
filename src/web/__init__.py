import os
from flask import Flask
from flask_admin import Admin
from flask_login import LoginManager

from .routes import ui_bp
from .api import api_bp  # New API Blueprint
from .auth import auth_bp

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

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

    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
