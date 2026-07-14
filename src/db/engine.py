from functools import lru_cache

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from .config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DATABASE_URL


@lru_cache(maxsize=1)
def get_engine():
    # Reuse one engine process-wide. Creating a new engine on every call
    # (with default QueuePool) quickly exhausts Supabase session pooler
    # limits (EMAXCONNSESSION / pool_size: 15).
    # NullPool opens a connection per checkout and closes it immediately,
    # which is the safest mode for Supabase pooler session endpoints.
    return create_engine(
        DATABASE_URL,
        poolclass=NullPool,
        pool_pre_ping=True,
    )


def get_conn():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )
