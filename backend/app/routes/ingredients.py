from flask import Blueprint, jsonify, request

from ..models.ingredient import (
    get_all_ingredients,
    get_restaurant_ingredients,
    get_restaurant_ingredient,
    create_ingredient,
    add_restaurant_ingredient,
    remove_restaurant_ingredient,
)

ingredients_bp = Blueprint("ingredients", __name__)


@ingredients_bp.route("/api/ingredients")
def ingredient_catalog():
    """Full ingredient catalog (for picker)."""
    rows = get_all_ingredients()
    return jsonify(rows)


@ingredients_bp.route("/api/ingredients", methods=["POST"])
def create_new_ingredient():
    """Create a brand-new ingredient in the catalog."""
    data = request.get_json(force=True)
    name = data.get("ingredient_name")
    unit = data.get("unit")
    if not name or not unit:
        return jsonify({"error": "ingredient_name and unit are required"}), 400

    result = create_ingredient(
        ingredient_name=name,
        unit=unit,
        unit_cost=data.get("unit_cost", 0),
        category=data.get("category"),
        shelf_life_days=data.get("shelf_life_days"),
    )
    return jsonify(result), 201


@ingredients_bp.route("/api/restaurants/<int:restaurant_id>/ingredients")
def list_restaurant_ingredients(restaurant_id):
    rows = get_restaurant_ingredients(restaurant_id)
    return jsonify(rows)


@ingredients_bp.route("/api/restaurants/<int:restaurant_id>/ingredients/<int:ingredient_id>")
def restaurant_ingredient_detail(restaurant_id, ingredient_id):
    row = get_restaurant_ingredient(restaurant_id, ingredient_id)
    if not row:
        return jsonify({"error": "Ingredient not found for this restaurant"}), 404
    return jsonify(row)


@ingredients_bp.route("/api/restaurants/<int:restaurant_id>/ingredients", methods=["POST"])
def add_ingredient(restaurant_id):
    data = request.get_json(force=True)
    ingredient_id = data.get("ingredient_id")
    if not ingredient_id:
        return jsonify({"error": "ingredient_id is required"}), 400

    result = add_restaurant_ingredient(
        restaurant_id,
        ingredient_id,
        data.get("lead_time_days", 2),
        data.get("safety_stock_days", 2),
    )
    return jsonify(result), 201


@ingredients_bp.route(
    "/api/restaurants/<int:restaurant_id>/ingredients/<int:ingredient_id>",
    methods=["DELETE"],
)
def delete_ingredient(restaurant_id, ingredient_id):
    result = remove_restaurant_ingredient(restaurant_id, ingredient_id)
    if not result:
        return jsonify({"error": "Ingredient not found"}), 404
    return jsonify(result)
