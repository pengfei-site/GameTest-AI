
from database.connection import get_connection


def main():
    print("开始检查测试用例相关数据库表结构……")

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT name, sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name LIKE 'test_case_%'
            ORDER BY name
        """).fetchall()

        if not rows:
            print("没有找到 test_case_% 相关数据表。")
            return

        print(f"\n共找到 {len(rows)} 张表。")

        for row in rows:
            print(f"\n========== {row['name']} ==========")
            print(row['sql'])


if __name__ == "__main__":
    main()
