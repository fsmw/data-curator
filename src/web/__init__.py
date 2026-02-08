import os
from flask import Flask
from flask_admin import Admin

from .routes import ui_bp
from .api import api_bp  # New API Blueprint


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

    # Configure SQLAlchemy
    from src.config import Config
    config = Config()
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{config.data_root / 'datasets_catalog.db'}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize SQLAlchemy
    from src.models import db
    db.init_app(app)

    # Initialize Flask-Admin
    from src.admin_views import (
        SecureAdminIndexView, DatasetAdminView,
        DatasetColumnAdminView, IndicatorAdminView
    )
    from src.models import Dataset, DatasetColumn, Indicator

    admin = Admin(
        app,
        name='Data Curator Admin',
        template_mode='bootstrap4',
        index_view=SecureAdminIndexView()
    )

    # Add admin views
    admin.add_view(DatasetAdminView(Dataset, db.session))
    admin.add_view(DatasetColumnAdminView(DatasetColumn, db.session))
    admin.add_view(IndicatorAdminView(Indicator, db.session))

    # Register blueprints
    app.register_blueprint(ui_bp)
    app.register_blueprint(api_bp)  # New: API routes under /api/*

    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
