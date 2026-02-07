from ..utils.query import execute_query, execute_one


def get_xgboost_predictions(restaurant_id):
    """Pre-computed XGBoost predictions from the predictions table."""
    return execute_query("""
        SELECT p.ingredient_id, i.ingredient_name, i.unit,
               p.prediction_date, p.model_type,
               p.projected_demand_leadtime, p.reorder_point,
               p.target_stock_level, p.stockout_probability,
               p.days_until_stockout, p.restock_today,
               p.suggested_order_qty, p.suggested_order_date
        FROM predictions p
        JOIN ingredients i ON i.ingredient_id = p.ingredient_id
        WHERE p.restaurant_id = %s
          AND p.prediction_date = (
              SELECT MAX(prediction_date) FROM predictions
              WHERE restaurant_id = %s
          )
        ORDER BY p.stockout_probability DESC NULLS LAST
    """, (restaurant_id, restaurant_id))


def get_xgboost_prediction_single(restaurant_id, ingredient_id):
    """Single XGBoost prediction for a specific ingredient."""
    return execute_one("""
        SELECT p.ingredient_id, i.ingredient_name, i.unit,
               p.prediction_date, p.model_type,
               p.projected_demand_leadtime, p.reorder_point,
               p.target_stock_level, p.stockout_probability,
               p.days_until_stockout, p.restock_today,
               p.suggested_order_qty, p.suggested_order_date
        FROM predictions p
        JOIN ingredients i ON i.ingredient_id = p.ingredient_id
        WHERE p.restaurant_id = %s AND p.ingredient_id = %s
          AND p.prediction_date = (
              SELECT MAX(prediction_date) FROM predictions
              WHERE restaurant_id = %s AND ingredient_id = %s
          )
    """, (restaurant_id, ingredient_id, restaurant_id, ingredient_id))


def get_simple_prediction_items(restaurant_id):
    """Items from v_simple_prediction_items view (< 90 days history)."""
    return execute_query("""
        SELECT restaurant_id, ingredient_id, ingredient_name,
               lead_time_days, days_of_history,
               current_inventory, on_order_qty, avg_daily_usage
        FROM v_simple_prediction_items
        WHERE restaurant_id = %s
        ORDER BY ingredient_name
    """, (restaurant_id,))


def get_simple_prediction_item(restaurant_id, ingredient_id):
    """Single item from v_simple_prediction_items view."""
    return execute_one("""
        SELECT restaurant_id, ingredient_id, ingredient_name,
               lead_time_days, days_of_history,
               current_inventory, on_order_qty, avg_daily_usage
        FROM v_simple_prediction_items
        WHERE restaurant_id = %s AND ingredient_id = %s
    """, (restaurant_id, ingredient_id))
