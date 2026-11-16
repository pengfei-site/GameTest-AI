
import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from core.case_schemas import TestCaseCandidate
from core.schemas import RequirementAnalysis

from database.repositories import (
    test_case_candidate_repository as candidate_repo,
    test_case_generation_batch_point_repository as batch_point_repo,
    test_case_generation_batch_repository as batch_repo,
    requirement_repository as requirement_repo,
)


# =========================================================
# 1. 数据格式处理
# =========================================================

def _format_conditions(items: list[str]) -> str:
    """将前置条件或后置条件转换为多行文本。"""

    if not items:
        return ""

    return "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(items, start=1)
    )


def _format_steps(steps: list) -> tuple[str, str]:
    """分别生成测试操作和预期结果的多行文本。"""

    actions = []
    expected_results = []

    for step in steps:
        actions.append(
            f"{step.step_no}. {step.action}"
        )

        expected_results.append(
            f"{step.step_no}. {step.expected_result}"
        )

    return (
        "\n".join(actions),
        "\n".join(expected_results),
    )


def _build_requirement_basis(
    test_point_content: dict,
    requirement: RequirementAnalysis,
) -> str:
    """
    根据测试点关联的 requirement_id，
    查找对应的结构化业务规则。
    """

    requirement_id = str(
        test_point_content.get("requirement_id", "")
    ).strip()

    for rule in requirement.business_rules:

        if rule.rule_id == requirement_id:

            basis = (
                f"{rule.rule_id}：{rule.rule_text}"
            )

            if rule.source_text:
                basis += (
                    f"\n文档依据：{rule.source_text}"
                )

            if rule.status == "needs_confirmation":
                basis += "\n规则状态：待确认"

            return basis

    # 找不到结构化规则时，使用测试点保存的原始规则依据
    return str(
        test_point_content.get("source_rule", "")
    ).strip()


# =========================================================
# 2. Excel 样式
# =========================================================

def _style_worksheet(
    worksheet,
    column_widths: list[int],
):
    """统一设置工作表样式。"""

    header_fill = PatternFill(
        fill_type="solid",
        fgColor="1F4E78",
    )

    header_font = Font(
        name="微软雅黑",
        size=10,
        bold=True,
        color="FFFFFF",
    )

    content_font = Font(
        name="微软雅黑",
        size=10,
        color="333333",
    )

    thin_gray = Side(
        style="thin",
        color="D9E2F3",
    )

    cell_border = Border(
        left=thin_gray,
        right=thin_gray,
        top=thin_gray,
        bottom=thin_gray,
    )

    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )
        cell.border = cell_border

    worksheet.row_dimensions[1].height = 30

    for row in worksheet.iter_rows(min_row=2):

        line_count = 1

        for cell in row:
            cell.font = content_font
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )
            cell.border = cell_border

            if cell.value:
                line_count = max(
                    line_count,
                    str(cell.value).count("\n") + 1,
                )

        worksheet.row_dimensions[row[0].row].height = min(
            max(30, line_count * 20),
            180,
        )

    for index, width in enumerate(
        column_widths,
        start=1,
    ):
        worksheet.column_dimensions[
            get_column_letter(index)
        ].width = width

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions


# =========================================================
# 3. 创建测试用例工作表
# =========================================================

def _create_testcase_sheet(
    workbook: Workbook,
    export_items: list[dict],
):
    worksheet = workbook.active
    worksheet.title = "测试用例"

    headers = [
        "用例编号",
        "用例标题",
        "测试目的",
        "优先级",
        "前置条件",
        "测试步骤",
        "预期结果",
        "后置条件",
    ]

    worksheet.append(headers)

    for item in export_items:

        candidate = item["candidate"]

        actions, expected_results = _format_steps(
            candidate.steps
        )

        worksheet.append([
            item["export_case_id"],
            candidate.title,
            candidate.objective,
            candidate.priority,
            _format_conditions(candidate.preconditions),
            actions,
            expected_results,
            _format_conditions(candidate.postconditions),
        ])

    _style_worksheet(
        worksheet,
        [
            14,
            32,
            36,
            10,
            32,
            48,
            48,
            32,
        ],
    )

    return worksheet


# =========================================================
# 4. 创建来源追溯工作表
# =========================================================

