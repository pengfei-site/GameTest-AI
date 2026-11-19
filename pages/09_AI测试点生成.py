
import json
from datetime import date, datetime
from enum import Enum

import streamlit as st

from components.header import render_header
from core.time_utils import format_local_datetime
from database.repositories.project_repository import list_projects
from database.repositories.requirement_repository import list_requirement_analyses
from core.testpoint_generation_service import run_testpoint_generation


# ============================================================
# 页面专属样式
# ============================================================

st.html("""
<style>
.tp-page-intro {
    padding: 18px 22px;
    border: 1px solid #e8e5f5;
    border-radius: 14px;
    background: linear-gradient(120deg, #f7f6ff 0%, #fbfaff 100%);
    margin-bottom: 20px;
}

.tp-step-label {
    color: #6254c7;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 5px;
}

.tp-section-note {
    color: #77758a;
    font-size: 13px;
    margin-top: -8px;
    margin-bottom: 16px;
}

.tp-info-card {
    padding: 14px 16px;
    border: 1px solid #ebe9f3;
    border-radius: 12px;
    background: #ffffff;
    min-height: 88px;
}

.tp-info-label {
    color: #858296;
    font-size: 12px;
    margin-bottom: 7px;
}

.tp-info-value {
    color: #302d43;
    font-size: 15px;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.tp-result-card {
    padding: 16px;
    border: 1px solid #ebe9f3;
    border-radius: 12px;
    background: #ffffff;
    min-height: 105px;
}

.tp-result-label {
    color: #858296;
    font-size: 12px;
    margin-bottom: 8px;
}

.tp-result-value {
    color: #302d43;
    font-size: 25px;
    font-weight: 700;
    line-height: 1.3;
    overflow-wrap: anywhere;
}

.tp-result-hint {
    color: #858296;
    font-size: 12px;
    margin-top: 5px;
}

.tp-action-note {
    padding: 15px 18px;
    border-left: 4px solid #8275d5;
    border-radius: 8px;
    background: #f7f6fc;
    color: #514d68;
    line-height: 1.7;
}

@media (max-width: 768px) {
    .tp-page-intro {
        padding: 14px 16px;
    }

    .tp-result-card {
        min-height: 85px;
    }
}
</style>
""")


# ============================================================
# 页面 Header
# ============================================================

render_header(
    title="AI 测试点生成",
    description="基于结构化需求分析结果，自动生成游戏测试点，并提供质量校验和 AI 审核报告。",
    breadcrumb=["测试点中心", "AI 测试点生成"],
)


# ============================================================
# 数据展示辅助函数
# ============================================================

