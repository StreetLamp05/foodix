from ..utils.query import execute_query, execute_one, execute_modify
from ..db import get_connection, release_connection
from psycopg2.extras import RealDictCursor


def get_batches(restaurant_id, ingredient_id, status=None):
    """Get batches for a restaurant ingredient, optionally filtered by status."""
    if status:
        return execute_query("""
            SELECT batch_id, restaurant_id, ingredient_id,
                   supplier_name, supplier_contact, purchase_cost_per_unit,
                   qty_received, qty_remaining,
                   received_date, expiration_date, status, created_at
            FROM ingredient_batches
            WHERE restaurant_id = %s AND ingredient_id = %s AND status = %s
            ORDER BY expiration_date ASC NULLS LAST, received_date ASC
        """, (restaurant_id, ingredient_id, status))

    return execute_query("""
        SELECT batch_id, restaurant_id, ingredient_id,
               supplier_name, supplier_contact, purchase_cost_per_unit,
               qty_received, qty_remaining,
               received_date, expiration_date, status, created_at
        FROM ingredient_batches
        WHERE restaurant_id = %s AND ingredient_id = %s
        ORDER BY expiration_date ASC NULLS LAST, received_date ASC
    """, (restaurant_id, ingredient_id))


def get_all_batches_for_restaurant(restaurant_id, active_only=True):
    """Get all batches across all ingredients for a restaurant."""
    if active_only:
        return execute_query("""
            SELECT b.batch_id, b.ingredient_id, i.ingredient_name, i.unit,
                   b.supplier_name, b.purchase_cost_per_unit,
                   b.qty_received, b.qty_remaining,
                   b.received_date, b.expiration_date, b.status
            FROM ingredient_batches b
            JOIN ingredients i ON i.ingredient_id = b.ingredient_id
            WHERE b.restaurant_id = %s AND b.status = 'active'
            ORDER BY b.expiration_date ASC NULLS LAST, b.received_date ASC
        """, (restaurant_id,))

    return execute_query("""
        SELECT b.batch_id, b.ingredient_id, i.ingredient_name, i.unit,
               b.supplier_name, b.purchase_cost_per_unit,
               b.qty_received, b.qty_remaining,
               b.received_date, b.expiration_date, b.status
        FROM ingredient_batches b
        JOIN ingredients i ON i.ingredient_id = b.ingredient_id
        WHERE b.restaurant_id = %s
        ORDER BY b.expiration_date ASC NULLS LAST, b.received_date ASC
    """, (restaurant_id,))


def get_batch_by_id(batch_id):
    return execute_one("""
        SELECT batch_id, restaurant_id, ingredient_id,
               supplier_name, supplier_contact, purchase_cost_per_unit,
               qty_received, qty_remaining,
               received_date, expiration_date, status, created_at
        FROM ingredient_batches
        WHERE batch_id = %s
    """, (batch_id,))


def create_batch(restaurant_id, ingredient_id, qty_received,
                 supplier_name=None, supplier_contact=None,
                 purchase_cost_per_unit=None, received_date=None,
                 expiration_date=None):
    """Record a new batch received."""
    return execute_modify("""
        INSERT INTO ingredient_batches
            (restaurant_id, ingredient_id, qty_received, qty_remaining,
             supplier_name, supplier_contact, purchase_cost_per_unit,
             received_date, expiration_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s,
                COALESCE(%s, CURRENT_DATE), %s)
        RETURNING batch_id, restaurant_id, ingredient_id,
                  supplier_name, supplier_contact, purchase_cost_per_unit,
                  qty_received, qty_remaining,
                  received_date, expiration_date, status
    """, (restaurant_id, ingredient_id, qty_received, qty_received,
          supplier_name, supplier_contact, purchase_cost_per_unit,
          received_date, expiration_date))


def fifo_deduct(restaurant_id, ingredient_id, qty_to_deduct):
    """
    FIFO deduction: walk active batches oldest-expiration-first,
    deduct qty, mark depleted when a batch hits 0.

    Runs in a single transaction. Returns list of affected batches
    and any shortfall if stock ran out.
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Lock active batches in FIFO order
            cur.execute("""
                SELECT batch_id, qty_remaining
                FROM ingredient_batches
                WHERE restaurant_id = %s AND ingredient_id = %s AND status = 'active'
                ORDER BY expiration_date ASC NULLS LAST, received_date ASC
                FOR UPDATE
            """, (restaurant_id, ingredient_id))

            batches = cur.fetchall()
            remaining = float(qty_to_deduct)
            affected = []

            for batch in batches:
                if remaining <= 0:
                    break

                available = float(batch["qty_remaining"])
                deducted = min(available, remaining)
                new_qty = available - deducted
                new_status = "depleted" if new_qty <= 0 else "active"

                cur.execute("""
                    UPDATE ingredient_batches
                    SET qty_remaining = %s, status = %s
                    WHERE batch_id = %s
                    RETURNING batch_id, qty_remaining, status
                """, (max(new_qty, 0), new_status, batch["batch_id"]))

                row = cur.fetchone()
                row["qty_deducted"] = deducted
                affected.append(row)
                remaining -= deducted

            conn.commit()

            return {
                "affected_batches": affected,
                "total_deducted": float(qty_to_deduct) - max(remaining, 0),
                "shortfall": max(remaining, 0),
            }
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


def mark_expired(restaurant_id):
    """Mark active batches past their expiration date as expired."""
    return execute_modify("""
        UPDATE ingredient_batches
        SET status = 'expired'
        WHERE restaurant_id = %s
          AND status = 'active'
          AND expiration_date < CURRENT_DATE
        RETURNING batch_id, ingredient_id, expiration_date
    """, (restaurant_id,))


def get_expiring_soon(restaurant_id, days=3):
    """Batches expiring within N days (for alerts)."""
    return execute_query("""
        SELECT b.batch_id, b.ingredient_id, i.ingredient_name, i.unit,
               b.qty_remaining, b.expiration_date, b.supplier_name
        FROM ingredient_batches b
        JOIN ingredients i ON i.ingredient_id = b.ingredient_id
        WHERE b.restaurant_id = %s
          AND b.status = 'active'
          AND b.expiration_date <= CURRENT_DATE + %s * INTERVAL '1 day'
          AND b.expiration_date >= CURRENT_DATE
        ORDER BY b.expiration_date ASC
    """, (restaurant_id, days))
