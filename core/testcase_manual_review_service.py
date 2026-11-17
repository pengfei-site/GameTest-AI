
import json
import uuid

from core.case_schemas import TestCaseCandidate
from database.connection import get_connection


def _get_current_candidate(conn, candidate_id: str):
    """获取候选用例及其当前版本。"""

    candidate = conn.execute(
        """
        SELECT *
        FROM test_case_candidates
        WHERE id = ?
        """,
        (candidate_id,),
    ).fetchone()

    if candidate is None:
        raise ValueError("候选用例不存在")

    candidate = dict(candidate)

    version = conn.execute(
        """
        SELECT *
        FROM test_case_candidate_versions
        WHERE candidate_id = ?
          AND version_no = ?
        """,
        (
            candidate_id,
            candidate["current_version"],
        ),
    ).fetchone()

    if version is None:
        raise RuntimeError("候选用例当前版本记录不存在")

    return candidate, dict(version)



def _check_quality_records(conn, candidate_id, version_id):
    """检查当前版本的 Python 校验、Reviewer 审查和人工确认结果。"""

    validation = conn.execute(
        """
        SELECT *
        FROM test_case_validation_records
        WHERE candidate_id = ?
          AND candidate_version_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT 1
        """,
        (candidate_id, version_id),
    ).fetchone()

    if validation is None:
        raise ValueError("当前版本尚未执行 Python 自动校验")

    if not validation["passed"]:
        raise ValueError("当前版本 Python 自动校验未通过")

    reviewer = conn.execute(
        """
        SELECT *
        FROM test_case_reviewer_records
        WHERE candidate_id = ?
          AND candidate_version_id = ?
        ORDER BY created_at DESC, rowid DESC
        LIMIT 1
        """,
        (candidate_id, version_id),
    ).fetchone()

    if reviewer is None:
        raise ValueError("当前版本尚未执行 AI Reviewer 审查")

    reviewer_status = reviewer["overall_status"]

    # Reviewer 原始审查通过，直接允许进入人工审批流程。
    if reviewer_status == "passed":
        return

    # Reviewer 需要复核时，检查该报告对应的最新人工确认。
    if reviewer_status == "needs_review":
        confirmation = conn.execute(
            """
            SELECT *
            FROM test_case_reviewer_confirmations
            WHERE reviewer_record_id = ?
              AND candidate_id = ?
              AND candidate_version_id = ?
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (
                reviewer["id"],
                candidate_id,
                version_id,
            ),
        ).fetchone()

        if confirmation is None:
            raise ValueError(
                "AI Reviewer 需要人工复核，尚未完成人工确认"
            )

        if confirmation["confirmation_status"] != "confirmed_passed":
            raise ValueError(
                "AI Reviewer 人工确认未通过，不能执行人工审批"
            )

        return

    # failed 或其他未知状态不能由人工确认覆盖。
    raise ValueError(
        f"当前版本 AI Reviewer 状态为 {reviewer_status}，不能执行人工审批"
    )



def _insert_manual_review(
    conn,
    candidate_id,
    version_id,
    action_type,
    comment="",
):
    """写入人工审核记录。"""

    review_id = str(uuid.uuid4())

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
            version_id,
            action_type,
            comment,
        ),
    )

    return review_id


def approve_candidate(
    candidate_id: str,
    comment: str = "",
) -> dict:
    """
    人工审核通过。

    必须满足：
    1. 候选当前状态为 pending。
    2. 当前版本 Python Validator 通过。
    3. 当前版本 AI Reviewer 状态为 passed。
    """

    with get_connection(write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")

        candidate, version = _get_current_candidate(
            conn,
            candidate_id,
        )

        if candidate["manual_review_status"] != "pending":
            raise ValueError("只有待审核候选用例才能执行审核通过")

        _check_quality_records(
            conn,
            candidate_id,
            version["id"],
        )

        review_id = _insert_manual_review(
            conn,
            candidate_id,
            version["id"],
            "approved",
            comment,
        )

        conn.execute(
            """
            UPDATE test_case_candidates
            SET manual_review_status = 'approved',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (candidate_id,),
        )

        return {
            "candidate_id": candidate_id,
            "candidate_version_id": version["id"],
            "manual_review_status": "approved",
            "review_id": review_id,
        }


