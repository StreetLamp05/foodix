from ..utils.query import execute_query, execute_one


def get_overview(restaurant_id):
    """Summary stats for the dashboard overview."""
    return execute_one("""
        WITH latest AS (
            SELECT DISTINCT ON (ingredient_id)
                   ingredient_id, inventory_end, avg_daily_usage_7d, on_order_qty
            FROM daily_inventory_log
            WHERE restaurant_id = %s
            ORDER BY ingredient_id, log_date DESC
        )
        SELECT
            COUNT(*)::int                                              AS total_ingredients,
            COUNT(*) FILTER (WHERE inventory_end <= 0)::int            AS stockout_count,
            COUNT(*) FILTER (
                WHERE avg_daily_usage_7d > 0
                  AND (inventory_end + COALESCE(on_order_qty, 0))
                      / avg_daily_usage_7d <= 3
                  AND inventory_end > 0
            )::int                                                     AS low_stock_count,
            ROUND(AVG(inventory_end)::numeric, 2)                      AS avg_inventory,
            ROUND(AVG(avg_daily_usage_7d)::numeric, 2)                 AS avg_daily_usage
        FROM latest
    """, (restaurant_id,))


def get_trends(restaurant_id, days=30):
    """Aggregated daily trends for charts."""
    return execute_query("""
        SELECT log_date,
               ROUND(SUM(qty_used)::numeric, 2)            AS total_used,
               ROUND(SUM(inventory_end)::numeric, 2)        AS total_inventory,
               ROUND(SUM(on_order_qty)::numeric, 2)         AS total_on_order,
               SUM(covers)::int                              AS total_covers
        FROM daily_inventory_log
        WHERE restaurant_id = %s
          AND log_date >= CURRENT_DATE - %s * INTERVAL '1 day'
        GROUP BY log_date
        ORDER BY log_date
    """, (restaurant_id, days))


def get_top_movers(restaurant_id, limit=10):
    """Highest-usage ingredients over the last 7 days."""
    return execute_query("""
        SELECT d.ingredient_id, i.ingredient_name, i.unit, i.category,
               ROUND(SUM(d.qty_used)::numeric, 2)  AS total_used_7d,
               ROUND(AVG(d.qty_used)::numeric, 2)  AS avg_daily_used
        FROM daily_inventory_log d
        JOIN ingredients i ON i.ingredient_id = d.ingredient_id
        WHERE d.restaurant_id = %s
          AND d.log_date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY d.ingredient_id, i.ingredient_name, i.unit, i.category
        ORDER BY total_used_7d DESC
        LIMIT %s
    """, (restaurant_id, limit))
