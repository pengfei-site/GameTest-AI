
import uuid
from typing import Literal

from database.connection import get_connection


ManualReviewAction = Literal[
    "approved",
    "rejected",
    "modified",
]


def create_manual_review(
    candidate_id: str,
    candidate_version_id: str,
    action_type: ManualReviewAction,
    comment: str = "",
) -> dict:
    """
    创建人工审核记录。

    approved: 审核通过
    rejected: 驳回，必须填写原因
    modified: 人工修改记录
    """

    valid_actions = {
        "approved",
        "rejected",
        "modified",
    }

    if action_type not in valid_actions:
        raise ValueError(
            f"不支持的审核操作类型：{action_type}"
        )

    if action_type == "rejected" and not comment.strip():
        raise ValueError("驳回操作必须填写驳回原因")

    review_id = str(uuid.uuid4())

    with get_connection(write=True) as conn:
        conn.execute(
            """
            INSERT INTO test_case_manual_reviews (
                id,
                candidate_id,
                candidate_version_id,
                action_type,
                comment
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                review_id,
                candidate_id,
                candidate_version_id,
                action_type,
                comment,
            ),
        )

        row = conn.execute(
            """
            SELECT *
            FROM test_case_manual_reviews
            WHERE id = ?
            """,
            (review_id,),
        ).fetchone()

    return dict(row)


def get_latest_manual_review(
    candidate_id: str,
    candidate_version_id: str,
) -> dict | None:
    """
    查询指定候选用例版本的最新人工审核记录。
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_manual_reviews
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

    return dict(row)


def list_manual_reviews(
    candidate_id: str,
) -> list[dict]:
    """
    查询指定候选用例的全部人工审核历史。

    按审核时间从早到晚排列。
    """

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_manual_reviews
            WHERE candidate_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (candidate_id,),
        ).fetchall()

    return [
        dict(row)
        for row in rows
    ]
