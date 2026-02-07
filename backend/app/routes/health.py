from datetime import datetime, timezone

from flask import Blueprint, jsonify

from ..db import test_connection

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health")
def health():
    db_connected = test_connection()
    return jsonify({
        "status": "healthy",
        "database": "connected" if db_connected else "disconnected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
