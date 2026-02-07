import os
import glob

import psycopg2
from psycopg2 import pool

from .config import Config

_pool = None

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "migrations")


def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(1, 10, Config.DATABASE_URL)
    return _pool


def get_connection():
    return get_pool().getconn()


def release_connection(conn):
    get_pool().putconn(conn)


def test_connection():
    """return True if the db is reachable, else false"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        release_connection(conn)
        return True
    except Exception:
        return False


def run_migrations():
    """Run pending SQL migrations from the migrations/ directory."""
    conn = psycopg2.connect(Config.DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id SERIAL PRIMARY KEY,
                filename TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()

        cur.execute("SELECT filename FROM _migrations ORDER BY filename")
        applied = {row[0] for row in cur.fetchall()}

        sql_files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, "*.sql")))
        if not sql_files:
            print("[migrate] No migration files found.")
            return

        new_count = 0
        for filepath in sql_files:
            filename = os.path.basename(filepath)
            if filename in applied:
                continue

            print(f"[migrate] Applying {filename}...", end=" ")
            with open(filepath) as f:
                sql = f.read()

            cur.execute(sql)
            cur.execute("INSERT INTO _migrations (filename) VALUES (%s)", (filename,))
            conn.commit()
            print("done.")
            new_count += 1

        if new_count == 0:
            print("[migrate] All migrations already applied.")
        else:
            print(f"[migrate] Applied {new_count} migration(s).")

    except Exception as e:
        conn.rollback()
        print(f"[migrate] Migration failed: {e}")
    finally:
        cur.close()
        conn.close()
