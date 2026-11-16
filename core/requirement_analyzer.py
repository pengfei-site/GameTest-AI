
from core.ai_client import ai_client
from core.schemas import RequirementAnalysis


SYSTEM_PROMPT = """
你是一名拥有多年经验的资深游戏测试工程师。

你的任务是分析游戏策划需求，并输出结构化 JSON。

必须遵守以下规则：

1. 只能依据用户提供的原始需求提取业务规则。
2. 不得将经验推测当作已经确认的需求。
3. 无法确定的规则必须放入 open_questions。
4. business_rules 中：
   - 明确写出的规则，status 为 confirmed。
   - 存在歧义或缺少依据的规则，status 为 needs_confirmation。
5. source_text 尽量引用对应的原始需求内容。
6. 数值限制必须准确提取，不得擅自修改。
7. 没有相关内容的数组返回空数组。
8. 只返回 JSON，不要输出 Markdown、解释或代码围栏。

必须按照下面的 JSON 结构输出：

{
  "module": "功能模块名称",
  "summary": "需求摘要",
  "business_rules": [
    {
      "rule_id": "R1",
      "rule_text": "规则描述",
      "source_text": "原始需求依据",
      "status": "confirmed"
    }
  ],
  "preconditions": [],
  "states": [],
  "numeric_constraints": [],
  "exception_cases": [],
  "open_questions": []
}

请确保返回的是合法 JSON。
"""


def analyze_requirement(requirement_text: str) -> RequirementAnalysis:
    """分析游戏需求并验证结构"""

    if not requirement_text or not requirement_text.strip():
        raise ValueError("需求内容不能为空")

    raw_result = ai_client.chat_json(
        SYSTEM_PROMPT,
        requirement_text
    )

    print("\n========== AI 原始 JSON ==========\n")
    print(raw_result)

    # 使用 Pydantic 验证 AI 返回的数据结构
    result = RequirementAnalysis.model_validate_json(
        raw_result
    )

    return result
