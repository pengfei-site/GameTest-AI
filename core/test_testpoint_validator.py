
from core.schemas import (
    BusinessRule,
    RequirementAnalysis,
    TestPoint,
    TestPointCollection,
)
from core.testpoint_validator import validate_testpoints


requirement = RequirementAnalysis(
    module="每日体力领取",
    summary="每日免费领取体力",
    business_rules=[
        BusinessRule(
            rule_id="R1",
            rule_text="玩家每天可以免费领取一次体力。",
            source_text="玩家每天可以免费领取一次体力。",
            status="confirmed",
        )
    ],
)

result = TestPointCollection(
    module="每日体力领取",
    points=[
        TestPoint(
            point_id="TP001",
            requirement_id="R1",
            category="positive",
            title="当天首次领取体力成功",
            test_objective="验证当天首次领取体力能够成功",
            coverage_description="当天未领取，当前体力不足100点",
            priority="P1",
            source_rule="玩家每天可以免费领取一次体力。",
        ),
        TestPoint(
            point_id="TP002",
            requirement_id="R1",
            category="positive",
            title="当天首次领取体力成功",
            test_objective="验证当天首次领取体力能够成功",
            coverage_description="当天未领取，当前体力不足100点",
            priority="P1",
            source_rule="玩家每天可以免费领取一次体力。",
        ),
    ],
)

report = validate_testpoints(requirement, result)

print("========== 测试点质量检查 ==========")
print(f"测试点总数：{report['total']}")
print(f"错误数量：{report['error_count']}")
print(f"警告数量：{report['warning_count']}")
print(f"是否通过：{report['passed']}")

for error in report["errors"]:
    print("[错误]", error)

for warning in report["warnings"]:
    print("[警告]", warning)

assert report["passed"] is True
assert report["warning_count"] == 1

print("\n========== 测试通过 ==========")
