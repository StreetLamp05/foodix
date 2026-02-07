from flask import Blueprint, jsonify

from ..models.restaurant import get_all_restaurants, get_restaurant_by_id

restaurants_bp = Blueprint("restaurants", __name__)


@restaurants_bp.route("/api/restaurants")
def list_restaurants():
    rows = get_all_restaurants()
    return jsonify(rows)


@restaurants_bp.route("/api/restaurants/<int:restaurant_id>")
def restaurant_detail(restaurant_id):
    row = get_restaurant_by_id(restaurant_id)
    if not row:
        return jsonify({"error": "Restaurant not found"}), 404
    return jsonify(row)
