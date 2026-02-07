from flask import Blueprint, jsonify

from ..models.menu import get_menu_items, get_menu_item_detail, get_menu_item_bom

menu_bp = Blueprint("menu", __name__)


@menu_bp.route("/api/restaurants/<int:restaurant_id>/menu")
def list_menu(restaurant_id):
    rows = get_menu_items(restaurant_id)
    return jsonify(rows)


@menu_bp.route("/api/menu-items/<int:menu_item_id>")
def menu_item_detail(menu_item_id):
    item = get_menu_item_detail(menu_item_id)
    if not item:
        return jsonify({"error": "Menu item not found"}), 404

    bom = get_menu_item_bom(menu_item_id)
    result = dict(item)
    result["ingredients"] = bom
    return jsonify(result)