def _create_traceability_sheet(
    workbook: Workbook,
    export_items: list[dict],
):
    worksheet = workbook.create_sheet(
        title="来源追溯"
    )

    headers = [
        "导出用例编号",
        "来源测试点编号",
        "来源测试点内容",
        "需求分析依据",
    ]

    worksheet.append(headers)

    for item in export_items:

        point_content = item["point_content"]

        point_title = str(
            point_content.get("title", "")
        ).strip()

        coverage = str(
            point_content.get("coverage_description", "")
        ).strip()

        # 同时保留测试点标题及覆盖内容
        point_description = "\n".join(
            value
            for value in [
                point_title,
                coverage,
            ]
            if value
        )

        worksheet.append([
            item["export_case_id"],
            item["point_id"],
            point_description,
            item["requirement_basis"],
        ])

    _style_worksheet(
        worksheet,
        [
            18,
            20,
            55,
            65,
        ],
    )

    return worksheet


# =========================================================
# 5. 收集导出数据
# =========================================================

def _collect_export_items(
    batch_id: str,
) -> list[dict]:
    """收集已审核通过的候选用例及其来源数据。"""

    batch = batch_repo.get_generation_batch(
        batch_id
    )

    if batch is None:
        raise ValueError("测试用例生成批次不存在")

    requirement_record = (
        requirement_repo.get_requirement_analysis(
            batch["requirement_analysis_id"]
        )
    )

    if requirement_record is None:
        raise ValueError("需求分析记录不存在")

    requirement = RequirementAnalysis.model_validate(
        requirement_record["analysis_data"]
    )

    candidates = candidate_repo.list_candidates_by_batch(
        batch_id
    )

    approved_candidates = [
        candidate
        for candidate in candidates
        if candidate["manual_review_status"] == "approved"
    ]

    if not approved_candidates:
        raise ValueError(
            "当前生成批次没有人工审核通过的候选用例，无法导出"
        )

    export_items = []

    for candidate_record in approved_candidates:

        point_record = batch_point_repo.get_batch_point_by_id(
            candidate_record["batch_point_id"]
        )

        if point_record is None:
            raise ValueError(
                f"候选用例 {candidate_record['id']} 对应的测试点快照不存在"
            )

        point_content = point_record["point_content"]

        if not isinstance(point_content, dict):
            raise ValueError("测试点快照内容格式错误")

        # 确保候选关联的批次与快照批次一致
        if point_record["batch_id"] != batch_id:
            raise ValueError("测试点快照不属于当前导出批次")

        if point_record["point_id"] != point_content.get("point_id"):
            raise ValueError("测试点快照编号与内容不一致")

        candidate = TestCaseCandidate.model_validate(
            candidate_record["current_content"]
        )

        export_items.append({
            "candidate_id": candidate_record["id"],
            "export_case_id": "",
            "candidate": candidate,
            "point_id": point_record["point_id"],
            "point_content": point_content,
            "requirement_basis": _build_requirement_basis(
                point_content,
                requirement,
            ),
        })

    # 按本次导出顺序生成临时编号
    for index, item in enumerate(
        export_items,
        start=1,
    ):
        item["export_case_id"] = (
            f"TC{index:03d}"
        )

    return export_items


# =========================================================
# 6. 对外导出接口
# =========================================================

def export_approved_testcases(
    batch_id: str,
    output_path: str,
) -> dict:
    """
    导出指定生成批次中人工审核通过的候选用例。

    Args:
        batch_id: 测试用例生成批次 ID
        output_path: Excel 文件保存路径

    Returns:
        {
            "success": True,
            "batch_id": "...",
            "exported_count": 2,
            "output_path": "..."
        }
    """

    if not batch_id or not batch_id.strip():
        raise ValueError("batch_id 不能为空")

    if not output_path or not output_path.strip():
        raise ValueError("output_path 不能为空")

    output_file = Path(output_path)

    if output_file.suffix.lower() != ".xlsx":
        raise ValueError("导出文件必须使用 .xlsx 格式")

    # 收集已审核通过的候选及来源追溯数据
    export_items = _collect_export_items(
        batch_id
    )

    # 创建工作簿
    workbook = Workbook()

    # Sheet 1：测试用例
    _create_testcase_sheet(
        workbook,
        export_items,
    )

    # Sheet 2：来源追溯
    _create_traceability_sheet(
        workbook,
        export_items,
    )

    # 创建输出目录
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 保存文件
    workbook.save(output_file)
    workbook.close()

    return {
        "success": True,
        "batch_id": batch_id,
        "exported_count": len(export_items),
        "output_path": str(output_file.resolve()),
    }
