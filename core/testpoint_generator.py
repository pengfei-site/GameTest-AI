
import json

from core.ai_client import ai_client
from core.schemas import (
    RequirementAnalysis,
    TestPointCollection,
)
from core.testpoint_validator import validate_testpoints
from core.testpoint_reviewer import review_testpoints
from core.generation_schemas import (
    TestPointGenerationResult,
    TestPointValidationReport,
)


SYSTEM_PROMPT = """
你是一名资深游戏测试负责人，擅长将游戏需求拆解为可执行测试点。

你需要根据输入的结构化需求 JSON，生成测试点集合。

必须遵守：

1. 只能依据输入的 business_rules 生成测试点。

2. 每个测试点必须关联真实存在的 rule_id。

3. 不得自行编造 requirement_id。

4. 覆盖正向、反向、边界、异常、状态和数据测试。

5. 只针对需求中明确的规则设计确定性测试点。

6. 对 status 为 needs_confirmation 的规则：
   - 可以提出探索性测试点；
   - 必须在 coverage_description 中注明待确认；
   - 不得把未确定的预期结果写成确定结论；
   - 探索性测试点的 category 仍必须使用规定的六种类型之一。

7. open_questions 中的问题不能直接当作已确认业务规则。
   - 如果问题没有关联到 needs_confirmation 状态的业务规则，不要单独据此生成测试点。

8. 测试点标题要具体，不能使用笼统标题。

9. 优先级定义：
   - P0：核心功能阻断或重大数据风险
   - P1：核心业务功能
   - P2：一般业务场景
   - P3：低风险补充场景

10. 不同测试点不能只是换一种说法重复描述。

11. 只返回合法 JSON，不要输出 Markdown。

12. category 只能使用以下六个英文值：
    - positive、negative、boundary、exception、state、data。
    - 严禁输出 exploratory、exploration 或其他未定义类型。
    - 探索性只体现在 coverage_description 的文字说明中，不得作为 category 的值。

13. 需求追溯必须准确：
    - requirement_id 必须对应一个真实存在的 rule_id。
    - source_rule 必须与该 rule_id 对应的 rule_text 完全一致。
    - 一个测试点只能指定一个主要关联规则。
    - 如果同时覆盖其他规则，可以在 coverage_description 中注明。

14. 禁止擅自扩展需求：
    - 不得凭空假设数据库表、字段、配置表、接口、网络机制。
    - 不得凭空增加并发、重试、断线恢复等测试场景。
    - 除非原始需求明确涉及这些内容，否则不要生成相关测试点。

15. 严格处理待确认问题：
    - 不得将 open_questions 中的问题直接转化为确定的预期结果。
    - 可以生成边界探索测试点，但必须明确标注「待策划确认」。
    - 未确认的规则不得作为确定的测试通过标准。

16. 测试点去重：
    - 不同测试点必须具有不同的测试目的。
    - 相同条件、相同操作、相同预期结果的测试点应合并。
    - 不要为了增加测试点数量而拆分重复场景。

17. 测试点应优先覆盖明确的业务规则，不要为了凑齐六种测试类型而生成无依据的场景。

18. 测试点合并原则：
    - 如果两个测试点的前置条件、操作和预期结果基本相同，必须合并，不得通过改变标题或测试目的重复生成。
    - 同一业务规则的不同描述不能作为拆分测试点的理由。
    - 每个测试点必须有独立的测试价值。

19. 待确认场景的预期结果：
    - 如果某个场景涉及 open_questions 中尚未确认的规则，不得在 coverage_description 中写入确定的预期数值。
    - 例如：体力90点领取后，不能直接写预期为100点。
    - 应注明待确认，并记录实际表现。
    - 探索性测试点不作为确定的通过或失败标准。

20. 跨天场景：
    - 可以根据每日领取规则设计跨天测试。
    - 不得擅自指定每日0点或其他具体重置时间。
    - 如果重置机制没有明确，应标记待策划确认。


21. 数值计算必须准确：
    - 涉及加减乘除时，必须先进行实际计算。
    - 必须区分数值增加规则与数值上限规则。
    - 如果增加后的数值超过上限，且截断规则尚未明确，必须标记待确认，不得给出确定的最终数值。

22. 边界值设计必须符合数学逻辑：
    - 体力为80，增加20，理论值为100。
    - 体力为81，增加20，理论值为101。
    - 体力为90，增加20，理论值为110。
    - 体力为99，增加20，理论值为119。
    - 上述理论值不代表最终实际值，最终值需依据已确认的上限处理规则判断。

23. 状态测试不得擅自推断：
    - 不得将未定义的失败状态处理规则当作确定预期。
    - 不同测试点必须具有独立的测试目的。
    - 如果一个测试点已经完整覆盖另一个测试点的场景，
      应优先合并，避免重复。

24. 不得擅自补充未定义的界面交互和业务行为：
    - 不得将未定义的按钮状态、提示文案、弹窗表现写成确定的预期结果。
    - 可以将这些内容作为测试观察项，但必须标记为待确认。
    - 对于根据业务规则推导出的结论，必须区分明确规定和逻辑推导。
    - 如果原始规则只描述某个条件下允许执行操作，不得擅自推导其他条件下必然禁止操作，除非其他规则明确支持该结论。


输出结构：

{
  "module": "功能模块名称",
  "points": [
    {
      "point_id": "TP001",
      "requirement_id": "R1",
      "category": "positive",
      "title": "测试点标题",
      "test_objective": "测试目的",
      "coverage_description": "测试覆盖内容",
      "priority": "P1",
      "source_rule": "对应的业务规则原文"
    }
  ]
}
"""


