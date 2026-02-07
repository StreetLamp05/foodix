#!/usr/bin/env python3
"""Import combined_restaurant_inventory_training_3y.csv into the inventory_health database."""

import csv
import sys
import psycopg2
from collections import defaultdict

DB_URL = "postgresql://hacks11:hackers11@localhost:5432/inventory_health"
CSV_PATH = "data/combined_restaurant_inventory_training_3y.csv"


def parse_id(raw, prefix):
    """R001 -> 1, I03 -> 3"""
    return int(raw.replace(prefix, ""))


def safe_decimal(val):
    if val == "" or val is None:
        return None
    return float(val)


def safe_int(val):
    if val == "" or val is None:
        return None
    return int(float(val))


def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Accumulators for dimension tables
    restaurants = {}          # rid_int -> name
    ingredients = {}          # iid_int -> (name, unit, unit_cost)
    holidays = {}             # (date, name) -> region
    rest_ingredients = {}     # (rid, iid) -> {lead_time_days, first_date}
    menu_items_set = {}       # (rid, item_name) -> menu_item_id (assigned later)
    menu_item_ing = {}        # (menu_item_name, rid, iid) -> qty_per_item

    daily_rows = []
    prediction_rows = []

    print("Reading CSV...")
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        row_count = 0
        for row in reader:
            row_count += 1
            rid = parse_id(row["restaurant_id"], "R")
            iid = parse_id(row["ingredient_id"], "I")
            log_date = row["date"]

            # --- dimension: restaurants ---
            if rid not in restaurants:
                restaurants[rid] = row["restaurant_name"]

            # --- dimension: ingredients ---
            if iid not in ingredients:
                ingredients[iid] = (
                    row["ingredient_name"],
                    row["unit"],
                    float(row["unit_cost"]),
                )

            # --- dimension: holidays ---
            if row["is_holiday"] == "1" and row["holiday_name"]:
                key = (log_date, row["holiday_name"])
                if key not in holidays:
                    holidays[key] = "US"

            # --- dimension: restaurant_ingredients ---
            ri_key = (rid, iid)
            lead = safe_int(row["lead_time_days"])
            if ri_key not in rest_ingredients:
                rest_ingredients[ri_key] = {
                    "lead_time_days": lead,
                    "first_date": log_date,
                }
            else:
                if log_date < rest_ingredients[ri_key]["first_date"]:
                    rest_ingredients[ri_key]["first_date"] = log_date

            # --- dimension: menu_items + menu_item_ingredients ---
            items_list_raw = row.get("menu_items_list", "")
            if items_list_raw:
                item_names = [n.strip() for n in items_list_raw.split("|")]
                num_items = len(item_names)
                avg_qty = safe_decimal(row.get("avg_qty_per_item"))

                for name in item_names:
                    mk = (rid, name)
                    if mk not in menu_items_set:
                        menu_items_set[mk] = None  # id assigned after insert

                    bom_key = (name, rid, iid)
                    if bom_key not in menu_item_ing and avg_qty is not None:
                        if num_items == 1:
                            menu_item_ing[bom_key] = avg_qty
                        else:
                            # approximate: use avg for all items
                            menu_item_ing[bom_key] = avg_qty

            # --- fact: daily_inventory_log ---
            daily_rows.append((
                rid, iid, log_date,
                safe_int(row["covers"]),
                safe_decimal(row["seasonality_factor"]),
                safe_decimal(row["inventory_start"]),
                safe_decimal(row["qty_used"]),
                safe_decimal(row["stockout_qty"]),
                safe_decimal(row["inventory_end"]),
                safe_decimal(row["on_order_qty"]),
                safe_decimal(row["avg_daily_usage_7d"]),
                safe_decimal(row["avg_daily_usage_28d"]),
                safe_decimal(row["avg_daily_usage_56d"]),
                safe_int(row.get("units_sold_items_using_ing")),
                safe_decimal(row.get("revenue_items_using_ing")),
            ))

            # --- predictions ---
            proj = safe_decimal(row.get("projected_demand_leadtime"))
            rp = safe_decimal(row.get("reorder_point"))
            tgt = safe_decimal(row.get("target_stock_level_S"))
            restock = row.get("restock_today_label", "0") == "1"
            oq = safe_decimal(row.get("order_qty"))

            if any(v is not None for v in [proj, rp, tgt, oq]):
                prediction_rows.append((
                    rid, iid, log_date,
                    "historical_import",
                    proj, rp, tgt,
                    None,  # stockout_probability not in CSV
                    None,  # days_until_stockout not in CSV
                    restock, oq,
                    None,  # suggested_order_date
                ))

    print(f"  {row_count} CSV rows parsed")
    print(f"  {len(restaurants)} restaurants, {len(ingredients)} ingredients")
    print(f"  {len(holidays)} holidays, {len(menu_items_set)} menu items")
    print(f"  {len(rest_ingredients)} restaurant-ingredient pairs")
    print(f"  {len(daily_rows)} daily_inventory_log rows")
    print(f"  {len(prediction_rows)} prediction rows")

    # ── INSERT DIMENSION TABLES ──

    print("\nInserting restaurants...")
    for rid, name in sorted(restaurants.items()):
        cur.execute(
            "INSERT INTO restaurants (restaurant_id, restaurant_name) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (rid, name),
        )
    # Reset sequence
    cur.execute("SELECT setval('restaurants_restaurant_id_seq', (SELECT MAX(restaurant_id) FROM restaurants))")

    print("Inserting ingredients...")
    for iid, (name, unit, cost) in sorted(ingredients.items()):
        cur.execute(
            "INSERT INTO ingredients (ingredient_id, ingredient_name, unit, unit_cost) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (iid, name, unit, cost),
        )
    cur.execute("SELECT setval('ingredients_ingredient_id_seq', (SELECT MAX(ingredient_id) FROM ingredients))")

    print("Inserting holidays...")
    for (hdate, hname), region in holidays.items():
        cur.execute(
            "INSERT INTO holidays (holiday_date, holiday_name, region) VALUES (%s, %s, %s) "
            "ON CONFLICT DO NOTHING",
            (hdate, hname, region),
        )

    print("Inserting restaurant_ingredients...")
    for (rid, iid), info in rest_ingredients.items():
        cur.execute(
            "INSERT INTO restaurant_ingredients (restaurant_id, ingredient_id, lead_time_days, first_stocked_date) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
            (rid, iid, info["lead_time_days"], info["first_date"]),
        )

    print("Inserting menu_items...")
    menu_item_id_map = {}  # (rid, name) -> auto-generated id
    for (rid, name) in sorted(menu_items_set.keys()):
        cur.execute(
            "INSERT INTO menu_items (restaurant_id, item_name) VALUES (%s, %s) RETURNING menu_item_id",
            (rid, name),
        )
        mid = cur.fetchone()[0]
        menu_item_id_map[(rid, name)] = mid

    print("Inserting menu_item_ingredients...")
    for (item_name, rid, iid), qty in menu_item_ing.items():
        mid = menu_item_id_map.get((rid, item_name))
        if mid is not None:
            cur.execute(
                "INSERT INTO menu_item_ingredients (menu_item_id, ingredient_id, qty_per_item) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (mid, iid, qty),
            )

    # ── INSERT FACT TABLE ──

    print(f"\nInserting {len(daily_rows)} daily_inventory_log rows...")
    sql_inv = """
        INSERT INTO daily_inventory_log (
            restaurant_id, ingredient_id, log_date,
            covers, seasonality_factor,
            inventory_start, qty_used, stockout_qty, inventory_end, on_order_qty,
            avg_daily_usage_7d, avg_daily_usage_28d, avg_daily_usage_56d,
            units_sold_items_using, revenue_items_using
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (restaurant_id, ingredient_id, log_date) DO NOTHING
    """
    batch_size = 5000
    for i in range(0, len(daily_rows), batch_size):
        batch = daily_rows[i : i + batch_size]
        cur.executemany(sql_inv, batch)
        print(f"  {min(i + batch_size, len(daily_rows))}/{len(daily_rows)}")

    # ── INSERT PREDICTIONS ──

    print(f"\nInserting {len(prediction_rows)} prediction rows...")
    sql_pred = """
        INSERT INTO predictions (
            restaurant_id, ingredient_id, prediction_date,
            model_type,
            projected_demand_leadtime, reorder_point, target_stock_level,
            stockout_probability, days_until_stockout,
            restock_today, suggested_order_qty, suggested_order_date
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (restaurant_id, ingredient_id, prediction_date) DO NOTHING
    """
    for i in range(0, len(prediction_rows), batch_size):
        batch = prediction_rows[i : i + batch_size]
        cur.executemany(sql_pred, batch)
        print(f"  {min(i + batch_size, len(prediction_rows))}/{len(prediction_rows)}")

    conn.commit()
    print("\nDone! All data imported successfully.")

    # Quick verification
    for table in [
        "restaurants", "ingredients", "holidays",
        "restaurant_ingredients", "menu_items", "menu_item_ingredients",
        "daily_inventory_log", "predictions",
    ]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {cur.fetchone()[0]} rows")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
