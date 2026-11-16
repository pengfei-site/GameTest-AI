import json

from database.connection import get_connection


SOURCE_BATCH_ID = "609483f6-2498-4e18-ab97-734140626b27"


def main():
    with get_connection() as conn:

        print("=" * 60)
        print("一、原始测试点生成批次")
        print("=" * 60)

        batch = conn.execute(
            """
            SELECT *
            FROM generation_batches
            WHERE id = ?
            """,
            (SOURCE_BATCH_ID,),
        ).fetchone()

        if batch is None:
            print("未找到原始测试点批次")
            return

        print(json.dumps(
            dict(batch),
            ensure_ascii=False,
            indent=2,
            default=str,
        ))

        print("\n" + "=" * 60)
        print("二、已审核通过的测试点")
        print("=" * 60)

        points = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE batch_id = ?
              AND manual_review_status = 'approved'
              AND is_deleted = 0
            ORDER BY point_id
            """,
            (SOURCE_BATCH_ID,),
        ).fetchall()

        for point in points:
            data = dict(point)

            for field in ("original_content", "current_content"):
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except (json.JSONDecodeError, TypeError):
                        pass

            print(json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
                default=str,
            ))

        print("\n" + "=" * 60)
        print("三、关联需求分析")
        print("=" * 60)

        # 展示项目中现有需求分析记录，供核对
        analyses = conn.execute(
            """
            SELECT id, project_id, module, summary, created_at
            FROM requirement_analyses
            ORDER BY created_at DESC
            """
        ).fetchall()

        for analysis in analyses:
            print(json.dumps(
                dict(analysis),
                ensure_ascii=False,
                indent=2,
                default=str,
            ))

        print("\n只读检查结束，没有修改数据库。")


if __name__ == "__main__":
    main()