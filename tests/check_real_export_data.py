
from database.connection import get_connection


def main():
    print("=" * 60)
    print("GameTest AI 真实数据库导出条件检查")
    print("=" * 60)

    with get_connection() as conn:

        # 1. 检查数据库文件及核心数据表
        tables = [
            "test_case_generation_batches",
            "test_case_generation_batch_points",
            "test_case_candidates",
            "test_case_candidate_versions",
            "test_points",
            "requirement_analyses",
        ]

        print("\n一、数据表检查")

        existing_tables = {
            row["name"]
            for row in conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        for table in tables:
            status = "PASS" if table in existing_tables else "MISSING"
            print(f"{table}: {status}")

        missing = [
            table for table in tables
            if table not in existing_tables
        ]

        if missing:
            print("\n缺少必要数据表，停止检查。")
            return

        # 2. 检查生成批次
        print("\n二、生成批次")

        batches = conn.execute(
            """
            SELECT
                id,
                project_id,
                requirement_analysis_id,
                module,
                status,
                total_points,
                total_candidates,
                created_at
            FROM test_case_generation_batches
            ORDER BY created_at DESC
            """
        ).fetchall()

        if not batches:
            print("暂无测试用例生成批次")

        for batch in batches:
            print(
                f"批次 ID: {batch['id']}\n"
                f"模块: {batch['module']}\n"
                f"状态: {batch['status']}\n"
                f"来源测试点数: {batch['total_points']}\n"
                f"候选数: {batch['total_candidates']}\n"
                f"创建时间: {batch['created_at']}\n"
            )

        # 3. 检查候选用例审核状态
        print("\n三、候选用例审核状态")

        candidate_stats = conn.execute(
            """
            SELECT
                batch_id,
                manual_review_status,
                COUNT(*) AS candidate_count
            FROM test_case_candidates
            GROUP BY batch_id, manual_review_status
            ORDER BY batch_id
            """
        ).fetchall()

        if not candidate_stats:
            print("暂无候选用例")

        for row in candidate_stats:
            print(
                f"批次: {row['batch_id']} | "
                f"状态: {row['manual_review_status']} | "
                f"数量: {row['candidate_count']}"
            )

        # 4. 检查每个批次实际可导出的候选数量
        print("\n四、可导出候选统计")

        approved_stats = conn.execute(
            """
            SELECT
                b.id AS batch_id,
                b.status AS batch_status,
                COUNT(c.id) AS approved_count
            FROM test_case_generation_batches b
            LEFT JOIN test_case_candidates c
                ON c.batch_id = b.id
                AND c.manual_review_status = 'approved'
            GROUP BY b.id
            ORDER BY b.created_at DESC
            """
        ).fetchall()

        for row in approved_stats:
            print(
                f"批次: {row['batch_id']} | "
                f"批次状态: {row['batch_status']} | "
                f"已审核通过候选: {row['approved_count']}"
            )

        # 5. 检查已通过候选对应的版本和质量记录
        print("\n五、已通过候选的质量记录")

        quality_tables = [
            "test_case_validation_records",
            "test_case_reviewer_records",
        ]

        for table in quality_tables:
            if table not in existing_tables:
                print(f"{table}: MISSING")
                continue

            rows = conn.execute(
                f"""
                SELECT
                    c.batch_id,
                    COUNT(*) AS record_count
                FROM test_case_candidates c
                JOIN test_case_candidate_versions v
                    ON v.candidate_id = c.id
                    AND v.version_no = c.current_version
                JOIN {table} q
                    ON q.candidate_id = c.id
                    AND q.candidate_version_id = v.id
                WHERE c.manual_review_status = 'approved'
                GROUP BY c.batch_id
                """
            ).fetchall()

            print(f"\n{table}")

            if not rows:
                print("没有对应记录")

            for row in rows:
                print(
                    f"批次: {row['batch_id']} | "
                    f"记录数: {row['record_count']}"
                )

    print("\n" + "=" * 60)
    print("只读检查完成，未执行任何数据修改。")
    print("=" * 60)


if __name__ == "__main__":
    main()
