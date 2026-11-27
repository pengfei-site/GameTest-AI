"""测试点人工审核服务。"""

from database.repositories.test_point_repository import (
    approve_test_point as repository_approve_test_point,
    batch_approve_test_points as repository_batch_approve_test_points,
    batch_reject_test_points as repository_batch_reject_test_points,
    reject_test_point as repository_reject_test_point,
)


# 临时关闭人工审核时改为 False；恢复流程时改为 True。
MANUAL_REVIEW_ENABLED = False


def _ensure_manual_review_enabled():
    if not MANUAL_REVIEW_ENABLED:
        raise RuntimeError("人工审核流程当前已暂时关闭")


def _normalize_test_point_id(test_point_id: str) -> str:
    """校验并规范化单条测试点 ID。"""
    if not isinstance(test_point_id, str) or not test_point_id.strip():
        raise ValueError("test_point_id 不能为空")
    return test_point_id.strip()


def _normalize_comment(comment: str, field_name: str = "comment") -> str:
    """校验并规范化审核意见。"""
    if not isinstance(comment, str):
        raise TypeError(f"{field_name} 必须是字符串")
    return comment.strip()


def _normalize_test_point_ids(test_point_ids: list[str]) -> list[str]:
    """校验并规范化批量测试点 ID。"""
    if not isinstance(test_point_ids, list):
        raise TypeError("test_point_ids 必须是 list 类型")

    if not test_point_ids:
        raise ValueError("请选择至少一条测试点")

    normalized_ids = []

    for point_id in test_point_ids:
        if not isinstance(point_id, str) or not point_id.strip():
            raise ValueError("测试点 ID 不能为空")
        normalized_ids.append(point_id.strip())

    if len(normalized_ids) != len(set(normalized_ids)):
        raise ValueError("测试点 ID 不能重复")

    return normalized_ids


def approve_test_point(test_point_id: str, comment: str = "") -> dict:
    """人工审核通过单条测试点，审核意见可以为空。"""
    _ensure_manual_review_enabled()
    normalized_id = _normalize_test_point_id(test_point_id)
    normalized_comment = _normalize_comment(comment)

    repository_approve_test_point(
        normalized_id,
        normalized_comment,
    )

    return {
        "success": True,
        "test_point_id": normalized_id,
        "manual_review_status": "approved",
        "message": "测试点审核通过",
    }


def reject_test_point(test_point_id: str, reason: str) -> dict:
    """人工驳回单条测试点，必须填写驳回原因。"""
    _ensure_manual_review_enabled()
    normalized_id = _normalize_test_point_id(test_point_id)
    normalized_reason = _normalize_comment(reason, "reason")

    if not normalized_reason:
        raise ValueError("驳回原因不能为空")

    repository_reject_test_point(
        normalized_id,
        normalized_reason,
    )

    return {
        "success": True,
        "test_point_id": normalized_id,
        "manual_review_status": "rejected",
        "message": "测试点已驳回",
    }


def batch_approve_test_points(
    test_point_ids: list[str],
    comment: str = "",
) -> dict:
    """批量人工审核通过测试点，审核意见可以为空。"""
    _ensure_manual_review_enabled()
    normalized_ids = _normalize_test_point_ids(test_point_ids)
    normalized_comment = _normalize_comment(comment)

    repository_batch_approve_test_points(
        normalized_ids,
        normalized_comment,
    )

    return {
        "success": True,
        "test_point_ids": normalized_ids,
        "count": len(normalized_ids),
        "manual_review_status": "approved",
        "message": f"已批量通过 {len(normalized_ids)} 条测试点",
    }


def batch_reject_test_points(
    test_point_ids: list[str],
    reason: str,
) -> dict:
    """批量人工驳回测试点，必须填写驳回原因。"""
    _ensure_manual_review_enabled()
    normalized_ids = _normalize_test_point_ids(test_point_ids)
    normalized_reason = _normalize_comment(reason, "reason")

    if not normalized_reason:
        raise ValueError("批量驳回原因不能为空")

    repository_batch_reject_test_points(
        normalized_ids,
        normalized_reason,
    )

    return {
        "success": True,
        "test_point_ids": normalized_ids,
        "count": len(normalized_ids),
        "manual_review_status": "rejected",
        "message": f"已批量驳回 {len(normalized_ids)} 条测试点",
    }
