from ..utils.query import execute_query, execute_one, execute_modify


def get_all_ingredients():
    """Full ingredient catalog (for picker UI)."""
    return execute_query("""
        SELECT ingredient_id, ingredient_name, unit, unit_cost, is_active
        FROM ingredients
        WHERE is_active = TRUE
        ORDER BY ingredient_name
    """)


def get_restaurant_ingredients(restaurant_id):
    """Ingredients actively stocked by a restaurant."""
    return execute_query("""
        SELECT i.ingredient_id, i.ingredient_name, i.unit, i.unit_cost,
               ri.lead_time_days, ri.safety_stock_days, ri.first_stocked_date
        FROM restaurant_ingredients ri
        JOIN ingredients i ON i.ingredient_id = ri.ingredient_id
        WHERE ri.restaurant_id = %s AND ri.is_active = TRUE
        ORDER BY i.ingredient_name
    """, (restaurant_id,))


def get_restaurant_ingredient(restaurant_id, ingredient_id):
    """Single ingredient detail for a restaurant."""
    return execute_one("""
        SELECT i.ingredient_id, i.ingredient_name, i.unit, i.unit_cost,
               ri.lead_time_days, ri.safety_stock_days, ri.first_stocked_date,
               ri.is_active
        FROM restaurant_ingredients ri
        JOIN ingredients i ON i.ingredient_id = ri.ingredient_id
        WHERE ri.restaurant_id = %s AND ri.ingredient_id = %s
    """, (restaurant_id, ingredient_id))


def add_restaurant_ingredient(restaurant_id, ingredient_id, lead_time_days=2, safety_stock_days=2):
    """Add an ingredient to a restaurant (or reactivate if soft-deleted)."""
    return execute_modify("""
        INSERT INTO restaurant_ingredients (restaurant_id, ingredient_id, lead_time_days, safety_stock_days)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (restaurant_id, ingredient_id)
        DO UPDATE SET is_active = TRUE,
                      lead_time_days = EXCLUDED.lead_time_days,
                      safety_stock_days = EXCLUDED.safety_stock_days
        RETURNING restaurant_id, ingredient_id, lead_time_days, safety_stock_days, is_active
    """, (restaurant_id, ingredient_id, lead_time_days, safety_stock_days))


def remove_restaurant_ingredient(restaurant_id, ingredient_id):
    """Soft-remove an ingredient from a restaurant."""
    return execute_modify("""
        UPDATE restaurant_ingredients
        SET is_active = FALSE
        WHERE restaurant_id = %s AND ingredient_id = %s
        RETURNING restaurant_id, ingredient_id, is_active
    """, (restaurant_id, ingredient_id))