def generate_testpoints(
    requirement: RequirementAnalysis
) -> TestPointGenerationResult:
    """生成测试点，由 Python 自动回填规则原文，并执行质量校验和 AI 逻辑审查。"""

    # 1. 建立原始业务规则映射
    rule_map = {
        rule.rule_id: rule.rule_text
        for rule in requirement.business_rules
    }

    if not rule_map:
        raise ValueError("当前需求没有业务规则，无法生成测试点。")

    # 2. AI 生成测试点
    requirement_json = requirement.model_dump_json(indent=2)

    raw_result = ai_client.chat_json(
        SYSTEM_PROMPT,
        requirement_json
    )

    data = json.loads(raw_result)

    if not isinstance(data, dict):
        raise ValueError("AI 返回的数据顶层必须是 JSON 对象。")

    points_data = data.get("points")

    if not isinstance(points_data, list):
        raise ValueError("AI 返回的数据中 points 必须是数组。")

    # 3. Python 检查规则 ID，并自动回填规则原文
    corrected_count = 0

    for point in points_data:
        if not isinstance(point, dict):
            raise ValueError("AI 返回的测试点必须是 JSON 对象。")

        requirement_id = point.get("requirement_id")

        if not requirement_id:
            raise ValueError(
                f"测试点 {point.get('point_id', '未知')} 缺少 requirement_id。"
            )

        if requirement_id not in rule_map:
            raise ValueError(
                f"测试点 {point.get('point_id', '未知')} "
                f"引用了不存在的需求规则：{requirement_id}"
            )

        # 由 Python 回填权威原文，不使用 AI 改写的内容
        expected_source = rule_map[requirement_id]
        ai_source = point.get("source_rule", "")

        if ai_source != expected_source:
            corrected_count += 1
            print(
                f"[规则追溯自动修正] "
                f"{point.get('point_id', '未知')} "
                f"关联规则 {requirement_id}：已自动回填原始规则。"
            )

        point["source_rule"] = expected_source

    if corrected_count:
        print(
            f"[规则追溯] 共自动修正 {corrected_count} 个测试点的规则原文。"
        )

    # 4. Pydantic 数据结构校验
    testpoints = TestPointCollection.model_validate(data)

    # 5. 再次执行严格规则追溯校验
    for point in testpoints.points:
        expected_source = rule_map[point.requirement_id]

        if point.source_rule != expected_source:
            raise ValueError(
                f"测试点 {point.point_id} 的规则追溯不一致！\n"
                f"关联规则ID：{point.requirement_id}\n"
                f"实际规则：{expected_source}\n"
                f"AI填写内容：{point.source_rule}"
            )

    # 6. 检查测试点编号是否重复
    point_ids = [
        point.point_id
        for point in testpoints.points
    ]

    if len(point_ids) != len(set(point_ids)):
        raise ValueError("AI 生成了重复的测试点编号。")

    # 7. Python 确定性质量检查
    validation_data = validate_testpoints(
        requirement,
        testpoints
    )

    validation_report = TestPointValidationReport.model_validate(
        validation_data
    )

    print("\n========== Python 质量检查报告 ==========")
    print(f"测试点总数：{validation_report.total}")
    print(f"错误数量：{validation_report.error_count}")
    print(f"警告数量：{validation_report.warning_count}")

    for error in validation_report.errors:
        print("[错误]", error)

    for warning in validation_report.warnings:
        print("[警告]", warning)

    # 8. Python 检查失败，不调用 AI Reviewer
    if not validation_report.passed:
        return TestPointGenerationResult(
            testpoints=testpoints,
            validation_report=validation_report,
            review_report={
                "overall_status": "failed",
                "summary": "Python 质量检查未通过，跳过 AI 逻辑审查。",
                "issues": [],
                "approved_point_ids": [],
                "review_point_ids": [
                    point.point_id
                    for point in testpoints.points
                ],
            },
            final_status="validation_failed",
        )

    print("Python 质量检查结果：通过")

    # 9. Python 检查通过，调用 AI Reviewer
    review_report = review_testpoints(
        requirement,
        testpoints
    )

    print("\n========== AI 逻辑审查报告 ==========")
    print(review_report.model_dump_json(indent=2))

    # 10. 汇总最终状态
    if review_report.overall_status == "failed":
        final_status = "review_failed"

    elif review_report.overall_status == "needs_review":
        final_status = "needs_manual_review"

    else:
        final_status = "ready_for_manual_review"

    # 11. 返回统一结果
    return TestPointGenerationResult(
        testpoints=testpoints,
        validation_report=validation_report,
        review_report=review_report,
        final_status=final_status,
    )