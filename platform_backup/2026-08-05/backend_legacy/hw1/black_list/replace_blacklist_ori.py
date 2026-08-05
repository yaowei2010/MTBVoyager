# replace_blacklist_ori.py
from __future__ import annotations

import csv
import io
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


# =========================
# 1. 資料庫連線設定
# =========================
DB_CONFIG = {
    "dbname": "somatic",
    "user": "uuuwei0504",
    "password": "REDACTED_SET_VIA_ENV",
    "host": "140.116.214.138",
    "port": "5432",
}


# =========================
# 2. CSV 檔案路徑
# =========================
CSV_PATH = "candidate_germline_blacklist_variants.csv"


# =========================
# 3. 目標資料表
# =========================
TABLE_SCHEMA = "public"
TABLE_NAME = "blacklist_ori"
BACKUP_TABLE_NAME = "blacklist_ori_backup"


CSV_COLUMNS = [
    "variant_id",
    "gene_symbol",
    "Chr",
    "Start",
    "End",
    "Ref",
    "Alt",
    "Func.refGeneWithVer",
    "ExonicFunc.refGeneWithVer",
    "AAChange.refGeneWithVer",
    "AF",
    "AF_popmax",
    "CntSampleWithVariant",
    "CntSampleWithVariantConfirmedGermline",
    "FreqConfirmedGermline",
    "CntSampleWithVariantConfirmedSomatic",
    "FreqConfirmedSomatic",
    "is_Germline",
    "is_benign",
    "is_pathogenic",
    "is_common",
    "CLNSIG",
    "LOVD_all_clinical",
    "Status",
    "candidate_germline_variant",
    "candidate_reason",
]


INTEGER_COLUMNS = {
    "Start",
    "End",
    "CntSampleWithVariant",
    "CntSampleWithVariantConfirmedGermline",
    "CntSampleWithVariantConfirmedSomatic",
    "candidate_germline_variant",
}


NUMERIC_COLUMNS = {
    "AF",
    "AF_popmax",
    "FreqConfirmedGermline",
    "FreqConfirmedSomatic",
    "is_Germline",
    "is_benign",
    "is_pathogenic",
    "is_common",
}


COLUMN_TYPES = {
    "variant_id": "TEXT",
    "gene_symbol": "TEXT",
    "Chr": "TEXT",
    "Start": "BIGINT",
    "End": "BIGINT",
    "Ref": "TEXT",
    "Alt": "TEXT",
    "Func.refGeneWithVer": "TEXT",
    "ExonicFunc.refGeneWithVer": "TEXT",
    "AAChange.refGeneWithVer": "TEXT",
    "AF": "NUMERIC",
    "AF_popmax": "NUMERIC",
    "CntSampleWithVariant": "BIGINT",
    "CntSampleWithVariantConfirmedGermline": "BIGINT",
    "FreqConfirmedGermline": "NUMERIC",
    "CntSampleWithVariantConfirmedSomatic": "BIGINT",
    "FreqConfirmedSomatic": "NUMERIC",
    "is_Germline": "NUMERIC",
    "is_benign": "NUMERIC",
    "is_pathogenic": "NUMERIC",
    "is_common": "NUMERIC",
    "CLNSIG": "TEXT",
    "LOVD_all_clinical": "TEXT",
    "Status": "TEXT",
    "candidate_germline_variant": "BIGINT",
    "candidate_reason": "TEXT",
}


def clean_value(col, value):
    if value is None:
        return None

    s = str(value).strip()

    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None

    if col in INTEGER_COLUMNS:
        try:
            return int(s)
        except Exception:
            try:
                return int(float(s))
            except Exception:
                return None

    if col in NUMERIC_COLUMNS:
        try:
            return float(s)
        except Exception:
            return None

    return s


