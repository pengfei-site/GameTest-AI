import sys
from pathlib import Path

# 将项目根目录加入 Python 模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from core.schemas import RequirementAnalysis

test_data = {
    "module": "玩家登录",
    "summary": "验证玩家登录功能是否符合需求",
    "business_rules": [
        {
            "rule_id": "R1",
            "rule_text": "账号密码正确时允许登录",
            "source_text": "输入正确账号密码后登录成功",
            "status": "confirmed"
        },
        {
            "rule_id": "R2",
            "rule_text": "账号不存在时不允许登录",
            "source_text": "账号不存在时提示错误",
            "status": "confirmed"
        }
    ],
    "preconditions": [
        "玩家已经注册账号"
    ],
    "states": [
        "未登录",
        "已登录"
    ],
    "numeric_constraints": [
        {
            "name": "登录超时时间",
            "value": 30,
            "unit": "秒",
            "description": "登录请求超时时间"
        }
    ],
    "exception_cases": [
        "账号不存在",
        "密码错误"
    ],
    "open_questions": []
}

result = RequirementAnalysis.model_validate(
    test_data,
    strict=True
)

print("Schema 测试通过！")
print(result.model_dump_json(indent=2))
