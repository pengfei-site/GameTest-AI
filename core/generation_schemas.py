
from typing import Literal

from pydantic import BaseModel, Field

from core.schemas import TestPointCollection
from core.review_schemas import TestPointReviewResult


class ParameterizedCandidate(BaseModel):
    """疑似可合并为参数化测试的测试点组合"""

    point_a: str
    point_b: str
    similarity: float
    reason: str


class TestPointValidationReport(BaseModel):
    """Python 测试点质量检查报告"""

    passed: bool
    total: int
    error_count: int
    warning_count: int
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    parameterized_candidates: list[ParameterizedCandidate] = Field(
        default_factory=list
    )


class TestPointGenerationResult(BaseModel):
    """测试点生成与质量审查的统一结果"""

    testpoints: TestPointCollection

    validation_report: TestPointValidationReport

    review_report: TestPointReviewResult

    final_status: Literal[
        "ready_for_manual_review",
        "needs_manual_review",
        "review_failed",
        "validation_failed",
    ]
