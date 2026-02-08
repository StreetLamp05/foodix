from ..utils.query import execute_query, execute_one, execute_modify


def get_current_levels(restaurant_id):
    """Latest inventory row per ingredient for this restaurant."""
    return execute_query("""
        SELECT DISTINCT ON (d.ingredient_id)
               d.ingredient_id, i.ingredient_name, i.unit,
               i.category, i.shelf_life_days,
               d.log_date, d.inventory_start, d.qty_used,
               d.inventory_end, d.on_order_qty,
               d.avg_daily_usage_7d, d.avg_daily_usage_28d
        FROM daily_inventory_log d
        JOIN ingredients i ON i.ingredient_id = d.ingredient_id
        JOIN restaurant_ingredients ri
          ON ri.restaurant_id = d.restaurant_id
         AND ri.ingredient_id = d.ingredient_id
         AND ri.is_active = TRUE
        WHERE d.restaurant_id = %s
        ORDER BY d.ingredient_id, d.log_date DESC
    """, (restaurant_id,))


def get_history(restaurant_id, ingredient_id, days=30):
    """Usage history for charts."""
    return execute_query("""
        SELECT log_date, inventory_start, qty_used, stockout_qty,
               inventory_end, on_order_qty,
               avg_daily_usage_7d, avg_daily_usage_28d,
               covers, seasonality_factor
        FROM daily_inventory_log
        WHERE restaurant_id = %s AND ingredient_id = %s
          AND log_date >= CURRENT_DATE - %s * INTERVAL '1 day'
        ORDER BY log_date
    """, (restaurant_id, ingredient_id, days))


def upsert_usage(restaurant_id, ingredient_id, qty_used):
    """Log usage for today. Upserts: INSERT pulls most recent end as today's start, UPDATE accumulates."""
    return execute_modify("""
        INSERT INTO daily_inventory_log
            (restaurant_id, ingredient_id, log_date, inventory_start, qty_used, inventory_end)
        VALUES (
            %s, %s, CURRENT_DATE,
            COALESCE(
                (SELECT inventory_end FROM daily_inventory_log
                 WHERE restaurant_id = %s AND ingredient_id = %s
                   AND log_date < CURRENT_DATE
                 ORDER BY log_date DESC LIMIT 1),
                0
            ),
            %s,
            COALESCE(
                (SELECT inventory_end FROM daily_inventory_log
                 WHERE restaurant_id = %s AND ingredient_id = %s
                   AND log_date < CURRENT_DATE
                 ORDER BY log_date DESC LIMIT 1),
                0
            ) - %s
        )
        ON CONFLICT (restaurant_id, ingredient_id, log_date)
        DO UPDATE SET qty_used      = daily_inventory_log.qty_used + EXCLUDED.qty_used,
                      inventory_end = daily_inventory_log.inventory_end - EXCLUDED.qty_used
        RETURNING id, log_date, inventory_start, qty_used, inventory_end
    """, (restaurant_id, ingredient_id,
          restaurant_id, ingredient_id,
          qty_used,
          restaurant_id, ingredient_id,
          qty_used))


def upsert_restock(restaurant_id, ingredient_id, restock_qty):
    """Log a restock for today. Adds to on_order_qty and inventory_end."""
    return execute_modify("""
        INSERT INTO daily_inventory_log
            (restaurant_id, ingredient_id, log_date, inventory_start, qty_used, inventory_end, on_order_qty)
        VALUES (
            %s, %s, CURRENT_DATE,
            COALESCE(
                (SELECT inventory_end FROM daily_inventory_log
                 WHERE restaurant_id = %s AND ingredient_id = %s
                   AND log_date < CURRENT_DATE
                 ORDER BY log_date DESC LIMIT 1),
                0
            ),
            0,
            COALESCE(
                (SELECT inventory_end FROM daily_inventory_log
                 WHERE restaurant_id = %s AND ingredient_id = %s
                   AND log_date < CURRENT_DATE
                 ORDER BY log_date DESC LIMIT 1),
                0
            ) + %s,
            %s
        )
        ON CONFLICT (restaurant_id, ingredient_id, log_date)
        DO UPDATE SET inventory_end = daily_inventory_log.inventory_end + EXCLUDED.on_order_qty,
                      on_order_qty  = daily_inventory_log.on_order_qty + EXCLUDED.on_order_qty
        RETURNING id, log_date, inventory_start, qty_used, inventory_end, on_order_qty
    """, (restaurant_id, ingredient_id,
          restaurant_id, ingredient_id,
          restaurant_id, ingredient_id,
          restock_qty,
          restock_qty))
