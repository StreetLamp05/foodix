from ..utils.query import execute_query, execute_one


def get_all_restaurants():
    return execute_query("""
        SELECT restaurant_id, restaurant_name, timezone, is_active, created_at
        FROM restaurants
        WHERE is_active = TRUE
        ORDER BY restaurant_name
    """)


def get_restaurant_by_id(restaurant_id):
    return execute_one("""
        SELECT restaurant_id, restaurant_name, timezone, is_active, created_at
        FROM restaurants
        WHERE restaurant_id = %s
    """, (restaurant_id,))
