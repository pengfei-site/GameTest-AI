
import re
from difflib import SequenceMatcher

from core.schemas import (
    RequirementAnalysis,
    TestPointCollection,
)


def normalize_text(text: str) -> str:
    """
    标准化测试点文本。
    去除数字和标点，便于识别不同数值下的相似测试场景。
    """
    text = text.lower()

    # 去除数字
    text = re.sub(r"\d+(?:\.\d+)?", "", text)

    # 去除常见标点和空白
    text = re.sub(r"[，。；：！？、（）()【】\[\]\s]", "", text)

    return text


def similarity(text_a: str, text_b: str) -> float:
    """计算两段文本的相似度"""
    a = normalize_text(text_a)
    b = normalize_text(text_b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def validate_testpoints(
    requirement: RequirementAnalysis,
    result: TestPointCollection
) -> dict:
    """
    测试点质量检查：

    1. 需求规则引用检查
    2. source_rule 原文检查
    3. 测试点编号检查
    4. 疑似重复测试点检查
    5. 参数化测试候选识别
    """

    errors = []
    warnings = []
    parameterized_candidates = []

    # 建立需求规则映射
    rule_map = {
        rule.rule_id: rule.rule_text
        for rule in requirement.business_rules
    }

    # 检查测试点编号
    point_ids = [
        point.point_id
        for point in result.points
    ]

    if len(point_ids) != len(set(point_ids)):
        errors.append("存在重复的测试点编号")

    # 检查需求规则引用和原文
    for point in result.points:

        if point.requirement_id not in rule_map:
            errors.append(
                f"{point.point_id}：引用了不存在的规则 "
                f"{point.requirement_id}"
            )
            continue

        expected_source = rule_map[point.requirement_id]

        if point.source_rule.strip() != expected_source.strip():
            errors.append(
                f"{point.point_id}：source_rule 与原始规则不一致"
            )

    # 检查测试点之间的相似度
    points = result.points

    for i in range(len(points)):
        for j in range(i + 1, len(points)):

            point_a = points[i]
            point_b = points[j]

            # 分别计算标题、目的、覆盖内容的相似度
            title_score = similarity(
                point_a.title,
                point_b.title
            )

            objective_score = similarity(
                point_a.test_objective,
                point_b.test_objective
            )

            coverage_score = similarity(
                point_a.coverage_description,
                point_b.coverage_description
            )

            average_score = (
                title_score * 0.3
                + objective_score * 0.4
                + coverage_score * 0.3
            )

            # 高度相似：疑似重复
            if average_score >= 0.85:
                warnings.append(
                    f"{point_a.point_id} 与 {point_b.point_id} "
                    f"疑似重复，相似度：{average_score:.2f}，"
                    "建议人工检查是否合并。"
                )

            # 相似度较高，但没有达到重复标准：
            # 提示可能是同一测试目的的不同数据组合
            elif average_score >= 0.60:
                parameterized_candidates.append(
                    {
                        "point_a": point_a.point_id,
                        "point_b": point_b.point_id,
                        "similarity": round(average_score, 2),
                        "reason": (
                            "测试目的可能相同，但输入条件或数值不同，"
                            "建议评估是否合并为参数化测试点。"
                        ),
                    }
                )

    return {
        "passed": len(errors) == 0,
        "total": len(points),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "parameterized_candidates": parameterized_candidates,
    }
