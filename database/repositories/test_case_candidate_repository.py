
import json
import uuid

from core.case_schemas import TestCaseCandidate
from database.connection import get_connection


def _serialize_content(candidate: TestCaseCandidate) -> str:
    """将候选用例序列化为 JSON 字符串。"""
    return json.dumps(
        candidate.model_dump(mode="json"),
        ensure_ascii=False,
    )


def _deserialize_content(content_json: str) -> dict:
    """将 JSON 字符串反序列化为字典。"""
    return json.loads(content_json)


def _row_to_candidate(row) -> dict:
    """将数据库候选记录转换为字典。"""
    result = dict(row)

    result["current_content"] = _deserialize_content(
        result.pop("current_content_json")
    )

    return result


def _row_to_version(row) -> dict:
    """将数据库版本记录转换为字典。"""
    result = dict(row)

    result["content"] = _deserialize_content(
        result.pop("content_json")
    )

    return result


def create_candidate(
    batch_id: str,
    batch_point_id: str,
    candidate_no: int,
    candidate: TestCaseCandidate,
) -> dict:
    """
    创建测试用例候选，并同步创建初始版本 V1。

    Args:
        batch_id: 测试用例生成批次 ID
        batch_point_id: 批次关联测试点记录 ID
        candidate_no: 当前测试点下的候选用例序号
        candidate: 已通过 Schema 校验的候选用例

    Returns:
        创建后的候选用例记录
    """

    if candidate_no < 1:
        raise ValueError("candidate_no 必须大于或等于 1")

    candidate_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    content_json = _serialize_content(candidate)

    with get_connection(write=True) as conn:
        conn.execute(
            """
            INSERT INTO test_case_candidates (
                id,
                batch_id,
                batch_point_id,
                candidate_no,
                current_content_json,
                current_version,
                manual_review_status
            )
            VALUES (?, ?, ?, ?, ?, 1, 'pending')
            """,
            (
                candidate_id,
                batch_id,
                batch_point_id,
                candidate_no,
                content_json,
            ),
        )

        conn.execute(
            """
            INSERT INTO test_case_candidate_versions (
                id,
                candidate_id,
                version_no,
                content_json,
                change_type
            )
            VALUES (?, ?, 1, ?, 'ai_generated')
            """,
            (
                version_id,
                candidate_id,
                content_json,
            ),
        )

        row = conn.execute(
            """
            SELECT *
            FROM test_case_candidates
            WHERE id = ?
            """,
            (candidate_id,),
        ).fetchone()

    return _row_to_candidate(row)


def get_candidate_by_id(candidate_id: str) -> dict | None:
    """根据候选用例 ID 查询候选记录。"""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_candidates
            WHERE id = ?
            """,
            (candidate_id,),
        ).fetchone()

    if row is None:
        return None

    return _row_to_candidate(row)


def list_candidates_by_batch(batch_id: str) -> list[dict]:
    """查询指定生成批次下的全部候选用例。"""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_candidates
            WHERE batch_id = ?
            ORDER BY batch_point_id, candidate_no
            """,
            (batch_id,),
        ).fetchall()

    return [
        _row_to_candidate(row)
        for row in rows
    ]


def list_candidate_versions(
    candidate_id: str,
) -> list[dict]:
    """查询候选用例的全部版本历史。"""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_candidate_versions
            WHERE candidate_id = ?
            ORDER BY version_no
            """,
            (candidate_id,),
        ).fetchall()

    return [
        _row_to_version(row)
        for row in rows
    ]
