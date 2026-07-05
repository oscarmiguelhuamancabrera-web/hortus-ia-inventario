import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app, g


def connection():
    """Devuelve una única conexión por petición HTTP."""
    if "db_connection" in g and not g.db_connection.closed:
        return g.db_connection
    url = current_app.config["DATABASE_URL"]
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    g.db_connection = psycopg2.connect(
        url,
        sslmode="require",
        connect_timeout=8,
        application_name="hortus-ia",
    )
    return g.db_connection


def close_connection(_error=None):
    conn = g.pop("db_connection", None)
    if conn is not None and not conn.closed:
        conn.close()


def query(sql, params=(), one=False):
    conn = connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description:
                data = cur.fetchall()
                return (data[0] if data else None) if one else data
    except Exception:
        conn.rollback()
        raise
    return None


def execute(sql, params=()):
    conn = connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