def reject_candidate(
    candidate_id: str,
    reason: str,
) -> dict:
    """
    人工驳回候选用例。

    驳回必须填写原因。
    """

    if not reason or not reason.strip():
        raise ValueError("驳回操作必须填写驳回原因")

    with get_connection(write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")

        candidate, version = _get_current_candidate(
            conn,
            candidate_id,
        )

        if candidate["manual_review_status"] != "pending":
            raise ValueError("只有待审核候选用例才能执行驳回操作")

        review_id = _insert_manual_review(
            conn,
            candidate_id,
            version["id"],
            "rejected",
            reason.strip(),
        )

        conn.execute(
            """
            UPDATE test_case_candidates
            SET manual_review_status = 'rejected',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (candidate_id,),
        )

        return {
            "candidate_id": candidate_id,
            "candidate_version_id": version["id"],
            "manual_review_status": "rejected",
            "review_id": review_id,
            "reason": reason.strip(),
        }


def modify_candidate(
    candidate_id: str,
    updated_candidate: TestCaseCandidate,
    comment: str = "",
) -> dict:
    """
    人工修改候选用例。

    1. 创建新的候选版本。
    2. 更新候选当前正文和版本号。
    3. 写入关联旧版本的 modified 审核记录。
    4. 将审核状态恢复为 pending。

    新版本的 Validator 和 Reviewer 由后续业务流程执行。
    """

    if not isinstance(updated_candidate, TestCaseCandidate):
        raise TypeError(
            "updated_candidate 必须是 TestCaseCandidate 类型"
        )

    content_json = json.dumps(
        updated_candidate.model_dump(mode="json"),
        ensure_ascii=False,
    )

    with get_connection(write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")

        candidate, old_version = _get_current_candidate(
            conn,
            candidate_id,
        )

        old_version_no = candidate["current_version"]
        new_version_no = old_version_no + 1
        new_version_id = str(uuid.uuid4())

        # 新增候选版本
        conn.execute(
            """
            INSERT INTO test_case_candidate_versions (
                id,
                candidate_id,
                version_no,
                content_json,
                change_type,
                change_note
            )
            VALUES (?, ?, ?, ?, 'manual_edit', ?)
            """,
            (
                new_version_id,
                candidate_id,
                new_version_no,
                content_json,
                comment,
            ),
        )

        # 写入人工修改记录，关联被修改的旧版本
        review_id = _insert_manual_review(
            conn,
            candidate_id,
            old_version["id"],
            "modified",
            comment,
        )

        # 更新候选当前版本
        conn.execute(
            """
            UPDATE test_case_candidates
            SET current_content_json = ?,
                current_version = ?,
                manual_review_status = 'pending',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                content_json,
                new_version_no,
                candidate_id,
            ),
        )

        return {
            "candidate_id": candidate_id,
            "old_version_id": old_version["id"],
            "old_version_no": old_version_no,
            "new_version_id": new_version_id,
            "new_version_no": new_version_no,
            "manual_review_status": "pending",
            "review_id": review_id,
        }


def _normalize_batch_candidate_ids(candidate_ids):
    """校验并去重批量审核候选 ID，保持原始顺序。"""

    if isinstance(candidate_ids, (str, bytes)):
        raise ValueError("candidate_ids 必须是候选 ID 列表")

    if not isinstance(candidate_ids, (list, tuple)):
        raise ValueError("candidate_ids 必须是列表或元组")

    normalized = []
    seen = set()

    for candidate_id in candidate_ids:
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("候选 ID 不能为空")

        candidate_id = candidate_id.strip()

        if candidate_id not in seen:
            seen.add(candidate_id)
            normalized.append(candidate_id)

    if not normalized:
        raise ValueError("请至少选择一个候选用例")

    return normalized


def batch_approve_candidates(candidate_ids, comment=""):
    """逐条执行批量人工审核通过，每条候选独立事务。"""

    candidate_ids = _normalize_batch_candidate_ids(candidate_ids)
    results = []

    for candidate_id in candidate_ids:
        try:
            result = approve_candidate(candidate_id, comment)
            results.append({
                "candidate_id": candidate_id,
                "success": True,
                "result": result,
                "error": "",
            })
        except Exception as exc:
            results.append({
                "candidate_id": candidate_id,
                "success": False,
                "result": None,
                "error": str(exc),
            })

    succeeded = sum(1 for item in results if item["success"])

    return {
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    }


def batch_reject_candidates(candidate_ids, reason):
    """逐条执行批量人工驳回，每条候选独立事务。"""

    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("批量驳回必须填写驳回原因")

    candidate_ids = _normalize_batch_candidate_ids(candidate_ids)
    reason = reason.strip()
    results = []

    for candidate_id in candidate_ids:
        try:
            result = reject_candidate(candidate_id, reason)
            results.append({
                "candidate_id": candidate_id,
                "success": True,
                "result": result,
                "error": "",
            })
        except Exception as exc:
            results.append({
                "candidate_id": candidate_id,
                "success": False,
                "result": None,
                "error": str(exc),
            })

    succeeded = sum(1 for item in results if item["success"])

    return {
        "total": len(results),
        "succeeded": succeeded,
        "failed": len(results) - succeeded,
        "results": results,
    }

