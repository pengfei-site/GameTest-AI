
from pydantic import ValidationError

from core.ai_client import ai_client
from core.schemas import RequirementAnalysis


SYSTEM_PROMPT = """
你是一名拥有多年经验的资深游戏测试工程师。

你的任务是分析游戏策划需求，并输出结构化 JSON。

一、基本分析规则

1. 只能依据用户提供的原始需求提取业务规则。
2. 不得将经验推测当作已经确认的需求。
3. 无法确定的规则必须放入 open_questions。
4. 明确写出的业务规则，status 为 confirmed。
5. 存在歧义或缺少依据的规则，status 为 needs_confirmation。
6. source_text 尽量引用对应的原始需求内容。
7. 数值限制必须准确提取，不得擅自修改。
8. 没有相关内容的数组返回空数组。
9. 不要为了填充数据而编造需求。
10. 不确定的内容必须明确标记，不得自行补全。

二、JSON 字段定义

1. module
类型：字符串
说明：游戏功能模块名称。

2. summary
类型：字符串
说明：需求整体摘要。

3. business_rules
类型：对象数组。

每个对象必须包含：

{
    "rule_id": "R1",
    "rule_text": "业务规则描述",
    "source_text": "原始需求依据",
    "status": "confirmed"
}

status 只能是：
confirmed
needs_confirmation

4. preconditions
类型：字符串数组。
说明：功能执行所需要的前置条件。

5. states
类型：字符串数组。
说明：功能涉及的状态，例如未登录、已登录。

6. numeric_constraints
类型：对象数组。

每个对象必须包含：

{
    "name": "约束名称",
    "value": 10,
    "unit": "秒",
    "description": "约束说明"
}

字段要求：

name：字符串。
value：字符串、整数或浮点数。
unit：字符串，没有单位时填写空字符串。
description：字符串，没有说明时填写空字符串。

7. exception_cases
类型：字符串数组。
说明：异常情况及异常处理规则。

8. open_questions
类型：字符串数组。
说明：需求中存在歧义、缺失或需要策划确认的问题。

三、输出要求

1. 只能返回一个合法 JSON 对象。
2. 不允许输出 Markdown。
3. 不允许使用代码围栏。
4. 不允许在 JSON 前后添加解释。
5. 不允许添加 Schema 未定义的字段。
6. 所有字段类型必须正确。
7. 对象数组中的每个对象必须包含规定字段。
8. 没有数据的数组必须返回 []。
9. 所有字符串必须符合 JSON 转义规范。
10. 不允许在 JSON 中使用注释。

四、必须遵循的 JSON 结构

{
    "module": "功能模块名称",
    "summary": "需求整体摘要",
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
    "numeric_constraints": [
        {
            "name": "数值约束名称",
            "value": 10,
            "unit": "秒",
            "description": "约束说明"
        }
    ],
    "exception_cases": [],
    "open_questions": []
}

注意：
以上示例仅用于说明数据结构。
必须根据用户提供的真实需求填写内容。
不能直接照抄示例中的业务数据。
"""


def analyze_requirement(
    requirement_text: str
) -> RequirementAnalysis:
    """
    分析游戏需求并验证结构。

    参数：
        requirement_text: 原始游戏策划需求

    返回：
        RequirementAnalysis: 经过 Pydantic 验证的需求分析结果
    """

    # 1. 检查输入
    if not isinstance(requirement_text, str):
        raise TypeError("需求内容必须是字符串")

    if not requirement_text.strip():
        raise ValueError("需求内容不能为空")

    # 2. 调用 AI
    raw_result = ai_client.chat_json(
        SYSTEM_PROMPT,
        requirement_text.strip(),
        stage="requirement_analysis",
    )

    # 3. 检查返回结果
    if not raw_result:
        raise ValueError("AI 返回结果为空")

    print("\n========== AI 原始 JSON ==========")
    print(raw_result)
    print("========== AI 原始 JSON 结束 ==========\n")

    # 4. Pydantic 数据校验
    try:
        result = RequirementAnalysis.model_validate_json(
            raw_result,
            strict=True
        )

    except ValidationError as e:

        print("\n========== 需求分析 Schema 校验失败 ==========")

        for error in e.errors():
            field_path = ".".join(
                str(item) for item in error["loc"]
            )

            print(f"字段位置：{field_path}")
            print(f"错误类型：{error['type']}")
            print(f"错误原因：{error['msg']}")
            print("----------------------------------------")

        print("============================================\n")

        raise ValueError(
            "AI 返回的需求分析数据不符合项目 Schema。\n"
            "详细错误：\n"
            + str(e)
        ) from e

    except Exception as e:
        raise RuntimeError(
            f"需求分析结果验证过程中发生异常：{str(e)}"
        ) from e

    # 5. 输出验证成功信息
    print("========== 需求分析成功 ==========")
    print("功能模块：", result.module)
    print("业务规则数量：", len(result.business_rules))
    print("前置条件数量：", len(result.preconditions))
    print("状态数量：", len(result.states))
    print("数值约束数量：", len(result.numeric_constraints))
    print("异常情况数量：", len(result.exception_cases))
    print("待确认问题数量：", len(result.open_questions))
    print("==================================")

    return result
