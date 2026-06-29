from __future__ import annotations

from collections.abc import Sequence

import psycopg
from psycopg import Connection
from supabase import Client, create_client

from app.config import settings


def create_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def create_admin_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_admin_connection() -> Connection:
    dsn = settings.database_url.replace("+psycopg", "")
    return psycopg.connect(dsn)


def execute_sql(sql: str, params: Sequence | None = None) -> None:
    with get_admin_connection() as conn:
        conn.execute(sql, params)
        conn.commit()
