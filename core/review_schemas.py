
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TestPointIssue(BaseModel):
    """单条测试点审查问题"""

    point_id: str = Field(
        description="存在问题的测试点编号"
    )

    issue_type: Literal[
        "logic_error",
        "unsupported_inference",
        "unclear_expectation",
        "coverage_overlap",
        "missing_coverage",
        "requirement_conflict",
    ] = Field(
        description="问题类型"
    )

    severity: Literal[
        "critical",
        "major",
        "minor",
    ] = Field(
        description="问题严重程度"
    )

    description: str = Field(
        description="具体问题描述"
    )

    suggestion: str = Field(
        description="修改建议"
    )


class TestPointReviewResult(BaseModel):
    """AI 测试点审查结果"""

    overall_status: Literal[
        "passed",
        "needs_review",
        "failed",
    ] = Field(
        description="整体审查状态"
    )

    summary: str = Field(
        description="本次审查的总体结论"
    )

    issues: list[TestPointIssue] = Field(
        default_factory=list,
        description="发现的问题列表"
    )

    approved_point_ids: list[str] = Field(
        default_factory=list,
        description="审查通过的测试点编号"
    )

    review_point_ids: list[str] = Field(
        default_factory=list,
        description="需要人工复核的测试点编号"
    )


class TestCaseIssue(BaseModel):
    """单条测试用例审查问题"""

    model_config = ConfigDict(extra="forbid")

    candidate_index: int = Field(
        ge=1,
        description="存在问题的候选用例序号，从 1 开始"
    )

    issue_type: Literal[
        "logic_error",
        "unsupported_inference",
        "unclear_step",
        "unverifiable_expected_result",
        "missing_precondition",
        "requirement_conflict",
        "redundant_step",
    ] = Field(
        description="问题类型"
    )

    severity: Literal[
        "critical",
        "major",
        "minor",
    ] = Field(
        description="问题严重程度"
    )

    description: str = Field(
        min_length=1,
        description="具体问题描述"
    )

    suggestion: str = Field(
        min_length=1,
        description="修改建议"
    )


class TestCaseReviewResult(BaseModel):
    """AI 测试用例审查结果"""

    model_config = ConfigDict(extra="forbid")

    overall_status: Literal[
        "passed",
        "needs_review",
        "failed",
    ] = Field(
        description="整体审查状态"
    )

    summary: str = Field(
        min_length=1,
        description="本次审查的总体结论"
    )

    issues: list[TestCaseIssue] = Field(
        default_factory=list,
        description="发现的问题列表"
    )

    approved_candidate_indices: list[int] = Field(
        default_factory=list,
        description="审查通过的候选用例序号，从 1 开始"
    )

    review_candidate_indices: list[int] = Field(
        default_factory=list,
        description="需要人工复核的候选用例序号，从 1 开始"
    )
