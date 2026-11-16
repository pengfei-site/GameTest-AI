
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TestPoint(BaseModel):
    """单条测试点"""

    point_id: str = Field(
        description="测试点编号，例如 TP001"
    )

    requirement_id: str = Field(
        description="关联的需求规则编号，例如 R1"
    )

    category: Literal[
        "positive",
        "negative",
        "boundary",
        "exception",
        "state",
        "data"
    ] = Field(
        description="测试点类型"
    )

    title: str = Field(
        description="测试点标题"
    )

    test_objective: str = Field(
        description="测试目的"
    )

    coverage_description: str = Field(
        description="具体测试覆盖内容"
    )

    priority: Literal[
        "P0",
        "P1",
        "P2",
        "P3"
    ] = Field(
        description="测试优先级"
    )

    source_rule: str = Field(
        description="对应的原始业务规则"
    )


class TestPointEditableContent(BaseModel):
    """人工编辑测试点时允许修改的内容"""

    model_config = ConfigDict(
        extra="forbid"
    )

    requirement_id: str = Field(
        description="关联的需求规则编号，例如 R1"
    )

    category: Literal[
        "positive",
        "negative",
        "boundary",
        "exception",
        "state",
        "data"
    ] = Field(
        description="测试点类型"
    )

    title: str = Field(
        description="测试点标题"
    )

    test_objective: str = Field(
        description="测试目的"
    )

    coverage_description: str = Field(
        description="具体测试覆盖内容"
    )

    priority: Literal[
        "P0",
        "P1",
        "P2",
        "P3"
    ] = Field(
        description="测试优先级"
    )

    source_rule: str = Field(
        description="对应的原始业务规则"
    )

    @field_validator(
        "requirement_id",
        "title",
        "test_objective",
        "coverage_description",
        "source_rule"
    )
    @classmethod
    def validate_not_empty(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("该字段不能为空")

        return value


class TestPointCollection(BaseModel):
    """测试点集合"""

    module: str = Field(
        description="所属功能模块"
    )

    points: list[TestPoint] = Field(
        default_factory=list,
        description="测试点列表"
    )


class BusinessRule(BaseModel):
    """单条业务规则"""

    rule_id: str = Field(
        description="规则编号，例如 R1"
    )

    rule_text: str = Field(
        description="业务规则描述"
    )

    source_text: str = Field(
        description="原始策划文档中的依据"
    )

    status: Literal[
        "confirmed",
        "needs_confirmation"
    ] = Field(
        description="规则确认状态"
    )


class NumericConstraint(BaseModel):
    """结构化数值约束"""

    name: str
    value: str | int | float
    unit: str = ""
    description: str = ""


class RequirementAnalysis(BaseModel):
    """游戏需求结构化分析结果"""

    module: str = Field(
        description="所属游戏功能模块"
    )

    summary: str = Field(
        description="需求整体摘要"
    )

    business_rules: list[BusinessRule] = Field(
        default_factory=list
    )

    preconditions: list[str] = Field(
        default_factory=list
    )

    states: list[str] = Field(
        default_factory=list
    )

    numeric_constraints: list[NumericConstraint] = Field(
        default_factory=list
    )

    exception_cases: list[str] = Field(
        default_factory=list
    )

    open_questions: list[str] = Field(
        default_factory=list
    )
