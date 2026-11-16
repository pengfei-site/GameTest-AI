
import json

from database.connection import get_connection


BATCH_ID = "859f58c4-a442-4be4-94dd-f39b39b10d07"


def main():
    with get_connection() as conn:

        print("=" * 60)
        print("一、真实候选用例")
        print("=" * 60)

        candidates = conn.execute(
            """
            SELECT
                id,
                batch_id,
                batch_point_id,
                candidate_no,
                current_version,
                current_content_json,
                manual_review_status
            FROM test_case_candidates
            WHERE batch_id = ?
            ORDER BY candidate_no
            """,
            (BATCH_ID,),
        ).fetchall()

        for row in candidates:
            item = dict(row)
            item["current_content"] = json.loads(
                item.pop("current_content_json")
            )

            print(json.dumps(
                item,
                ensure_ascii=False,
                indent=2,
            ))

        print("\n" + "=" * 60)
        print("二、Python Validator 记录")
        print("=" * 60)

        validations = conn.execute(
            """
            SELECT
                candidate_id,
                candidate_version_id,
                passed,
                error_count,
                warning_count,
                report_json
            FROM test_case_validation_records
            WHERE candidate_id IN (
                SELECT id
                FROM test_case_candidates
                WHERE batch_id = ?
            )
            """,
            (BATCH_ID,),
        ).fetchall()

        for row in validations:
            item = dict(row)
            item["report"] = json.loads(
                item.pop("report_json")
            )

            print(json.dumps(
                item,
                ensure_ascii=False,
                indent=2,
            ))

        print("\n" + "=" * 60)
        print("三、AI Reviewer 记录")
        print("=" * 60)

        reviews = conn.execute(
            """
            SELECT
                candidate_id,
                candidate_version_id,
                overall_status,
                summary,
                report_json,
                model_name
            FROM test_case_reviewer_records
            WHERE candidate_id IN (
                SELECT id
                FROM test_case_candidates
                WHERE batch_id = ?
            )
            """,
            (BATCH_ID,),
        ).fetchall()

        for row in reviews:
            item = dict(row)
            item["report"] = json.loads(
                item.pop("report_json")
            )

            print(json.dumps(
                item,
                ensure_ascii=False,
                indent=2,
            ))

    print("\n只读检查完成，未修改数据库。")


if __name__ == "__main__":
    main()
