from flask import Flask

from .routes import ui_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.register_blueprint(ui_bp)
    app.config.setdefault("TEMPLATES_AUTO_RELOAD", True)
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
