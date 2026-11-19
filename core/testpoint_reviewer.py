
import json

from core.ai_client import ai_client
from core.schemas import RequirementAnalysis, TestPointCollection
from core.review_schemas import TestPointReviewResult


SYSTEM_PROMPT = """
你是一名拥有丰富游戏测试经验的高级游戏测试负责人。

你的任务是审查 AI 生成的游戏测试点，判断其是否符合原始需求，
是否存在逻辑错误、无依据推断和测试覆盖问题。

【审查原则】

1. 必须以输入的 RequirementAnalysis 为需求依据。
2. 不得把需求未明确的规则推断为确定结论。
3. 不得把“满足条件时可以”擅自推断为“不满足条件时一定不可以”。
4. 不得把待确认事项写成确定的预期结果。
5. 检查数值计算是否正确。
6. 检查测试点是否存在重复或覆盖重叠。
7. 检查测试点是否遗漏重要的正向、反向、边界、异常和状态场景。
8. 不要因为测试点关联了其他规则，就直接认定其错误。
9. 不要为了增加测试点数量而创造需求中没有的测试场景。
10. 对于需求本身不明确的情况，应提出待确认建议，而不是自行补充规则。

【特别注意】

- R1“每天可以免费领取一次体力”不能单独证明具体的重置时间。
- R4“当前体力不足100点时，可以领取”不能直接推导出体力等于100时一定禁止领取。
- R3“体力上限100点”不能单独证明超过上限时一定截断为100点。
- 需求中未明确的行为，应标记为待确认。

【数值推理补充规则】

1. 必须进行明确的数值计算，不要仅因为需求存在未确认规则就判定所有相关测试点有问题。

2. 当初始数值 + 增加数值 <= 已明确的上限时，
   如果最终数值仍然低于或等于上限，则该场景不涉及溢出处理。

3. 例如：
   - 当前体力50点
   - 领取增加20点
   - 体力上限100点
   - 最终体力70点

   该场景不触发上限，不需要等待策划确认截断规则。

4. 当初始数值 + 增加数值 > 上限时，
   才需要审查溢出处理规则是否明确。

5. 必须区分测试点中的不同验证目标。
   一个测试点包含多个验证目标时，如果只有部分目标存在待确认事项，
   不应直接否定其他有明确需求依据的验证目标。
   应在问题描述中明确指出具体需要复核的部分。

【审查状态】

passed：
没有发现需要人工复核的问题。

needs_review：
存在需要人工判断或向策划确认的问题。

failed：
存在明确的逻辑错误、需求冲突或严重问题。

【问题类型】

logic_error：明确的逻辑错误
unsupported_inference：缺少需求依据的推断
unclear_expectation：预期结果不明确
coverage_overlap：测试点覆盖重叠
missing_coverage：重要测试场景遗漏
requirement_conflict：与原始需求冲突

【输出要求】

只输出符合指定 JSON Schema 的 JSON 对象。

每个问题必须关联真实存在的 point_id。
approved_point_ids 和 review_point_ids 必须来自输入测试点。
存在问题的测试点应进入 review_point_ids。
没有问题的测试点可以进入 approved_point_ids。
不要编造测试点编号。
"""



def review_testpoints(
    requirement: RequirementAnalysis,
    testpoints: TestPointCollection,
) -> TestPointReviewResult:
    """
    调用 AI 审查测试点逻辑质量，并兼容中英文 JSON 字段。
    """

    input_data = {
        "requirement_analysis": requirement.model_dump(exclude_none=True),
        "testpoints": testpoints.model_dump(exclude_none=True),
    }

    user_prompt = json.dumps(
        input_data,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    raw_result = ai_client.chat_json(
        SYSTEM_PROMPT,
        user_prompt,
        stage="testpoint_review",
    )

    print("\n========== DeepSeek 原始审查结果 ==========")
    print(raw_result)

    data = json.loads(raw_result)

    # 1. 兼容中文和英文顶层字段
    field_mapping = {
        "审查状态": "overall_status",
        "status": "overall_status",
        "通过测试点": "approved_point_ids",
        "复核测试点": "review_point_ids",
        "问题列表": "issues",
    }

    for old_key, new_key in field_mapping.items():
        if old_key in data and new_key not in data:
            data[new_key] = data.pop(old_key)

    # 2. 兼容中文审查状态
    status_mapping = {
        "通过": "passed",
        "需复核": "needs_review",
        "需要复核": "needs_review",
        "失败": "failed",
    }

    data["overall_status"] = status_mapping.get(
        data.get("overall_status"),
        data.get("overall_status", "needs_review"),
    )

    # 3. 兼容中文问题字段
    issue_field_mapping = {
        "测试点编号": "point_id",
        "问题类型": "issue_type",
        "type": "issue_type",
        "问题描述": "description",
        "问题建议": "suggestion",
    }

    severity_map = {
        "logic_error": "critical",
        "requirement_conflict": "critical",
        "unsupported_inference": "major",
        "missing_coverage": "major",
        "unclear_expectation": "minor",
        "coverage_overlap": "minor",
    }

    issues = data.get("issues", [])

    for issue in issues:
        for old_key, new_key in issue_field_mapping.items():
            if old_key in issue and new_key not in issue:
                issue[new_key] = issue.pop(old_key)

        if "issue_type" not in issue:
            issue["issue_type"] = "unclear_expectation"

        if "severity" not in issue:
            issue["severity"] = severity_map.get(
                issue["issue_type"],
                "minor",
            )

        if "description" not in issue:
            issue["description"] = "AI 未提供具体问题描述。"

        if "suggestion" not in issue:
            issue["suggestion"] = "请人工复核该测试点。"

    # 4. 如果没有 summary，根据实际问题生成摘要
    if "summary" not in data:
        data["summary"] = (
            f"AI 审查发现 {len(issues)} 个需要复核的问题。"
            if issues
            else "AI 未发现需要复核的问题。"
        )

    # 5. 检查测试点编号是否合法
    valid_ids = {
        point.point_id
        for point in testpoints.points
    }

    approved_ids = set(data.get("approved_point_ids", []))
    review_ids = set(data.get("review_point_ids", []))

    issue_point_ids = {
        issue["point_id"]
        for issue in issues
    }

    all_returned_ids = approved_ids | review_ids | issue_point_ids

    invalid_ids = all_returned_ids - valid_ids

    if invalid_ids:
        raise ValueError(
            f"AI 审查返回了不存在的测试点编号：{sorted(invalid_ids)}"
        )

    # 6. 有问题的测试点必须进入复核列表
    approved_ids -= issue_point_ids
    review_ids |= issue_point_ids

    # 7. 检查分类完整性
    # AI 没有返回分类的测试点，不允许默认通过
    unclassified_ids = valid_ids - approved_ids - review_ids

    if unclassified_ids:
        review_ids |= unclassified_ids

    data["approved_point_ids"] = sorted(approved_ids)
    data["review_point_ids"] = sorted(review_ids)

    # 8. 根据最终结果修正整体状态
    if issues or review_ids:
        if data["overall_status"] == "passed":
            data["overall_status"] = "needs_review"

    # 9. Pydantic 结构校验
    result = TestPointReviewResult.model_validate(data)

    return result
