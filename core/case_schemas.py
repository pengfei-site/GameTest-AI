
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TestCaseStep(BaseModel):
    """测试用例中的单个执行步骤。"""

    model_config = ConfigDict(extra="forbid")

    step_no: int = Field(ge=1, description="步骤序号")
    action: str = Field(min_length=1, description="测试操作")
    expected_result: str = Field(
        min_length=1,
        description="该步骤对应的预期结果",
    )


class TestCaseCandidate(BaseModel):
    """AI 生成的一条测试用例候选。"""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, description="测试用例标题")
    objective: str = Field(min_length=1, description="测试目的")
    priority: Literal["P0", "P1", "P2", "P3"] = Field(
        description="测试优先级"
    )

    preconditions: list[str] = Field(
        default_factory=list,
        description="测试前置条件",
    )

    steps: list[TestCaseStep] = Field(
        min_length=1,
        description="测试步骤",
    )

    postconditions: list[str] = Field(
        default_factory=list,
        description="测试结束后的状态",
    )


class TestCaseCandidateCollection(BaseModel):
    """一个测试点对应的候选用例集合。"""

    model_config = ConfigDict(extra="forbid")

    candidates: list[TestCaseCandidate] = Field(
        default_factory=list,
        description="生成的候选用例，允许为空",
    )


class TestCaseGenerationResult(BaseModel):
    """测试用例生成结果。"""

    model_config = ConfigDict(extra="forbid")

    success: bool
    candidate_count: int = Field(ge=0)
    candidates: list[TestCaseCandidate] = Field(
        default_factory=list
    )
    error_message: str | None = None


class TestCaseValidationReport(BaseModel):
    """Python 测试用例质量检查报告。"""

    model_config = ConfigDict(extra="forbid")

    passed: bool = Field(
        description="是否通过校验，即是否不存在错误",
    )

    total: int = Field(
        ge=0,
        description="本次校验的候选用例总数",
    )

    error_count: int = Field(
        ge=0,
        description="错误数量",
    )

    warning_count: int = Field(
        ge=0,
        description="警告数量",
    )

    errors: list[str] = Field(
        default_factory=list,
        description="错误信息",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="警告信息",
    )
