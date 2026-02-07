from flask import Flask
from flask_cors import CORS

from .config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    if Config.AUTO_MIGRATE:
        from .db import run_migrations
        run_migrations()

    from .routes.health import health_bp
    app.register_blueprint(health_bp)

    return app
