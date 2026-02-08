from flask import Blueprint, jsonify, request

from ..models.menu import (
    get_menu_items,
    get_menu_item_detail,
    get_menu_item_bom,
    create_menu_item,
    delete_menu_item,
    add_menu_item_ingredient,
    remove_menu_item_ingredient,
)

menu_bp = Blueprint("menu", __name__)


@menu_bp.route("/api/restaurants/<int:restaurant_id>/menu")
def list_menu(restaurant_id):
    rows = get_menu_items(restaurant_id)
    return jsonify(rows)


@menu_bp.route("/api/restaurants/<int:restaurant_id>/menu", methods=["POST"])
def create_menu(restaurant_id):
    data = request.get_json(force=True)
    item_name = (data.get("item_name") or "").strip()
    price = data.get("price")

    if not item_name:
        return jsonify({"error": "item_name is required"}), 400

    try:
        price = float(price)
    except (TypeError, ValueError):
        return jsonify({"error": "price must be a number"}), 400

    if price < 0:
        return jsonify({"error": "price must be >= 0"}), 400

    result = create_menu_item(restaurant_id, item_name, price)
    return jsonify(result), 201


@menu_bp.route("/api/menu-items/<int:menu_item_id>")
def menu_item_detail(menu_item_id):
    item = get_menu_item_detail(menu_item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    bom = get_menu_item_bom(menu_item_id)
    result = dict(item)
    result["ingredients"] = bom
    return jsonify(result)


@menu_bp.route("/api/menu-items/<int:menu_item_id>", methods=["DELETE"])
def menu_item_remove(menu_item_id):
    result = delete_menu_item(menu_item_id)
    if not result:
        return jsonify({"error": "Menu item not found"}), 404
    return jsonify(result)


@menu_bp.route("/api/menu-items/<int:menu_item_id>/ingredients", methods=["POST"])
def menu_item_add_ingredient(menu_item_id):
    data = request.get_json(force=True)
    ingredient_id = data.get("ingredient_id")
    qty_per_item = data.get("qty_per_item")

    if ingredient_id is None:
        return jsonify({"error": "ingredient_id is required"}), 400

    try:
        ingredient_id = int(ingredient_id)
    except (TypeError, ValueError):
        return jsonify({"error": "ingredient_id must be an integer"}), 400

    try:
        qty_per_item = float(qty_per_item)
    except (TypeError, ValueError):
        return jsonify({"error": "qty_per_item must be a number"}), 400

    if qty_per_item <= 0:
        return jsonify({"error": "qty_per_item must be > 0"}), 400

    result = add_menu_item_ingredient(menu_item_id, ingredient_id, qty_per_item)
    return jsonify(result), 201


@menu_bp.route(
    "/api/menu-items/<int:menu_item_id>/ingredients/<int:ingredient_id>",
    methods=["DELETE"],
)
def menu_item_remove_ingredient(menu_item_id, ingredient_id):
    result = remove_menu_item_ingredient(menu_item_id, ingredient_id)
    if not result:
        return jsonify({"error": "Ingredient not found in menu item"}), 404
    return jsonify(result)
