
import json

from pydantic import ValidationError

from core.ai_client import ai_client
from core.case_schemas import TestCaseCandidateCollection
from core.review_schemas import TestCaseReviewResult
from core.schemas import RequirementAnalysis, TestPoint
from core.testcase_review_prompt import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)


MAX_REVIEW_ATTEMPTS = 3


def _build_manual_review_result(
    candidate_count: int,
    reason: str,
) -> TestCaseReviewResult:
    """
    Reviewer 多次失败时的安全降级结果。

    所有候选用例进入人工复核，不自动通过。
    """

    return TestCaseReviewResult(
        overall_status="needs_review",
        summary=(
            "AI Reviewer 多次未能返回有效审查结果，"
            "本次无法可靠完成自动审查。"
            f"原因：{reason[:500]}。"
            "所有候选用例均已转入人工复核。"
        ),
        issues=[],
        approved_candidate_indices=[],
        review_candidate_indices=list(
            range(1, candidate_count + 1)
        ),
    )


def review_testcases(
    requirement: RequirementAnalysis,
    test_point: TestPoint,
    candidates: TestCaseCandidateCollection,
) -> TestCaseReviewResult:
    """
    AI 测试用例审查。

    1. 只负责审查，不修改候选用例正文。
    2. 候选用例序号从 1 开始。
    3. 所有候选用例必须进入通过或人工复核列表。
    4. 未分类候选用例自动进入人工复核列表。
    5. JSON 或 Schema 校验失败时有限重试。
    6. 多次失败后全部转入人工复核。
    """

    candidate_count = len(candidates.candidates)

    if candidate_count == 0:
        return TestCaseReviewResult(
            overall_status="needs_review",
            summary="本次没有可供审查的候选测试用例。",
            issues=[],
            approved_candidate_indices=[],
            review_candidate_indices=[],
        )

    requirement_json = requirement.model_dump_json(indent=2)
    test_point_json = test_point.model_dump_json(indent=2)
    candidates_json = candidates.model_dump_json(indent=2)

    base_prompt = USER_PROMPT_TEMPLATE.format(
        requirement_analysis=requirement_json,
        test_point=test_point_json,
        candidates=candidates_json,
    )

    user_prompt = base_prompt
    result = None
    last_error = None

    # 第一阶段：AI 调用、JSON 解析和 Schema 校验
    for attempt in range(1, MAX_REVIEW_ATTEMPTS + 1):
        try:
            raw_result = ai_client.chat_json(
                SYSTEM_PROMPT,
                user_prompt,
            )

            data = json.loads(raw_result)

            if not isinstance(data, dict):
                raise ValueError(
                    "AI Reviewer 返回结果必须是 JSON 对象"
                )

            result = TestCaseReviewResult.model_validate(data)

            break

        except (ValueError, ValidationError) as exc:
            last_error = exc

            print(
                f"[TestCase Reviewer] 第 {attempt}/"
                f"{MAX_REVIEW_ATTEMPTS} 次审查失败：{exc}"
            )

            if attempt >= MAX_REVIEW_ATTEMPTS:
                break

            user_prompt = (
                base_prompt
                + "\n\n【审查结果格式错误，请重新完成审查】\n"
                + f"上一次错误：{str(exc)[:1500]}\n"
                + "请重新审查全部候选用例，并重新生成完整 JSON。"
                + "必须完整输出 overall_status、summary、issues、"
                + "approved_candidate_indices、review_candidate_indices。"
                + "approved_candidate_indices 和 "
                + "review_candidate_indices 必须是整数数组。"
                + "所有候选序号必须且只能归入其中一个列表。"
                + "没有内容的数组必须输出 []。"
                + "不得输出空字段值、null 或不完整 JSON。"
                + "只输出完整 JSON，不要解释。"
            )

    if result is None:
        print(
            "[TestCase Reviewer] 多次尝试仍失败，"
            "所有候选用例转入人工复核。"
        )

        return _build_manual_review_result(
            candidate_count,
            str(last_error or "未知错误"),
        )

    # 第二阶段：保留原有候选序号检查和分类规则

    valid_indices = set(
        range(1, candidate_count + 1)
    )

    # 检查问题记录中的候选序号
    valid_issues = []

    for issue in result.issues:
        if issue.candidate_index not in valid_indices:
            print(
                "[Reviewer Warning] 忽略无效候选序号的问题记录："
                f"{issue.candidate_index}"
            )
            continue

        valid_issues.append(issue)

    # 清理无效候选序号
    approved_indices = {
        index
        for index in result.approved_candidate_indices
        if index in valid_indices
    }

    review_indices = {
        index
        for index in result.review_candidate_indices
        if index in valid_indices
    }

    # 有问题的候选用例必须进入人工复核
    issue_indices = {
        issue.candidate_index
        for issue in valid_issues
    }

    review_indices.update(issue_indices)

    # 有问题的候选不能同时进入通过列表
    approved_indices.difference_update(issue_indices)

    # 复核列表优先
    approved_indices.difference_update(review_indices)

    # 未分类候选自动进入人工复核
    classified_indices = (
        approved_indices | review_indices
    )

    unclassified_indices = (
        valid_indices - classified_indices
    )

    if unclassified_indices:
        print(
            "[Reviewer Warning] 发现未分类候选用例，"
            f"自动转入人工复核：{sorted(unclassified_indices)}"
        )

        review_indices.update(unclassified_indices)

    # 按原始候选顺序输出
    approved_indices = sorted(approved_indices)
    review_indices = sorted(review_indices)

    # 修正整体审查状态
    overall_status = result.overall_status

    if review_indices and overall_status == "passed":
        overall_status = "needs_review"

    # 如果发现 critical 问题，不能维持 passed
    has_critical_issue = any(
        issue.severity == "critical"
        for issue in valid_issues
    )

    if has_critical_issue:
        overall_status = "failed"

    return TestCaseReviewResult(
        overall_status=overall_status,
        summary=result.summary,
        issues=valid_issues,
        approved_candidate_indices=approved_indices,
        review_candidate_indices=review_indices,
    )