def read_csv_rows(csv_path):
    with open(csv_path, "rb") as f:
        raw = f.read()

    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    missing = [c for c in CSV_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    rows = []

    for r in reader:
        cleaned = {c: clean_value(c, r.get(c)) for c in CSV_COLUMNS}

        # 五鍵不完整就跳過
        required_cols = ["Chr", "Start", "End", "Ref", "Alt"]
        if not all(cleaned.get(c) not in (None, "") for c in required_cols):
            continue

        rows.append(cleaned)

    return rows


def create_blacklist_ori(cur):
    col_defs = [
        sql.SQL("id BIGSERIAL PRIMARY KEY"),
        *[
            sql.SQL("{} {}").format(
                sql.Identifier(c),
                sql.SQL(COLUMN_TYPES[c])
            )
            for c in CSV_COLUMNS
        ],
        sql.SQL("created_at TIMESTAMPTZ DEFAULT NOW()"),
    ]

    cur.execute(
        sql.SQL("CREATE TABLE {}.{} ({})").format(
            sql.Identifier(TABLE_SCHEMA),
            sql.Identifier(TABLE_NAME),
            sql.SQL(", ").join(col_defs),
        )
    )

    cur.execute(
        sql.SQL(
            "CREATE INDEX idx_blacklist_ori_variant_key "
            "ON {}.{} ({}, {}, {}, {}, {})"
        ).format(
            sql.Identifier(TABLE_SCHEMA),
            sql.Identifier(TABLE_NAME),
            sql.Identifier("Chr"),
            sql.Identifier("Start"),
            sql.Identifier("End"),
            sql.Identifier("Ref"),
            sql.Identifier("Alt"),
        )
    )


def replace_blacklist_ori(rows, backup_old=True):
    values = [[r.get(c) for c in CSV_COLUMNS] for r in rows]

    conn = psycopg2.connect(**DB_CONFIG)

    try:
        with conn:
            with conn.cursor() as cur:
                if backup_old:
                    print("Backing up old public.blacklist_ori ...")

                    cur.execute(
                        sql.SQL("DROP TABLE IF EXISTS {}.{}").format(
                            sql.Identifier(TABLE_SCHEMA),
                            sql.Identifier(BACKUP_TABLE_NAME),
                        )
                    )

                    cur.execute(
                        sql.SQL("CREATE TABLE {}.{} AS TABLE {}.{}").format(
                            sql.Identifier(TABLE_SCHEMA),
                            sql.Identifier(BACKUP_TABLE_NAME),
                            sql.Identifier(TABLE_SCHEMA),
                            sql.Identifier(TABLE_NAME),
                        )
                    )

                print("Dropping old public.blacklist_ori ...")

                cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {}.{} CASCADE").format(
                        sql.Identifier(TABLE_SCHEMA),
                        sql.Identifier(TABLE_NAME),
                    )
                )

                print("Creating new public.blacklist_ori ...")
                create_blacklist_ori(cur)

                print(f"Inserting {len(values)} rows ...")

                insert_sql = sql.SQL("INSERT INTO {}.{} ({}) VALUES %s").format(
                    sql.Identifier(TABLE_SCHEMA),
                    sql.Identifier(TABLE_NAME),
                    sql.SQL(", ").join(sql.Identifier(c) for c in CSV_COLUMNS),
                )

                execute_values(
                    cur,
                    insert_sql.as_string(conn),
                    values,
                    page_size=1000,
                )

        print("Done.")
        print(f"Inserted rows: {len(rows)}")
        print(f"Target table: {TABLE_SCHEMA}.{TABLE_NAME}")

        if backup_old:
            print(f"Backup table: {TABLE_SCHEMA}.{BACKUP_TABLE_NAME}")

    except Exception as e:
        conn.rollback()
        print("Failed.")
        print(type(e).__name__, str(e))
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    rows = read_csv_rows(CSV_PATH)

    if not rows:
        raise RuntimeError("CSV has no valid rows.")

    replace_blacklist_ori(rows, backup_old=True)