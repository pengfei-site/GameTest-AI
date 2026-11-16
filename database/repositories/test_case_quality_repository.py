
import json
import uuid

from core.case_schemas import TestCaseValidationReport
from core.review_schemas import TestCaseReviewResult
from database.connection import get_connection


REVIEWER_CONFIRMATION_STATUSES = {
    "confirmed_passed",
    "confirmed_issues",
    "recheck_required",
}


def create_validation_record(
    candidate_id: str,
    candidate_version_id: str,
    report: TestCaseValidationReport,
    conn=None,
) -> dict:
    """保存 Python 自动校验报告。"""
    record_id = str(uuid.uuid4())

    report_json = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
    )

    def _insert(connection):
        connection.execute(
            """
            INSERT INTO test_case_validation_records (
                id,
                candidate_id,
                candidate_version_id,
                passed,
                error_count,
                warning_count,
                report_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                candidate_id,
                candidate_version_id,
                int(report.passed),
                report.error_count,
                report.warning_count,
                report_json,
            ),
        )

        row = connection.execute(
            """
            SELECT *
            FROM test_case_validation_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

        return _row_to_validation_record(row)

    if conn is not None:
        return _insert(conn)

    with get_connection(write=True) as connection:
        return _insert(connection)


def get_latest_validation_record(
    candidate_id: str,
    candidate_version_id: str,
) -> dict | None:
    """查询指定候选版本的最新 Python 校验记录。"""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_validation_records
            WHERE candidate_id = ?
              AND candidate_version_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (
                candidate_id,
                candidate_version_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return _row_to_validation_record(row)


def create_reviewer_record(
    candidate_id: str,
    candidate_version_id: str,
    report: TestCaseReviewResult,
    model_name: str | None = None,
    conn=None,
) -> dict:
    """保存 AI Reviewer 审查报告。"""
    record_id = str(uuid.uuid4())

    report_json = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
    )

    def _insert(connection):
        connection.execute(
            """
            INSERT INTO test_case_reviewer_records (
                id,
                candidate_id,
                candidate_version_id,
                overall_status,
                summary,
                report_json,
                model_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                candidate_id,
                candidate_version_id,
                report.overall_status,
                report.summary,
                report_json,
                model_name,
            ),
        )

        row = connection.execute(
            """
            SELECT *
            FROM test_case_reviewer_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

        return _row_to_reviewer_record(row)

    if conn is not None:
        return _insert(conn)

    with get_connection(write=True) as connection:
        return _insert(connection)


def get_latest_reviewer_record(
    candidate_id: str,
    candidate_version_id: str,
) -> dict | None:
    """查询指定候选版本的最新 AI Reviewer 审查记录。"""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_records
            WHERE candidate_id = ?
              AND candidate_version_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (
                candidate_id,
                candidate_version_id,
            ),
        ).fetchone()

    if row is None:
        return None

    return _row_to_reviewer_record(row)


def list_reviewer_records(
    candidate_id: str,
    candidate_version_id: str,
) -> list[dict]:
    """查询指定候选、指定版本的全部 AI Reviewer 历史记录。"""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_records
            WHERE candidate_id = ?
              AND candidate_version_id = ?
            ORDER BY created_at DESC, rowid DESC
            """,
            (
                candidate_id,
                candidate_version_id,
            ),
        ).fetchall()

    return [
        _row_to_reviewer_record(row)
        for row in rows
    ]


def create_reviewer_confirmation(
    reviewer_record_id: str,
    candidate_id: str,
    candidate_version_id: str,
    confirmation_status: str,
    confirmed_by: str,
    confirmation_comment: str = "",
) -> dict:
    """
    创建一条 AI Reviewer 人工确认记录。

    每次确认均新增记录，不覆盖历史记录。
    """
    required_fields = {
        "reviewer_record_id": reviewer_record_id,
        "candidate_id": candidate_id,
        "candidate_version_id": candidate_version_id,
        "confirmation_status": confirmation_status,
        "confirmed_by": confirmed_by,
    }

    for field_name, value in required_fields.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} 不能为空。")

    if confirmation_status not in REVIEWER_CONFIRMATION_STATUSES:
        raise ValueError(
            "confirmation_status 不合法，允许的值为："
            "confirmed_passed、confirmed_issues、recheck_required。"
        )

    if not isinstance(confirmation_comment, str):
        raise ValueError("confirmation_comment 必须是字符串。")

    confirmation_id = str(uuid.uuid4())

    with get_connection(write=True) as conn:
        reviewer_row = conn.execute(
            """
            SELECT id
            FROM test_case_reviewer_records
            WHERE id = ?
              AND candidate_id = ?
              AND candidate_version_id = ?
            """,
            (
                reviewer_record_id,
                candidate_id,
                candidate_version_id,
            ),
        ).fetchone()

        if reviewer_row is None:
            raise ValueError(
                "Reviewer 报告不存在，或报告与指定候选版本不匹配。"
            )

        conn.execute(
            """
            INSERT INTO test_case_reviewer_confirmations (
                id,
                reviewer_record_id,
                candidate_id,
                candidate_version_id,
                confirmation_status,
                confirmation_comment,
                confirmed_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                confirmation_id,
                reviewer_record_id,
                candidate_id,
                candidate_version_id,
                confirmation_status,
                confirmation_comment,
                confirmed_by,
            ),
        )

        row = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_confirmations
            WHERE id = ?
            """,
            (confirmation_id,),
        ).fetchone()

    return _row_to_reviewer_confirmation(row)


def get_latest_reviewer_confirmation(
    reviewer_record_id: str,
) -> dict | None:
    """查询指定 AI Reviewer 报告的最新人工确认记录。"""
    if not isinstance(reviewer_record_id, str) or not reviewer_record_id.strip():
        raise ValueError("reviewer_record_id 不能为空。")

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_confirmations
            WHERE reviewer_record_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (reviewer_record_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_reviewer_confirmation(row)


def list_reviewer_confirmations(
    reviewer_record_id: str,
) -> list[dict]:
    """查询指定 AI Reviewer 报告的全部人工确认历史。"""
    if not isinstance(reviewer_record_id, str) or not reviewer_record_id.strip():
        raise ValueError("reviewer_record_id 不能为空。")

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_confirmations
            WHERE reviewer_record_id = ?
            ORDER BY created_at DESC, rowid DESC
            """,
            (reviewer_record_id,),
        ).fetchall()

    return [
        _row_to_reviewer_confirmation(row)
        for row in rows
    ]


def list_version_reviewer_confirmations(
    candidate_id: str,
    candidate_version_id: str,
) -> list[dict]:
    """查询指定候选版本下的全部人工确认记录。"""
    if not candidate_id or not candidate_version_id:
        raise ValueError(
            "candidate_id 和 candidate_version_id 不能为空。"
        )

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_confirmations
            WHERE candidate_id = ?
              AND candidate_version_id = ?
            ORDER BY created_at DESC, rowid DESC
            """,
            (
                candidate_id,
                candidate_version_id,
            ),
        ).fetchall()

    return [
        _row_to_reviewer_confirmation(row)
        for row in rows
    ]


def _row_to_validation_record(row) -> dict:
    """将 Python 校验记录转换为字典。"""
    result = dict(row)
    result["report"] = json.loads(result.pop("report_json"))
    return result


def _row_to_reviewer_record(row) -> dict:
    """将 AI Reviewer 审查记录转换为字典。"""
    result = dict(row)
    result["report"] = json.loads(result.pop("report_json"))
    return result


def _row_to_reviewer_confirmation(row) -> dict:
    """将 AI Reviewer 人工确认记录转换为字典。"""
    return dict(row)
