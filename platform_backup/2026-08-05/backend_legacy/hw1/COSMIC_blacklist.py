import psycopg2
import pandas as pd
import os

def cosmic_blacklist():
    """
    從所有 *_COSMIC 資料表中統計 Chr, Start, End, Ref, Alt 出現次數，輸出為 COSMIC_blacklist.csv
    存放位置：/miRTI/media/reference/COSMIC_blacklist.csv
    """

    # === PostgreSQL 連線資訊 === #
    DB_NAME = "somatic"
    DB_USER = "uuuwei0504"
    DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    DB_HOST = "172.17.0.1"
    DB_PORT = "5432"

    # === 要統計的欄位 === #
    target_cols = ["Chr", "Start", "End", "Ref", "Alt"]

    # === 輸出路徑 === #
    output_path = "/miRTI/media/reference/Blacklist/COSMIC_blacklist.csv"

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("✅ 成功連接 PostgreSQL")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name LIKE '%\\_COSMIC' ESCAPE '\\';
            """)
            cosmic_tables = [row[0] for row in cur.fetchall()]

        if not cosmic_tables:
            print("⚠️ 找不到任何 *_COSMIC 資料表")
            return

        all_rows = []

        for table in cosmic_tables:
            try:
                df = pd.read_sql(f'SELECT "{target_cols[0]}", "{target_cols[1]}", "{target_cols[2]}", "{target_cols[3]}", "{target_cols[4]}" FROM "{table}"', conn)
                all_rows.append(df)
                print(f"✅ 讀取 {table} 成功，共 {len(df)} 筆")
            except Exception as e:
                print(f"❌ 無法讀取 {table} 中指定欄位：{e}")

        if not all_rows:
            print("⚠️ 所有 *_COSMIC 表皆無有效資料")
            return

        # 合併統計
        merged_df = pd.concat(all_rows, ignore_index=True)
        grouped = merged_df.groupby(target_cols).size().reset_index(name="count")
        grouped.to_csv(output_path, index=False)
        print(f"📁 已輸出統計結果至：{output_path}")

    except Exception as e:
        print(f"❌ PostgreSQL 錯誤：{e}")

    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 已關閉 PostgreSQL 連線")
            

import psycopg2
import pandas as pd
import os

import psycopg2
import pandas as pd

def somatic_drug_blacklist():
    """
    從所有 *_somaticResult 資料表中統計特定欄位完全一致的出現次數，
    並輸出成 somatic_result_blacklist.csv，並加入 ClinVar 查詢欄位 query_clinvar。
    """

    # === PostgreSQL 連線資訊 === #
    DB_NAME = "somatic"
    DB_USER = "uuuwei0504"
    DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    DB_HOST = "172.17.0.1"
    DB_PORT = "5432"

    # === 要統計的欄位（12個）=== #
    target_cols = [
        "Chr", "Start", "End", "Ref", "Alt", "Func.refGene", "Gene.refGene",
        "avsnp150", "Feature", "HGVSc", "HGVSp", "#Uploaded_variation"
    ]

    # === 輸出檔案位置 === #
    output_path = "/miRTI/media/reference/Blacklist/somatic_result_blacklist.csv"

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("✅ 成功連接 PostgreSQL")

        with conn.cursor() as cur:
            # 找出所有 *_somaticResult 表格
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name LIKE '%\\_somaticResult' ESCAPE '\\';
            """)
            tables = [row[0] for row in cur.fetchall()]

        if not tables:
            print("⚠️ 找不到任何 *_somaticResult 資料表")
            return

        all_rows = []

        for table in tables:
            try:
                col_string = ', '.join([f'"{col}"' for col in target_cols])
                df = pd.read_sql(f'SELECT {col_string} FROM "{table}"', conn)
                all_rows.append(df)
                print(f"✅ 讀取 {table} 成功，共 {len(df)} 筆")
            except Exception as e:
                print(f"❌ 無法讀取 {table} 中欄位資料：{e}")

        if not all_rows:
            print("⚠️ 所有 *_somaticResult 表皆無有效資料")
            return

        merged_df = pd.concat(all_rows, ignore_index=True)
        grouped = merged_df.groupby(target_cols).size().reset_index(name="count")

        # === 加入 query_clinvar 欄位 === #
        def build_query(row):
            try:
                transcript = str(row["Feature"]).strip()
                gene = str(row["Gene.refGene"]).strip()
                hgvsc = str(row["HGVSc"]).strip()
                if ":" in hgvsc:
                    c_part = hgvsc.split(":", 1)[1]
                    return f"{transcript}({gene}):{c_part}"
                else:
                    return ""
            except Exception:
                return ""

        grouped["query_clinvar"] = grouped.apply(build_query, axis=1)

        grouped.to_csv(output_path, index=False)
        print(f"📁 已輸出統計結果至：{output_path}")

    except Exception as e:
        print(f"❌ PostgreSQL 錯誤：{e}")

    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 已關閉 PostgreSQL 連線")


somatic_drug_blacklist()

# import psycopg2

# def drop_all_somatic_result_tables():
#     """
#     刪除所有表名符合 *_somatic_result 的 PostgreSQL 資料表
#     """

#     # === PostgreSQL 連線資訊 === #
#     DB_NAME = "somatic"
#     DB_USER = "uuuwei0504"
#     DB_PASSWORD = "REDACTED_SET_VIA_ENV"
#     DB_HOST = "172.17.0.1"
#     DB_PORT = "5432"

#     try:
#         conn = psycopg2.connect(
#             dbname=DB_NAME,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             host=DB_HOST,
#             port=DB_PORT
#         )
#         print("✅ 成功連接 PostgreSQL")

#         with conn.cursor() as cur:
#             # 尋找所有以 _somatic_result 結尾的表
#             cur.execute("""
#                 SELECT table_name
#                 FROM information_schema.tables
#                 WHERE table_schema = 'public'
#                   AND table_name LIKE '%\\_somaticResult' ESCAPE '\\';
#             """)
#             tables_to_drop = [row[0] for row in cur.fetchall()]

#             if not tables_to_drop:
#                 print("⚠️ 沒有符合條件的 _somatic_result 表格")
#                 return

#             for table in tables_to_drop:
#                 try:
#                     cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE;')
#                     print(f"🗑️ 已刪除資料表：{table}")
#                 except Exception as e:
#                     print(f"❌ 刪除失敗：{table}，錯誤：{e}")

#             conn.commit()

#     except Exception as e:
#         print(f"❌ PostgreSQL 錯誤：{e}")

#     finally:
#         if 'conn' in locals():
#             conn.close()
#             print("🔌 已關閉 PostgreSQL 連線")

# 執行
# drop_all_somatic_result_tables()