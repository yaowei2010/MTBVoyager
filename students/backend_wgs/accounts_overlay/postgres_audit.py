import logging
import os

import psycopg2


logger = logging.getLogger(__name__)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS mtb_erp_accounts (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    role VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL,
    password_hash TEXT NOT NULL,
    date_joined TIMESTAMPTZ,
    last_login TIMESTAMPTZ,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS mtb_erp_login_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NULL,
    username VARCHAR(150) NOT NULL,
    role VARCHAR(16) NULL,
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(120) NOT NULL DEFAULT '',
    ip_address INET NULL,
    user_agent TEXT NOT NULL DEFAULT '',
    login_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS mtb_erp_login_logs_user_time_idx
    ON mtb_erp_login_logs (user_id, login_at DESC);
CREATE INDEX IF NOT EXISTS mtb_erp_login_logs_username_time_idx
    ON mtb_erp_login_logs (username, login_at DESC);
"""


def _connect():
    return psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=os.environ.get("PG_PORT", "5432"),
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PW"],
        connect_timeout=5,
    )


def ensure_tables(cursor):
    cursor.execute(SCHEMA_SQL)


def sync_account(user, role):
    try:
        with _connect() as connection, connection.cursor() as cursor:
            ensure_tables(cursor)
            cursor.execute(
                """
                INSERT INTO mtb_erp_accounts
                    (user_id, username, role, is_active, password_hash, date_joined, last_login, synced_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET
                    username=EXCLUDED.username,
                    role=EXCLUDED.role,
                    is_active=EXCLUDED.is_active,
                    password_hash=EXCLUDED.password_hash,
                    date_joined=EXCLUDED.date_joined,
                    last_login=EXCLUDED.last_login,
                    synced_at=NOW()
                """,
                (user.id, user.username, role, user.is_active, user.password, user.date_joined, user.last_login),
            )
    except Exception:
        logger.exception("Unable to synchronize ERP account %s to PostgreSQL", user.id)


def record_login(*, user, username, role, success, failure_reason, ip_address, user_agent):
    try:
        with _connect() as connection, connection.cursor() as cursor:
            ensure_tables(cursor)
            cursor.execute(
                """
                INSERT INTO mtb_erp_login_logs
                    (user_id, username, role, success, failure_reason, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user.id if user else None,
                    username[:150],
                    role,
                    success,
                    failure_reason[:120],
                    ip_address,
                    user_agent[:2000],
                ),
            )
    except Exception:
        # PostgreSQL audit availability must not lock every user out of MTB.
        logger.exception("Unable to write ERP login audit to PostgreSQL")
