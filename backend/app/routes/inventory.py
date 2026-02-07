from flask import Blueprint, jsonify, request

from ..services.inventory_service import (
    get_inventory_levels,
    get_inventory_history,
    log_usage,
    log_restock,
)
from ..models.batch import fifo_deduct

inventory_bp = Blueprint("inventory", __name__)


@inventory_bp.route("/api/restaurants/<int:restaurant_id>/inventory")
def current_levels(restaurant_id):
    rows = get_inventory_levels(restaurant_id)
    return jsonify(rows)


@inventory_bp.route(
    "/api/restaurants/<int:restaurant_id>/inventory/<int:ingredient_id>/history"
)
def history(restaurant_id, ingredient_id):
    days = request.args.get("days", 30, type=int)
    rows = get_inventory_history(restaurant_id, ingredient_id, days)
    return jsonify(rows)


@inventory_bp.route(
    "/api/restaurants/<int:restaurant_id>/inventory/<int:ingredient_id>/usage",
    methods=["POST"],
)
def post_usage(restaurant_id, ingredient_id):
    data = request.get_json(force=True)
    qty_used = data.get("qty_used")
    try:
        result = log_usage(restaurant_id, ingredient_id, qty_used)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # FIFO deduction from batches (best-effort — batches may not exist yet)
    try:
        fifo_result = fifo_deduct(restaurant_id, ingredient_id, qty_used)
        result["fifo"] = fifo_result
    except Exception:
        result["fifo"] = None

    return jsonify(result), 201


@inventory_bp.route(
    "/api/restaurants/<int:restaurant_id>/inventory/<int:ingredient_id>/restock",
    methods=["POST"],
)
def post_restock(restaurant_id, ingredient_id):
    data = request.get_json(force=True)
    restock_qty = data.get("restock_qty")
    try:
        result = log_restock(restaurant_id, ingredient_id, restock_qty)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify(result), 201
