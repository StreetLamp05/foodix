from flask import Blueprint, jsonify, request

from ..models.batch import (
    get_batches,
    get_all_batches_for_restaurant,
    get_batch_by_id,
    create_batch,
    get_expiring_soon,
)

batches_bp = Blueprint("batches", __name__)


@batches_bp.route("/api/restaurants/<int:restaurant_id>/batches")
def list_batches(restaurant_id):
    """All active batches for a restaurant (across all ingredients)."""
    active_only = request.args.get("active_only", "true").lower() == "true"
    rows = get_all_batches_for_restaurant(restaurant_id, active_only=active_only)
    return jsonify(rows)


@batches_bp.route(
    "/api/restaurants/<int:restaurant_id>/ingredients/<int:ingredient_id>/batches"
)
def ingredient_batches(restaurant_id, ingredient_id):
    """Batches for a specific ingredient at a restaurant."""
    status = request.args.get("status")
    rows = get_batches(restaurant_id, ingredient_id, status=status)
    return jsonify(rows)


@batches_bp.route("/api/batches/<int:batch_id>")
def batch_detail(batch_id):
    row = get_batch_by_id(batch_id)
    if not row:
        return jsonify({"error": "Batch not found"}), 404
    return jsonify(row)


@batches_bp.route(
    "/api/restaurants/<int:restaurant_id>/ingredients/<int:ingredient_id>/batches",
    methods=["POST"],
)
def add_batch(restaurant_id, ingredient_id):
    """Record a new batch received.

    Body: {
        qty_received: N (required),
        supplier_name, supplier_contact, purchase_cost_per_unit,
        received_date, expiration_date (all optional)
    }
    """
    data = request.get_json(force=True)
    qty = data.get("qty_received")
    if not qty or qty <= 0:
        return jsonify({"error": "qty_received must be a positive number"}), 400

    result = create_batch(
        restaurant_id,
        ingredient_id,
        qty_received=qty,
        supplier_name=data.get("supplier_name"),
        supplier_contact=data.get("supplier_contact"),
        purchase_cost_per_unit=data.get("purchase_cost_per_unit"),
        received_date=data.get("received_date"),
        expiration_date=data.get("expiration_date"),
    )
    return jsonify(result), 201


@batches_bp.route("/api/restaurants/<int:restaurant_id>/batches/expiring-soon")
def expiring_soon(restaurant_id):
    """Batches expiring within N days (default 3)."""
    days = request.args.get("days", 3, type=int)
    rows = get_expiring_soon(restaurant_id, days)
    return jsonify(rows)
