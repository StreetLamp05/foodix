from psycopg2.extras import RealDictCursor

from ..db import get_connection, release_connection


def execute_query(sql, params=None):
    """Execute a SELECT and return all rows as list of dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        release_connection(conn)


def execute_one(sql, params=None):
    """Execute a SELECT and return a single row dict, or None."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        release_connection(conn)


def execute_modify(sql, params=None):
    """Execute an INSERT/UPDATE/DELETE with commit. Returns the row if RETURNING is used."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            conn.commit()
            try:
                return cur.fetchone()
            except Exception:
                return None
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)
