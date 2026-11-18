
import json
from datetime import date, datetime
from enum import Enum

import streamlit as st

from core.time_utils import format_local_datetime
from database.repositories.project_repository import list_projects
from database.repositories.requirement_repository import (
    list_requirement_analyses,
)
from core.testpoint_generation_service import run_testpoint_generation


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="测试点生成 - GameTest AI",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 AI 测试点生成")
st.caption("选择结构化需求分析记录，调用 AI 自动生成测试点。")


# ============================================================
# 通用数据转换
# ============================================================

def to_display_data(value):
    """
    将 Pydantic、dict、list 等数据转换为 Streamlit 可展示的数据。
    不假设报告或测试点对象的具体字段结构。
    """

    if hasattr(value, "model_dump"):
        return to_display_data(value.model_dump(mode="json"))

    if isinstance(value, dict):
        return {
            str(key): to_display_data(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [to_display_data(item) for item in value]

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if value is None or isinstance(
        value,
        (str, int, float, bool),
    ):
        return value

    return str(value)


def show_json(title: str, data):
    """统一展示结构化 JSON 数据。"""

    st.subheader(title)

    display_data = to_display_data(data)

    if display_data is None:
        st.info("暂无数据")
    else:
        st.json(display_data, expanded=2)


def format_project(project: dict) -> str:
    return project.get("name", project.get("id", "未命名项目"))


def format_analysis(analysis: dict) -> str:
    module = analysis.get("module") or "未命名模块"
    summary = analysis.get("summary") or "无摘要"

    # 仅在页面展示时转换 UTC 时间，不修改原始记录
    created_at = format_local_datetime(
        analysis.get("created_at")
    )

    summary = summary.replace("\n", " ").strip()

    if len(summary) > 55:
        summary = summary[:55] + "..."

    return f"{module} | {summary} | {created_at}"


# ============================================================
# 加载项目
# ============================================================

try:
    projects = list_projects()
except Exception as exc:
    st.error(f"读取项目列表失败：{exc}")
    st.stop()


if not projects:
    st.warning("当前没有可用的游戏项目，请先创建项目。")
    st.stop()


# ============================================================
# 项目选择
# ============================================================

st.header("一、选择游戏项目")

project = st.selectbox(
    "游戏项目",
    options=projects,
    format_func=format_project,
    key="testpoint_generation_project",
)

project_id = project["id"]


# ============================================================
# 加载需求分析记录
# ============================================================

try:
    analyses = list_requirement_analyses(
        project_id=project_id,
    )
except Exception as exc:
    st.error(f"读取需求分析记录失败：{exc}")
    st.stop()


st.header("二、选择结构化需求分析")

if not analyses:
    st.warning(
        "该项目下暂无结构化需求分析记录。"
        "请先前往“结构化需求分析”页面完成需求分析。"
    )
    st.stop()


analysis = st.selectbox(
    "需求分析记录",
    options=analyses,
    format_func=format_analysis,
    key=f"testpoint_generation_analysis_{project_id}",
)

analysis_id = analysis["id"]


# ============================================================
# 展示需求依据
# ============================================================

st.header("三、确认需求分析内容")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "需求所属项目",
        project.get("name", "未知项目"),
    )

with col2:
    st.metric(
        "需求分析模块",
        analysis.get("module") or "未指定",
    )

st.markdown("**需求摘要**")
st.write(analysis.get("summary") or "暂无摘要")

with st.expander("查看完整结构化需求分析", expanded=False):
    show_json(
        "结构化需求数据",
        analysis.get("analysis_data"),
    )

st.divider()


# ============================================================
# 执行测试点生成
# ============================================================

st.header("四、执行 AI 测试点生成")

st.warning(
    "执行后将调用 AI 生成测试点，并创建新的生成批次及测试点记录。"
)

generate_clicked = st.button(
    "🚀 开始生成测试点",
    type="primary",
    use_container_width=True,
)

if generate_clicked:

    # 防止切换项目或需求后继续展示旧结果
    st.session_state.pop(
        "testpoint_generation_result",
        None,
    )

    with st.spinner(
        "AI 正在分析需求并生成测试点，请稍候……"
    ):
        try:
            result = run_testpoint_generation(
                project_id=project_id,
                requirement_analysis_id=analysis_id,
            )

            st.session_state[
                "testpoint_generation_result"
            ] = {
                "project_id": project_id,
                "requirement_analysis_id": analysis_id,
                "result": result,
            }

        except ValueError as exc:
            st.error(f"业务校验未通过：{exc}")

        except Exception as exc:
            st.error(f"测试点生成失败：{exc}")


# ============================================================
# 展示本次生成结果
# ============================================================

saved_result = st.session_state.get(
    "testpoint_generation_result"
)

if saved_result:

    # 只展示当前项目、当前需求分析对应的结果
    if (
        saved_result["project_id"] == project_id
        and saved_result["requirement_analysis_id"] == analysis_id
    ):

        result = saved_result["result"]

        st.divider()
        st.header("五、本次生成结果")

        if not result.get("success"):
            st.error("测试点生成未成功。")
            st.stop()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "AI 生成数量",
                result.get("generated_count", 0),
            )

        with col2:
            st.metric(
                "实际保存数量",
                result.get("saved_count", 0),
            )

        with col3:
            st.metric(
                "生成批次状态",
                result.get("final_status", "未知"),
            )

        st.text("生成批次 ID")
        st.code(result.get("batch_id", "未知"))

        st.success("测试点生成流程执行完成。")

        # ----------------------------------------------------
        # 质量报告
        # ----------------------------------------------------

        st.header("六、质量检查报告")

        validation_report = result.get(
            "validation_report"
        )

        review_report = result.get(
            "review_report"
        )

        tab1, tab2 = st.tabs(
            ["Python Validator", "AI Reviewer"]
        )

        with tab1:
            show_json(
                "Python 质量校验报告",
                validation_report,
            )

        with tab2:
            show_json(
                "AI Reviewer 审查报告",
                review_report,
            )

        # ----------------------------------------------------
        # 测试点结果
        # ----------------------------------------------------

        st.header("七、生成的测试点")

        created_points = result.get(
            "created_points",
            [],
        )

        st.metric(
            "本次保存的测试点",
            len(created_points),
        )

        if created_points:

            for index, point in enumerate(
                created_points,
                start=1,
            ):
                with st.expander(
                    f"测试点 {index}",
                    expanded=(index == 1),
                ):
                    st.json(
                        to_display_data(point),
                        expanded=2,
                    )

        else:
            st.info("本次没有保存测试点。")

        st.caption(
            "提示：测试点人工审核、编辑及历史记录管理"
            "将在后续测试点管理页面中实现。"
        )
