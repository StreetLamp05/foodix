from flask import Blueprint, jsonify, request

from ..services.dashboard_service import get_overview, get_trends, get_top_movers

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/api/restaurants/<int:restaurant_id>/dashboard/overview")
def overview(restaurant_id):
    result = get_overview(restaurant_id)
    if not result:
        return jsonify({"error": "No data found"}), 404
    return jsonify(result)


@dashboard_bp.route("/api/restaurants/<int:restaurant_id>/dashboard/trends")
def trends(restaurant_id):
    days = request.args.get("days", 30, type=int)
    rows = get_trends(restaurant_id, days)
    return jsonify(rows)


@dashboard_bp.route("/api/restaurants/<int:restaurant_id>/dashboard/top-movers")
def top_movers(restaurant_id):
    limit = request.args.get("limit", 10, type=int)
    rows = get_top_movers(restaurant_id, limit)
    return jsonify(rows)
