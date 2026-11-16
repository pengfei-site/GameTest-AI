
import json

from core.ai_client import ai_client
from core.case_schemas import TestCaseCandidateCollection
from core.review_schemas import TestCaseReviewResult
from core.schemas import RequirementAnalysis, TestPoint
from core.testcase_review_prompt import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)


def review_testcases(
    requirement: RequirementAnalysis,
    test_point: TestPoint,
    candidates: TestCaseCandidateCollection,
) -> TestCaseReviewResult:
    """
    AI 测试用例审查。

    输入：
        requirement: 原始需求分析
        test_point: 来源测试点
        candidates: AI 生成的候选测试用例集合

    输出：
        TestCaseReviewResult: AI 审查报告

    注意：
        1. 只负责审查，不修改候选用例正文。
        2. 候选用例序号从 1 开始。
        3. 所有候选用例必须进入通过或人工复核列表。
        4. 未分类候选用例自动进入人工复核列表。
    """

    candidate_count = len(candidates.candidates)

    # 特殊情况：没有候选用例
    if candidate_count == 0:
        return TestCaseReviewResult(
            overall_status="needs_review",
            summary="本次没有可供审查的候选测试用例。",
            issues=[],
            approved_candidate_indices=[],
            review_candidate_indices=[],
        )

    # 序列化审查输入
    requirement_json = requirement.model_dump_json(
        indent=2
    )

    test_point_json = test_point.model_dump_json(
        indent=2
    )

    candidates_json = candidates.model_dump_json(
        indent=2
    )

    # 构造用户提示词
    user_prompt = USER_PROMPT_TEMPLATE.format(
        requirement_analysis=requirement_json,
        test_point=test_point_json,
        candidates=candidates_json,
    )

    # 调用 AI
    raw_result = ai_client.chat_json(
        SYSTEM_PROMPT,
        user_prompt,
    )

    # 解析 JSON
    data = json.loads(raw_result)

    if not isinstance(data, dict):
        raise ValueError("AI Reviewer 返回结果必须是 JSON 对象")

    # 解析审查结果 Schema
    result = TestCaseReviewResult.model_validate(data)

    valid_indices = set(
        range(1, candidate_count + 1)
    )

    # 检查问题记录中的候选序号
    valid_issues = []

    for issue in result.issues:
        if issue.candidate_index not in valid_indices:
            print(
                "[Reviewer Warning] "
                f"忽略无效候选序号的问题记录："
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

    # 存在问题的候选用例不能同时进入通过列表
    approved_indices.difference_update(issue_indices)

    # 复核列表优先，避免同一候选重复分类
    approved_indices.difference_update(review_indices)

    # 未分类候选用例不能默认通过
    classified_indices = (
        approved_indices | review_indices
    )

    unclassified_indices = (
        valid_indices - classified_indices
    )

    if unclassified_indices:
        print(
            "[Reviewer Warning] "
            f"发现未分类候选用例，自动转入人工复核："
            f"{sorted(unclassified_indices)}"
        )

        review_indices.update(unclassified_indices)

    # 按候选用例原始顺序输出
    approved_indices = sorted(approved_indices)
    review_indices = sorted(review_indices)

    # 修正整体审查状态
    overall_status = result.overall_status

    if overall_status == "passed" and review_indices:
        overall_status = "needs_review"

    # 生成最终审查报告
    final_result = TestCaseReviewResult(
        overall_status=overall_status,
        summary=result.summary,
        issues=valid_issues,
        approved_candidate_indices=approved_indices,
        review_candidate_indices=review_indices,
    )

    return final_result
