import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app


def connection():
    url = current_app.config["DATABASE_URL"]
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    return psycopg2.connect(url, sslmode="require")


def query(sql, params=(), one=False):
    with connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description:
                data = cur.fetchall()
                return (data[0] if data else None) if one else data
    return None


def execute(sql, params=()):
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)

