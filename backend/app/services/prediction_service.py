from ..models.prediction import (
    get_xgboost_predictions,
    get_xgboost_prediction_single,
    get_simple_prediction_items,
    get_simple_prediction_item,
)


def _compute_simple_prediction(row):
    """On-the-fly calculation for items with < 90 days history."""
    avg_usage = float(row["avg_daily_usage"] or 0)
    current_inv = float(row["current_inventory"] or 0)
    on_order = float(row["on_order_qty"] or 0)
    available = current_inv + on_order

    days_until_stockout = None
    if avg_usage > 0:
        days_until_stockout = round(available / avg_usage)

    return {
        "ingredient_id": row["ingredient_id"],
        "ingredient_name": row["ingredient_name"],
        "lead_time_days": row["lead_time_days"],
        "days_of_history": row["days_of_history"],
        "current_inventory": current_inv,
        "on_order_qty": on_order,
        "avg_daily_usage": avg_usage,
        "days_until_stockout": days_until_stockout,
        "confidence": "low",
    }


def _tag_xgboost(row):
    """Tag an XGBoost prediction row with high confidence."""
    result = dict(row)
    result["confidence"] = "high"
    return result


def get_all_predictions(restaurant_id):
    """Merge both tiers into a single response."""
    xgboost_rows = get_xgboost_predictions(restaurant_id)
    simple_rows = get_simple_prediction_items(restaurant_id)

    xgboost = [_tag_xgboost(r) for r in xgboost_rows]
    simple = [_compute_simple_prediction(r) for r in simple_rows]

    return {
        "xgboost": xgboost,
        "simple": simple,
        "all": xgboost + simple,
    }


def get_single_prediction(restaurant_id, ingredient_id):
    """Return prediction for a single ingredient (XGBoost preferred, simple fallback)."""
    xg = get_xgboost_prediction_single(restaurant_id, ingredient_id)
    if xg:
        return _tag_xgboost(xg)

    simple = get_simple_prediction_item(restaurant_id, ingredient_id)
    if simple:
        return _compute_simple_prediction(simple)

    return None
