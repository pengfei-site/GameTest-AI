
from database.connection import get_connection


GENERATION_BATCH_ID = (
    "859f58c4-a442-4be4-94dd-f39b39b10d07"
)

CANDIDATE_ID = (
    "f5656d37-6a53-4f69-85a0-adf4994908ca"
)

EXPECTED_MVP_TABLES = [
    "test_case_generation_batches",
    "test_case_generation_batch_points",
    "test_case_candidates",
    "test_case_candidate_versions",
    "test_case_validation_records",
    "test_case_reviewer_records",
    "test_case_manual_reviews",
]


def rows_to_dict(cursor, rows):
    columns = [item[0] for item in cursor.description]
    return [
        dict(zip(columns, row))
        for row in rows
    ]


def print_section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main():
    with get_connection() as conn:

        # 1. 数据表检查
        print_section("一、数据库表检查")

        tables = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        table_names = [row[0] for row in tables]

        print("实际业务表数量:", len(table_names))
        print("预期业务表数量: 13")

        for name in table_names:
            print(
                "[PASS]" if name in table_names else "[FAIL]",
                name,
            )

        for name in EXPECTED_MVP_TABLES:
            status = (
                "PASS" if name in table_names else "FAIL"
            )
            print(f"[{status}] MVP-1 表: {name}")

        # 2. 外键检查
        print_section("二、外键完整性检查")

        foreign_key_errors = conn.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if not foreign_key_errors:
            print("[PASS] 未发现外键完整性问题")
        else:
            print("[FAIL] 发现外键问题:")
            for error in foreign_key_errors:
                print(error)

        # 3. 索引检查
        print_section("三、数据库索引检查")

        index_count = 0

        for table_name in table_names:
            cursor = conn.execute(
                f'PRAGMA index_list("{table_name}")'
            )
            indexes = cursor.fetchall()

            for index in indexes:
                index_count += 1
                print(
                    f"[INDEX] {table_name}: {index[1]}"
                )

        print("实际索引总数:", index_count)
        print("此前基线索引数量: 20")

        # 4. 数据表记录数量
        print_section("四、业务数据记录数量")

        for table_name in table_names:
            count = conn.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            print(f"{table_name}: {count}")

        # 5. 本次生成批次
        print_section("五、本次真实生成批次")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batches
            WHERE id = ?
            """,
            (GENERATION_BATCH_ID,),
        )

        batch_rows = rows_to_dict(
            cursor, cursor.fetchall()
        )

        for item in batch_rows:
            print(item)

        if not batch_rows:
            print("[FAIL] 未找到本次生成批次")

        # 6. 候选用例
        print_section("六、本次候选用例")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_candidates
            WHERE id = ?
              AND batch_id = ?
            """,
            (CANDIDATE_ID, GENERATION_BATCH_ID),
        )

        candidate_rows = rows_to_dict(
            cursor, cursor.fetchall()
        )

        for item in candidate_rows:
            print(item)

        if not candidate_rows:
            print("[FAIL] 未找到候选用例")

        # 7. 候选版本
        print_section("七、候选版本记录")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_candidate_versions
            WHERE candidate_id = ?
            ORDER BY version_no
            """,
            (CANDIDATE_ID,),
        )

        for item in rows_to_dict(
            cursor, cursor.fetchall()
        ):
            print(item)

        # 8. Python Validator
        print_section("八、Python Validator 记录")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_validation_records
            WHERE candidate_id = ?
            ORDER BY rowid
            """,
            (CANDIDATE_ID,),
        )

        for item in rows_to_dict(
            cursor, cursor.fetchall()
        ):
            print(item)

        # 9. AI Reviewer
        print_section("九、AI Reviewer 记录")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_records
            WHERE candidate_id = ?
            ORDER BY rowid
            """,
            (CANDIDATE_ID,),
        )

        for item in rows_to_dict(
            cursor, cursor.fetchall()
        ):
            print(item)

        # 10. 人工审核
        print_section("十、人工审核记录")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_manual_reviews
            WHERE candidate_id = ?
            ORDER BY rowid
            """,
            (CANDIDATE_ID,),
        )

        for item in rows_to_dict(
            cursor, cursor.fetchall()
        ):
            print(item)

        # 11. 批次测试点快照
        print_section("十一、生成批次测试点快照")

        cursor = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batch_points
            WHERE batch_id = ?
            """,
            (GENERATION_BATCH_ID,),
        )

        snapshot_rows = rows_to_dict(
            cursor, cursor.fetchall()
        )

        for item in snapshot_rows:
            print(item)

        if not snapshot_rows:
            print("[FAIL] 未找到测试点快照")

    print_section("检查结束")
    print("本脚本仅执行查询，没有修改数据库。")


if __name__ == "__main__":
    main()
