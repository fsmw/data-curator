import os
from flask import Flask

from .routes import ui_bp


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

    app.register_blueprint(ui_bp)
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