def to_display_data(value):
    """
    将 Pydantic、Enum、日期时间等对象转换为可展示的数据。
    保留原有生成结果的数据结构。
    """
    if hasattr(value, "model_dump"):
        return to_display_data(value.model_dump(mode="json"))

    if isinstance(value, dict):
        return {
            str(key): to_display_data(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            to_display_data(item)
            for item in value
        ]

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def show_json(title, data):
    st.subheader(title)

    display_data = to_display_data(data)

    if display_data is None:
        st.info("暂无数据")
    else:
        st.json(display_data, expanded=True)


def format_project(project):
    name = (
        project.get("project_name")
        or project.get("name")
        or "未命名项目"
    )

    return f"{name}（{project.get('id', '')}）"


def format_analysis(analysis):
    module = analysis.get("module") or "未命名模块"
    summary = analysis.get("summary") or ""

    if len(summary) > 45:
        summary = summary[:45] + "..."

    return (
        f"{module} | {summary} | "
        f"分析 ID：{analysis.get('id', '')}"
    )


def render_info_card(label, value):
    st.html(f"""
    <div class="tp-info-card">
        <div class="tp-info-label">{label}</div>
        <div class="tp-info-value">{value}</div>
    </div>
    """)


def render_result_card(label, value, hint=""):
    st.html(f"""
    <div class="tp-result-card">
        <div class="tp-result-label">{label}</div>
        <div class="tp-result-value">{value}</div>
        <div class="tp-result-hint">{hint}</div>
    </div>
    """)


# ============================================================
# Session State 初始化
# 保留原有状态键，避免影响已有页面逻辑
# ============================================================

if "testpoint_generation_result" not in st.session_state:
    st.session_state["testpoint_generation_result"] = None


# ============================================================
# 页面说明
# ============================================================

st.html("""
<div class="tp-page-intro">
    <div class="tp-step-label">AI TEST POINT GENERATION</div>
    <div style="font-size:17px;font-weight:700;color:#302d43;margin-bottom:6px;">
        从结构化需求到游戏测试点
    </div>
    <div style="font-size:13px;color:#77758a;line-height:1.7;">
        选择项目及已保存的结构化需求分析，启动 AI 测试点生成流程。
        生成完成后，可查看生成统计、质量校验报告和测试点详情。
    </div>
</div>
""")


# ============================================================
# 1. 项目选择
# ============================================================

st.subheader("第一步：选择项目")
st.caption("选择需要生成测试点的游戏项目。")

try:
    projects = list_projects()

except Exception as exc:
    st.error(f"读取项目列表失败：{exc}")
    st.stop()

if not projects:
    st.warning("当前没有可用项目，请先创建项目。")
    st.stop()


project_options = {
    project["id"]: project
    for project in projects
}

project_id = st.selectbox(
    "选择项目",
    options=list(project_options.keys()),
    format_func=lambda value: format_project(
        project_options[value]
    ),
    key="testpoint_generation_project",
)


# ============================================================
# 2. 需求分析选择
# ============================================================

st.divider()

st.subheader("第二步：选择结构化需求分析")
st.caption("测试点将基于选中的需求分析结果生成。")

try:
    analyses = list_requirement_analyses(
        project_id=project_id
    )

except Exception as exc:
    st.error(f"读取结构化需求分析失败：{exc}")
    st.stop()

if not analyses:
    st.warning(
        "当前项目暂无结构化需求分析结果。"
        "请先前往「结构化需求分析」页面完成需求分析并保存。"
    )
    st.stop()


analysis_options = {
    analysis["id"]: analysis
    for analysis in analyses
}

analysis_id = st.selectbox(
    "选择需求分析",
    options=list(analysis_options.keys()),
    format_func=lambda value: format_analysis(
        analysis_options[value]
    ),
    key=f"testpoint_generation_analysis_{project_id}",
)


selected_analysis = analysis_options[analysis_id]


# ============================================================
# 3. 需求分析内容预览
# ============================================================

st.divider()

st.subheader("需求分析内容")
st.caption("生成前请确认当前选择的项目和需求分析内容。")

with st.container(border=True):
    analysis_col1, analysis_col2 = st.columns(2)

    with analysis_col1:
        render_info_card(
            "所属项目",
            format_project(project_options[project_id]),
        )

        st.write("")
        render_info_card(
            "需求模块",
            selected_analysis.get("module") or "未填写",
        )

    with analysis_col2:
        render_info_card(
            "需求分析 ID",
            str(analysis_id),
        )

        st.write("")
        render_info_card(
            "创建时间",
            str(
                format_local_datetime(
                    selected_analysis.get("created_at")
                )
            ),
        )

    st.markdown("**需求摘要**")

    st.write(
        selected_analysis.get("summary") or "暂无需求摘要"
    )


analysis_data = selected_analysis.get("analysis_data")

if isinstance(analysis_data, str):
    try:
        analysis_data = json.loads(analysis_data)
    except (json.JSONDecodeError, TypeError):
        pass


with st.expander("查看完整结构化需求数据", expanded=False):
    show_json(
        "结构化需求数据",
        analysis_data,
    )


# ============================================================
# 4. 执行 AI 测试点生成
# ============================================================

st.divider()

st.subheader("第三步：生成测试点")
st.caption("确认需求内容无误后，启动 AI 测试点生成流程。")

with st.container(border=True):
    st.markdown("**本次生成任务**")

    task_col1, task_col2 = st.columns(2)

    with task_col1:
        render_info_card(
            "目标项目",
            format_project(project_options[project_id]),
        )

    with task_col2:
        render_info_card(
            "需求模块",
            selected_analysis.get("module") or "未填写",
        )

    st.write("")

    st.info(
        "生成操作将基于当前选择的项目和需求分析执行。"
        "请确认需求内容无误后，再点击生成按钮。"
    )


# 判断已有结果是否属于当前项目和需求分析
previous_result = st.session_state.get(
    "testpoint_generation_result"
)

if previous_result:
    result_matches = (
        previous_result.get("project_id") == project_id
        and previous_result.get("requirement_analysis_id") == analysis_id
    )

    if not result_matches:
        st.caption(
            "当前选择与上一次生成结果不同。"
            "点击生成后将展示当前需求对应的新结果。"
        )


if st.button(
    "开始生成测试点",
    type="primary",
    width="stretch",
    key="run_testpoint_generation_button",
):

    try:
        with st.spinner(
            "AI 正在分析需求并生成测试点，请稍候..."
        ):
            result = run_testpoint_generation(
                project_id=project_id,
                requirement_analysis_id=analysis_id,
            )

        st.session_state["testpoint_generation_result"] = {
            "project_id": project_id,
            "requirement_analysis_id": analysis_id,
            "result": result,
        }

        st.success("测试点生成流程已执行完成。")
        st.rerun()

    except Exception as exc:
        st.error(f"AI 测试点生成失败：{exc}")


# ============================================================
# 5. 生成结果展示
# ============================================================

st.divider()

st.subheader("生成结果")

generation_state = st.session_state.get(
    "testpoint_generation_result"
)

if not generation_state:
    st.info(
        "当前还没有生成结果。"
        "请选择需求分析并点击「开始生成测试点」。"
    )
    st.stop()


# 只展示与当前项目、需求分析匹配的结果
if (
    generation_state.get("project_id") != project_id
    or generation_state.get("requirement_analysis_id") != analysis_id
):
    st.info(
        "当前选择的项目或需求分析与上一次生成结果不同，"
        "请点击「开始生成测试点」生成对应结果。"
    )
    st.stop()


result = generation_state.get("result")

if result is None:
    st.warning("没有可展示的生成结果。")
    st.stop()


result_data = to_display_data(result)

if not isinstance(result_data, dict):
    st.error("生成结果格式异常，无法展示结构化数据。")
    st.stop()


# ------------------------------------------------------------
# 生成统计
# ------------------------------------------------------------

generated_count = result_data.get("generated_count", 0)
saved_count = result_data.get("saved_count", 0)
final_status = result_data.get("final_status", "unknown")
batch_id = result_data.get("batch_id")


metric_col1, metric_col2, metric_col3 = st.columns(3)

with metric_col1:
    render_result_card(
        "生成测试点数量",
        str(generated_count),
        "本次生成返回的测试点数量",
    )

with metric_col2:
    render_result_card(
        "成功保存数量",
        str(saved_count),
        "成功写入的测试点数量",
    )

with metric_col3:
    render_result_card(
        "最终状态",
        str(final_status),
        "本次生成流程状态",
    )


if batch_id:
    st.write("")
    render_info_card(
        "生成批次 ID",
        str(batch_id),
    )


# ------------------------------------------------------------
# 质量报告
# ------------------------------------------------------------

st.divider()

st.subheader("质量检查报告")
st.caption("查看 Python Validator 校验结果和 AI Reviewer 审核结果。")

validation_report = result_data.get("validation_report")
review_report = result_data.get("review_report")

report_tab1, report_tab2 = st.tabs(
    ["Python Validator", "AI Reviewer"]
)

with report_tab1:
    if validation_report is not None:
        show_json(
            "Python Validator 校验报告",
            validation_report,
        )
    else:
        st.info("当前结果没有 Python Validator 报告。")


with report_tab2:
    if review_report is not None:
        show_json(
            "AI Reviewer 审核报告",
            review_report,
        )
    else:
        st.info("当前结果没有 AI Reviewer 报告。")


# ------------------------------------------------------------
# 创建的测试点
# ------------------------------------------------------------

st.divider()

st.subheader("本次生成的测试点")

created_points = result_data.get("created_points")

if created_points:
    st.caption(
        f"本次生成结果包含 {len(created_points)} 条测试点记录。"
    )

    for index, point in enumerate(created_points, start=1):
        point_data = to_display_data(point)

        if isinstance(point_data, dict):
            point_title = (
                point_data.get("title")
                or point_data.get("point_id")
                or f"测试点 {index}"
            )
        else:
            point_title = f"测试点 {index}"

        with st.expander(
            f"{index}. {point_title}",
            expanded=False,
        ):
            st.json(
                point_data,
                expanded=True,
            )

else:
    st.info("当前生成结果没有返回 created_points 数据。")


# ============================================================
# 6. 后续操作提示
# ============================================================

st.divider()

st.html("""
<div class="tp-action-note">
    <strong>下一步可以做什么？</strong><br>
    生成完成后，可以前往「测试点列表」查看测试点详情，
    进行人工编辑、单条审核和批量审核；
    也可以前往「测试点批次管理」查看批次详情、质量报告和操作历史。
</div>
""")
