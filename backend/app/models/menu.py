from ..utils.query import execute_query, execute_one


def get_menu_items(restaurant_id):
    """All active menu items for a restaurant."""
    return execute_query("""
        SELECT menu_item_id, item_name, price, is_active
        FROM menu_items
        WHERE restaurant_id = %s AND is_active = TRUE
        ORDER BY item_name
    """, (restaurant_id,))


def get_menu_item_detail(menu_item_id):
    """Menu item with its ingredient bill of materials."""
    return execute_one("""
        SELECT m.menu_item_id, m.item_name, m.price, m.restaurant_id, m.is_active
        FROM menu_items m
        WHERE m.menu_item_id = %s
    """, (menu_item_id,))


def get_menu_item_bom(menu_item_id):
    """Bill of materials: ingredients that go into this menu item."""
    return execute_query("""
        SELECT mi.ingredient_id, i.ingredient_name, i.unit,
               mi.qty_per_item, i.unit_cost
        FROM menu_item_ingredients mi
        JOIN ingredients i ON i.ingredient_id = mi.ingredient_id
        WHERE mi.menu_item_id = %s
        ORDER BY i.ingredient_name
    """, (menu_item_id,))
