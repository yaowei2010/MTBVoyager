import psycopg2
import pandas as pd

# ✅ 設定 PostgreSQL 連線資訊
DB_NAME = "somatic"
DB_USER = "uuuwei0504"
DB_PASSWORD = "REDACTED_SET_VIA_ENV"
DB_HOST = "172.17.0.1"  # 你的 Docker 內部 IP
DB_PORT = "5432"

# ✅ 指定 CSV 檔案
newjobID='WvALHnstor'
CSV_FILE = f'/miRTI/media/patient/{newjobID}/somatic_result.csv'

# ✅ 指定表名稱
TABLE_NAME = f'somatic_result_{newjobID}'

def create_table_from_csv(csv_file, conn, table_name):
    """根據 CSV 建立新表"""
    df = pd.read_csv(csv_file, nrows=5)  # 讀取前 5 行確認欄位名稱
    columns = df.columns

    # 🔥 確保欄位名稱合法
    column_definitions = ", ".join([f'"{col}" TEXT' for col in columns])

    create_table_query = f"""
    DROP TABLE IF EXISTS "{table_name}";  -- 先刪除舊表
    CREATE TABLE "{table_name}" (
        {column_definitions}
    );
    """

    with conn.cursor() as cur:
        cur.execute(create_table_query)
        conn.commit()
    print(f"✅ 創建表: {table_name}")

def load_csv_to_postgres(csv_file, conn, table_name):
    """將 CSV 匯入 PostgreSQL"""
    try:
        with conn.cursor() as cur:
            with open(csv_file, 'r', encoding='utf-8') as f:
                cur.copy_expert(
                    f"COPY \"{table_name}\" FROM STDIN WITH CSV HEADER DELIMITER ',' NULL ''", f
                )
            conn.commit()
            print(f"✅ 成功匯入: {csv_file} 到 {table_name}")
    except Exception as e:
        conn.rollback()
        print(f"❌ 匯入失敗: {csv_file}, 錯誤: {e}")

def main():
    """主函式，連接 PostgreSQL 並載入 CSV"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("✅ 成功連接 PostgreSQL")

        # 1️⃣ 創建表 `1111`
        create_table_from_csv(CSV_FILE, conn, TABLE_NAME)

        # 2️⃣ 載入 CSV 到表 `1111`
        load_csv_to_postgres(CSV_FILE, conn, TABLE_NAME)

    except Exception as e:
        print(f"❌ PostgreSQL 連線失敗: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 已關閉 PostgreSQL 連線")

if __name__ == "__main__":
    main()
