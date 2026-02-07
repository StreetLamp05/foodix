from ..models.inventory import (
    get_current_levels,
    get_history,
    upsert_usage,
    upsert_restock,
)


def get_inventory_levels(restaurant_id):
    return get_current_levels(restaurant_id)


def get_inventory_history(restaurant_id, ingredient_id, days=30):
    return get_history(restaurant_id, ingredient_id, days)


def log_usage(restaurant_id, ingredient_id, qty_used):
    if qty_used is None or qty_used <= 0:
        raise ValueError("qty_used must be a positive number")
    return upsert_usage(restaurant_id, ingredient_id, qty_used)


def log_restock(restaurant_id, ingredient_id, restock_qty):
    if restock_qty is None or restock_qty <= 0:
        raise ValueError("restock_qty must be a positive number")
    return upsert_restock(restaurant_id, ingredient_id, restock_qty)
