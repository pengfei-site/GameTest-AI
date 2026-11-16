
import json

from core.ai_client import ai_client
from core.schemas import RequirementAnalysis, TestPoint
from core.case_schemas import (
    TestCaseCandidateCollection,
    TestCaseGenerationResult,
)
from core.testcase_generation_prompt import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)


def generate_testcases(
    requirement: RequirementAnalysis,
    test_point: TestPoint,
) -> TestCaseGenerationResult:
    """
    根据需求分析和单个测试点生成 AI 测试用例候选。

    本函数只负责：
    1. 组织 AI 输入
    2. 调用 AI
    3. 解析 JSON
    4. 执行 Pydantic 结构校验
    5. 返回统一生成结果

    不负责：
    - 测试点人工审核状态检查
    - Python 测试用例质量校验
    - AI Reviewer 审查
    - 数据库持久化
    """

    # 1. 序列化需求分析
    requirement_json = requirement.model_dump_json(
        indent=2
    )

    # 2. 序列化当前测试点
    test_point_json = test_point.model_dump_json(
        indent=2
    )

    # 3. 组织用户 Prompt
    user_prompt = USER_PROMPT_TEMPLATE.format(
        requirement_analysis=requirement_json,
        test_point=test_point_json,
    )

    # 4. 调用 AI 生成 JSON
    raw_result = ai_client.chat_json(
        SYSTEM_PROMPT,
        user_prompt,
    )

    # 5. 解析 JSON
    data = json.loads(raw_result)

    # 6. Pydantic 结构校验
    collection = TestCaseCandidateCollection.model_validate(
        data
    )

    # 7. 组装统一生成结果
    result = TestCaseGenerationResult(
        success=True,
        candidate_count=len(collection.candidates),
        candidates=collection.candidates,
    )

    return result
