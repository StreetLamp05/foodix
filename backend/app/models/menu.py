from ..utils.query import execute_query, execute_one, execute_modify


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


def create_menu_item(restaurant_id, item_name, price):
    """Create a new active menu item for a restaurant."""
    return execute_modify("""
        INSERT INTO menu_items (restaurant_id, item_name, price, is_active)
        VALUES (%s, %s, %s, TRUE)
        RETURNING menu_item_id, item_name, price, is_active
    """, (restaurant_id, item_name, price))


def delete_menu_item(menu_item_id):
    """Soft-delete a menu item."""
    return execute_modify("""
        UPDATE menu_items
        SET is_active = FALSE
        WHERE menu_item_id = %s
        RETURNING menu_item_id, item_name, price, is_active
    """, (menu_item_id,))


def add_menu_item_ingredient(menu_item_id, ingredient_id, qty_per_item):
    """Add or update an ingredient BOM entry for a menu item."""
    return execute_modify("""
        INSERT INTO menu_item_ingredients (menu_item_id, ingredient_id, qty_per_item)
        VALUES (%s, %s, %s)
        ON CONFLICT (menu_item_id, ingredient_id)
        DO UPDATE SET qty_per_item = EXCLUDED.qty_per_item
        RETURNING menu_item_id, ingredient_id, qty_per_item
    """, (menu_item_id, ingredient_id, qty_per_item))


def remove_menu_item_ingredient(menu_item_id, ingredient_id):
    """Delete a BOM ingredient from a menu item."""
    return execute_modify("""
        DELETE FROM menu_item_ingredients
        WHERE menu_item_id = %s AND ingredient_id = %s
        RETURNING menu_item_id, ingredient_id
    """, (menu_item_id, ingredient_id))
