
import json
from unittest.mock import patch

from core.schemas import RequirementAnalysis, TestPoint
from core.testcase_generator import generate_testcases


# 使用 model_construct 构造测试输入，避免测试依赖真实需求数据
requirement = RequirementAnalysis.model_construct(
    module="玩家登录",
    summary="玩家可以通过账号和密码登录游戏",
    business_rules=[],
    preconditions=[],
    states=[],
    numeric_constraints=[],
    exception_cases=[],
    open_questions=[],
)

test_point = TestPoint.model_construct(
    point_id="TP001",
    requirement_id="R1",
    category="positive",
    title="正确账号密码登录成功",
    test_objective="验证玩家能够正常登录",
    coverage_description="验证正确账号密码的登录流程",
    priority="P1",
    source_rule="玩家可以通过正确账号密码登录",
)


# 模拟 AI 返回一条候选用例
mock_response = {
    "candidates": [
        {
            "title": "玩家正常登录",
            "objective": "验证正确账号密码能够登录游戏",
            "priority": "P1",
            "preconditions": ["玩家账号已注册"],
            "steps": [
                {
                    "step_no": 1,
                    "action": "打开登录界面",
                    "expected_result": "显示登录界面",
                },
                {
                    "step_no": 2,
                    "action": "输入正确账号密码并登录",
                    "expected_result": "成功进入游戏",
                },
            ],
            "postconditions": ["玩家处于登录状态"],
        }
    ]
}


def test_single_candidate():
    with patch(
        "core.testcase_generator.ai_client.chat_json",
        return_value=json.dumps(mock_response, ensure_ascii=False),
    ) as mock_ai:

        result = generate_testcases(requirement, test_point)

        assert result.success is True
        assert result.candidate_count == 1
        assert len(result.candidates) == 1
        assert result.candidates[0].title == "玩家正常登录"

        mock_ai.assert_called_once()

    print("单条候选用例生成：PASS")


def test_empty_candidates():
    with patch(
        "core.testcase_generator.ai_client.chat_json",
        return_value='{"candidates": []}',
    ):

        result = generate_testcases(requirement, test_point)

        assert result.success is True
        assert result.candidate_count == 0
        assert result.candidates == []

    print("零条候选用例生成：PASS")


def test_invalid_schema():
    invalid_response = {
        "candidates": [
            {
                "title": "错误用例",
                "objective": "测试",
                "priority": "P5",
                "preconditions": [],
                "steps": [
                    {
                        "step_no": 1,
                        "action": "执行操作",
                        "expected_result": "操作成功",
                    }
                ],
                "postconditions": [],
            }
        ]
    }

    from pydantic import ValidationError

    with patch(
        "core.testcase_generator.ai_client.chat_json",
        return_value=json.dumps(invalid_response),
    ):
        try:
            generate_testcases(requirement, test_point)
        except ValidationError:
            print("非法 Schema 拦截：PASS")
        else:
            raise AssertionError("非法优先级未被拦截")


if __name__ == "__main__":
    print("========== Generator Mock 测试 ==========")

    test_single_candidate()
    test_empty_candidates()
    test_invalid_schema()

    print("\n所有 Mock 测试通过！")
