from datetime import date, datetime
from decimal import Decimal

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS

from .config import Config


class CustomJSONProvider(DefaultJSONProvider):
    """Handle Decimal and date types from psycopg2."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.json_provider_class = CustomJSONProvider
    app.json = CustomJSONProvider(app)

    CORS(app)

    if Config.AUTO_MIGRATE:
        from .db import run_migrations
        run_migrations()

    from .routes.health import health_bp
    from .routes.restaurants import restaurants_bp
    from .routes.ingredients import ingredients_bp
    from .routes.inventory import inventory_bp
    from .routes.predictions import predictions_bp
    from .routes.dashboard import dashboard_bp
    from .routes.menu import menu_bp
    from .routes.batches import batches_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(ingredients_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(batches_bp)

    return app
