
import json

from pydantic import ValidationError

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


MAX_GENERATION_ATTEMPTS = 3


def generate_testcases(
    requirement: RequirementAnalysis,
    test_point: TestPoint,
) -> TestCaseGenerationResult:
    """
    根据需求分析和单个测试点生成 AI 测试用例候选。

    负责：
    1. 组织 AI 输入
    2. 调用 AI
    3. 解析 JSON
    4. 执行 Pydantic 结构校验
    5. 失败时有限重试
    6. 返回统一生成结果
    """

    # 使用紧凑 JSON，减少缩进、换行和空格带来的 Token 消耗。
    # 保留全部字段，不改变原始需求和测试点语义。
    requirement_json = json.dumps(
        requirement.model_dump(exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    test_point_json = json.dumps(
        test_point.model_dump(exclude_none=True),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # 基础 Prompt 只构建一次，重试时复用。
    base_user_prompt = USER_PROMPT_TEMPLATE.format(
        requirement_analysis=requirement_json,
        test_point=test_point_json,
    )

    user_prompt = base_user_prompt
    last_error = None

    for attempt in range(1, MAX_GENERATION_ATTEMPTS + 1):
        try:
            raw_result = ai_client.chat_json(
                SYSTEM_PROMPT,
                user_prompt,
                stage="testcase_generation",
            )

            data = json.loads(raw_result)

            if not isinstance(data, dict):
                raise ValueError("AI 返回结果必须是 JSON 对象")

            collection = TestCaseCandidateCollection.model_validate(
                data
            )

            return TestCaseGenerationResult(
                success=True,
                candidate_count=len(collection.candidates),
                candidates=collection.candidates,
            )

        except (ValueError, ValidationError) as exc:
            last_error = exc

            print(
                f"[TestCase Generator] 第 {attempt}/"
                f"{MAX_GENERATION_ATTEMPTS} 次生成校验失败：{exc}"
            )

            if attempt >= MAX_GENERATION_ATTEMPTS:
                break

            user_prompt = (
                base_user_prompt
                + "\n\n【上一次输出存在错误，请重新生成完整 JSON】\n"
                + f"错误信息：{str(exc)[:1500]}\n"
                + "请重新检查全部字段的数据类型和结构。"
                + "特别注意：steps 中的 action 必须是非空字符串，"
                + "不得输出整数、布尔值、对象或数组。"
                + "不要解释错误，不要修补旧 JSON，"
                + "请重新生成完整的 candidates JSON 对象。"
            )

    if last_error is not None:
        raise last_error

    raise RuntimeError("测试用例候选生成失败，但未记录具体错误。")
