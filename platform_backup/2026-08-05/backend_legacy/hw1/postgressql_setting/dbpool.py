# dbpool.py
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Optional, Sequence

from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

# ─────────────────────────────────────────────
# 讀環境變數：容器內用 postgres；容器外可用 140.xxx
# ─────────────────────────────────────────────
PG_HOST = os.getenv("PG_HOST") or "140.116.214.138"
PG_PORT = int(os.getenv("PG_PORT") or "5432")
PG_DB   = os.getenv("PG_DB")  or "somatic"
PG_USER = os.getenv("PG_USER")  or "uuuwei0504"
PG_PW   = os.getenv("PG_PW")  or "REDACTED_SET_VIA_ENV"

MINCONN = int(os.getenv("PG_MINCONN", "1"))
MAXCONN = int(os.getenv("PG_MAXCONN", "20"))

_pool_lock = threading.Lock()
_POOL: ThreadedConnectionPool | None = None


def _ensure_pool() -> ThreadedConnectionPool:
    global _POOL
    if _POOL is None:
        with _pool_lock:
            if _POOL is None:
                if not PG_PW:
                    raise RuntimeError(
                        "DB password not set. Please set PG_PW (or PGPASSWORD) in environment."
                    )
                _POOL = ThreadedConnectionPool(
                    minconn=MINCONN,
                    maxconn=MAXCONN,
                    host=PG_HOST,
                    port=PG_PORT,
                    dbname=PG_DB,
                    user=PG_USER,
                    password=PG_PW,
                )
    return _POOL


class PgConn:
    """with PgConn() as conn: ...  (success commit, error rollback)"""
    def __init__(self, autocommit: bool = False):
        self.autocommit = autocommit
        self._conn = None

    def __enter__(self):
        pool = _ensure_pool()
        self._conn = pool.getconn()
        self._conn.autocommit = self.autocommit
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        pool = _ensure_pool()
        if not self._conn:
            return
        try:
            if not self.autocommit:
                if exc_type is None:
                    self._conn.commit()
                else:
                    self._conn.rollback()
        finally:
            try:
                if not self._conn.closed:
                    pool.putconn(self._conn)
            finally:
                self._conn = None


@contextmanager
def pg_cursor(*, autocommit: bool = False, dict_rows: bool = False):
    with PgConn(autocommit=autocommit) as conn:
        cursor_factory = RealDictCursor if dict_rows else None
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield cur


def pg_execute(sql: str, params: Optional[Sequence[Any]] = None, *, autocommit: bool = False) -> None:
    with pg_cursor(autocommit=autocommit) as cur:
        cur.execute(sql, params)


def pg_fetchone(sql: str, params: Optional[Sequence[Any]] = None, *, dict_rows: bool = False):
    with pg_cursor(dict_rows=dict_rows) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def pg_fetchall(sql: str, params: Optional[Sequence[Any]] = None, *, dict_rows: bool = False):
    with pg_cursor(dict_rows=dict_rows) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def close_pool() -> None:
    global _POOL
    with _pool_lock:
        if _POOL is not None:
            _POOL.closeall()
            _POOL = None
