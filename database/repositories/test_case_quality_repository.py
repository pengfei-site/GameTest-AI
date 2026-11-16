
import json
import uuid

from core.case_schemas import TestCaseValidationReport
from core.review_schemas import TestCaseReviewResult
from database.connection import get_connection


def create_validation_record(
    candidate_id: str,
    candidate_version_id: str,
    report: TestCaseValidationReport,
) -> dict:
    """
    保存 Python 自动校验报告。

    报告关联候选用例及其具体版本。
    """

    record_id = str(uuid.uuid4())

    report_json = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
    )

    with get_connection(write=True) as conn:
        conn.execute(
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

        row = conn.execute(
            """
            SELECT *
            FROM test_case_validation_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    return _row_to_validation_record(row)


def get_latest_validation_record(
    candidate_id: str,
    candidate_version_id: str,
) -> dict | None:
    """
    查询指定候选用例版本的最新 Python 校验记录。
    """

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
) -> dict:
    """
    保存 AI Reviewer 审查报告。

    报告关联候选用例及其具体版本。
    """

    record_id = str(uuid.uuid4())

    report_json = json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
    )

    with get_connection(write=True) as conn:
        conn.execute(
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

        row = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_records
            WHERE id = ?
            """,
            (record_id,),
        ).fetchone()

    return _row_to_reviewer_record(row)


def get_latest_reviewer_record(
    candidate_id: str,
    candidate_version_id: str,
) -> dict | None:
    """
    查询指定候选用例版本的最新 AI Reviewer 审查记录。
    """

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


def _row_to_validation_record(row) -> dict:
    """将 Python 校验记录转换为字典。"""

    result = dict(row)

    result["report"] = json.loads(
        result.pop("report_json")
    )

    return result


def _row_to_reviewer_record(row) -> dict:
    """将 AI Reviewer 审查记录转换为字典。"""

    result = dict(row)

    result["report"] = json.loads(
        result.pop("report_json")
    )

    return result
