
from database.repositories import (
    test_case_quality_repository as quality_repo,
)


REVIEWER_CONFIRMATION_STATUSES = {
    "confirmed_passed",
    "confirmed_issues",
    "recheck_required",
}


def _validate_required_string(value: str, field_name: str) -> str:
    """校验必填字符串。"""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} 不能为空")

    return value.strip()


def confirm_reviewer_report(
    reviewer_record_id: str,
    candidate_id: str,
    candidate_version_id: str,
    confirmation_status: str,
    confirmed_by: str,
    confirmation_comment: str = "",
) -> dict:
    """
    对指定 AI Reviewer 报告提交人工确认。

    业务规则：
    1. 必须关联具体 Reviewer 报告。
    2. 必须关联正确的候选用例及版本。
    3. 只允许三种正式人工确认结果。
    4. 每次确认均新增历史记录。
    5. 不修改 AI Reviewer 原始报告。
    6. 不修改候选用例最终人工审核状态。

    返回：
        dict，包含本次人工确认记录。

    注意：
        关联关系不正确时由 Repository 拒绝写入。
    """
    reviewer_record_id = _validate_required_string(
        reviewer_record_id,
        "reviewer_record_id",
    )

    candidate_id = _validate_required_string(
        candidate_id,
        "candidate_id",
    )

    candidate_version_id = _validate_required_string(
        candidate_version_id,
        "candidate_version_id",
    )

    confirmed_by = _validate_required_string(
        confirmed_by,
        "confirmed_by",
    )

    if not isinstance(confirmation_status, str):
        raise ValueError("confirmation_status 不合法")

    confirmation_status = confirmation_status.strip()

    if confirmation_status not in REVIEWER_CONFIRMATION_STATUSES:
        raise ValueError(
            "confirmation_status 不合法，允许的值为："
            "confirmed_passed、confirmed_issues、recheck_required"
        )

    if not isinstance(confirmation_comment, str):
        raise ValueError("confirmation_comment 必须是字符串")

    return quality_repo.create_reviewer_confirmation(
        reviewer_record_id=reviewer_record_id,
        candidate_id=candidate_id,
        candidate_version_id=candidate_version_id,
        confirmation_status=confirmation_status,
        confirmed_by=confirmed_by,
        confirmation_comment=confirmation_comment.strip(),
    )


def get_latest_reviewer_confirmation(
    reviewer_record_id: str,
) -> dict:
    """
    查询指定 AI Reviewer 报告的最新人工确认结果。

    如果尚未人工确认：
        返回 confirmation_status="pending"。

    pending 仅用于页面展示，不写入数据库。
    """
    reviewer_record_id = _validate_required_string(
        reviewer_record_id,
        "reviewer_record_id",
    )

    record = quality_repo.get_latest_reviewer_confirmation(
        reviewer_record_id
    )

    if record is None:
        return {
            "reviewer_record_id": reviewer_record_id,
            "confirmation_status": "pending",
            "confirmation": None,
        }

    return {
        "reviewer_record_id": reviewer_record_id,
        "confirmation_status": record["confirmation_status"],
        "confirmation": record,
    }


def list_reviewer_confirmation_history(
    reviewer_record_id: str,
) -> list[dict]:
    """
    查询指定 AI Reviewer 报告的全部人工确认历史。

    按 Repository 提供的创建时间倒序返回。
    """
    reviewer_record_id = _validate_required_string(
        reviewer_record_id,
        "reviewer_record_id",
    )

    return quality_repo.list_reviewer_confirmations(
        reviewer_record_id
    )


def batch_confirm_reviewer_reports(
    confirmations: list[dict],
    confirmation_status: str,
    confirmed_by: str,
    confirmation_comment: str = "",
) -> dict:
    """
    批量提交 AI Reviewer 人工确认。

    每条记录均调用 confirm_reviewer_report，
    复用单条确认的全部校验和持久化逻辑。

    confirmations 中每项必须包含：
        reviewer_record_id
        candidate_id
        candidate_version_id

    可选：
        confirmation_comment
    """

    if not isinstance(confirmations, (list, tuple)):
        raise ValueError("confirmations 必须是列表或元组")

    if not confirmations:
        raise ValueError("请选择至少一条需要人工确认的记录")

    results = []

    for item in confirmations:
        candidate_id = (
            item.get("candidate_id")
            if isinstance(item, dict)
            else None
        )

        try:
            if not isinstance(item, dict):
                raise ValueError("确认记录必须是字典")

            result = confirm_reviewer_report(
                reviewer_record_id=item["reviewer_record_id"],
                candidate_id=item["candidate_id"],
                candidate_version_id=item["candidate_version_id"],
                confirmation_status=confirmation_status,
                confirmed_by=confirmed_by,
                confirmation_comment=item.get(
                    "confirmation_comment",
                    confirmation_comment,
                ),
            )

            results.append({
                "candidate_id": candidate_id,
                "success": True,
                "result": result,
                "error": None,
            })

        except Exception as exc:
            results.append({
                "candidate_id": candidate_id,
                "success": False,
                "result": None,
                "error": str(exc),
            })

    succeeded = sum(
        1 for item in results if item["success"]
    )
    failed = len(results) - succeeded

    return {
        "total": len(results),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }

