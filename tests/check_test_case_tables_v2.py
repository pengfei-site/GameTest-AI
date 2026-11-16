import sqlite3
from database.connection import DB_PATH

print("数据库路径：", DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT name, sql
    FROM sqlite_master
    WHERE type = 'table'
      AND name LIKE 'test_case_%'
    ORDER BY name
""").fetchall()

print(f"\n共找到 {len(rows)} 张表。")

for row in rows:
    print(f"\n========== {row['name']} ==========")
    print(row['sql'])

conn.close()
