import psycopg2
import pandas as pd

conn = psycopg2.connect(
    dbname="somatic",
    user="uuuwei0504",
    password="REDACTED_SET_VIA_ENV",
    host="140.116.214.138",
    port="5432"
)

query = 'SELECT * FROM "somatic_result_ybhcRSkIEH"  LIMIT 20;'
df = pd.read_sql(query, conn)

print(df.head())
conn.close()
