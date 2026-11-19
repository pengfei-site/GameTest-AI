
import html
import streamlit as st

from components.header import render_header

from database.repositories.project_repository import list_projects
from database.repositories.requirement_repository import (
    list_requirement_analyses,
)
from database.repositories.generation_batch_repository import (
    list_generation_batches as list_test_point_generation_batches,
)
from database.repositories.test_point_repository import list_test_points


# ============================================================
# 页面专属样式
# ============================================================

st.html("""
<style>
.tc-generation-intro {
    padding: 20px 22px;
    margin: 8px 0 22px 0;
    border: 1px solid #e7e3fa;
    border-radius: 14px;
    background: linear-gradient(120deg, #f5f3ff 0%, #faf9ff 100%);
}

.tc-generation-intro-title {
    color: #40358f;
    font-size: 19px;
    font-weight: 700;
    margin-bottom: 7px;
}

.tc-generation-intro-text {
    color: #66627d;
    font-size: 14px;
    line-height: 1.7;
}

.tc-stat-card {
    padding: 15px 17px;
    border: 1px solid #e9e7f1;
    border-radius: 12px;
    background: #ffffff;
    min-height: 92px;
}

.tc-stat-label {
    color: #77738b;
    font-size: 13px;
    margin-bottom: 8px;
}

.tc-stat-value {
    color: #302b49;
    font-size: 25px;
    font-weight: 700;
    line-height: 1.2;
    overflow-wrap: anywhere;
}

.tc-info-card {
    padding: 14px 16px;
    border: 1px solid #e9e7f1;
    border-radius: 12px;
    background: #ffffff;
    margin-bottom: 10px;
}

.tc-info-label {
    color: #77738b;
    font-size: 12px;
    margin-bottom: 6px;
}

.tc-info-value {
    color: #302b49;
    font-size: 14px;
    font-weight: 600;
    overflow-wrap: anywhere;
}

.tc-section-caption {
    color: #77738b;
    font-size: 13px;
    margin-top: -8px;
    margin-bottom: 14px;
}

.tc-step-number {
    display: inline-block;
    padding: 3px 9px;
    margin-right: 7px;
    border-radius: 7px;
    background: #eeeaff;
    color: #6254c7;
    font-size: 12px;
    font-weight: 700;
}

.tc-footer-note {
    padding: 15px 17px;
    border-radius: 12px;
    background: #f7f6fb;
    border: 1px solid #ebe9f2;
    color: #69657b;
    font-size: 13px;
    line-height: 1.7;
}

@media (max-width: 768px) {
    .tc-generation-intro {
        padding: 16px;
    }

    .tc-stat-card {
        margin-bottom: 8px;
    }
}
</style>
""")


# ============================================================
# 通用辅助函数
# ============================================================

def get_project_name(project):
    return (
        project.get("name")
        or project.get("project_name")
        or project.get("id")
        or "未命名项目"
    )


def get_status_label(status):
    labels = {
        "pending": "待审核",
        "approved": "已通过",
        "rejected": "已驳回",
        "ready_for_manual_review": "待人工审核",
        "needs_manual_review": "需要人工审核",
        "review_failed": "审核失败",
        "validation_failed": "校验失败",
        "completed": "已完成",
        "running": "执行中",
        "failed": "失败",
        "empty": "无候选用例",
    }
    return labels.get(status, status or "-")


def render_stat_card(label, value):
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))

    st.html(f"""
    <div class="tc-stat-card">
        <div class="tc-stat-label">{safe_label}</div>
        <div class="tc-stat-value">{safe_value}</div>
    </div>
    """)


def render_info_card(label, value):
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))

    st.html(f"""
    <div class="tc-info-card">
        <div class="tc-info-label">{safe_label}</div>
        <div class="tc-info-value">{safe_value}</div>
    </div>
    """)


def get_test_point_content(point):
    content = point.get("current_content")

    if isinstance(content, dict):
        return content

    return {}


def get_test_point_title(point):
    content = get_test_point_content(point)

    return (
        content.get("title")
        or content.get("name")
        or content.get("point_name")
        or point.get("point_id")
        or "未命名测试点"
    )


def show_test_point(point, index):
    content = get_test_point_content(point)

    point_no = point.get("point_id", "-")
    title = get_test_point_title(point)

    with st.expander(
        f"{index}. {point_no} | {title}",
        expanded=False,
    ):
        col1, col2 = st.columns([1, 2])

        with col1:
            st.caption("测试点业务编号")
            st.write(point_no)

        with col2:
            st.caption("人工审核状态")
            st.success("已通过")

        st.divider()
        st.write("**测试点内容**")

        if content:
            st.json(content)
        else:
            st.warning("当前测试点没有可展示的内容")

        if point.get("manual_comment"):
            st.write("**人工审核意见**")
            st.write(point.get("manual_comment"))


def show_generation_result(result):
    st.divider()

    st.subheader("本次 AI 测试用例生成结果")

    if result.get("success"):
        st.success("测试用例生成流程执行成功")
    else:
        st.error("测试用例生成流程未能全部成功")

    col1, col2, col3 = st.columns(3)

    with col1:
        render_stat_card(
            "测试点总数",
            result.get("total_points", 0),
        )

    with col2:
        render_stat_card(
            "成功处理测试点",
            result.get("successful_points", 0),
        )

    with col3:
        render_stat_card(
            "失败测试点",
            result.get("failed_points", 0),
        )

    st.write("")

    col4, col5 = st.columns(2)

    with col4:
        render_stat_card(
            "生成候选用例数",
            result.get("total_candidates", 0),
        )

    with col5:
        render_stat_card(
            "无候选用例测试点",
            result.get("empty_points", 0),
        )

    st.write("")

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        render_info_card(
            "生成批次 ID",
            result.get("batch_id", "-"),
        )

    with info_col2:
        render_info_card(
            "批次状态",
            get_status_label(result.get("status")),
        )

    point_results = result.get("point_results") or []

    if point_results:
        with st.expander("查看各测试点生成结果"):
            for index, item in enumerate(point_results, start=1):
                st.markdown(f"**测试点 {index}**")
                st.json(item)

    errors = result.get("errors") or []

    if errors:
        st.error("生成过程中存在错误")

        with st.expander("查看错误详情", expanded=True):
            for index, error in enumerate(errors, start=1):
                st.write(f"错误 {index}")

                if isinstance(error, dict):
                    st.json(error)
                else:
                    st.write(str(error))

    if result.get("batch_id"):
        st.info(
            "生成批次和候选用例已由后端 Service 持久化。"
            "请前往「08 测试用例管理」页面查看和管理候选用例。"
        )


# ============================================================
# 页面主体
# ============================================================

def main():
    render_header(
        title="AI 测试用例生成",
        description="根据结构化需求分析和已审核通过的测试点，调用 AI 自动生成测试用例候选集。",
        breadcrumb=["工作空间", "AI 测试中心", "AI 测试用例生成"],
    )

    st.html("""
    <div class="tc-generation-intro">
        <div class="tc-generation-intro-title">
            从已审核测试点生成测试用例
        </div>
        <div class="tc-generation-intro-text">
            选择项目、需求分析记录和测试点生成批次。
            系统将筛选人工审核通过的测试点，并为其生成测试用例候选集。
            生成前可以检查测试点内容和批次信息。
        </div>
    </div>
    """)

    # --------------------------------------------------------
    # 1. 项目选择
    # --------------------------------------------------------

    st.subheader("1. 选择项目")
    st.caption("选择本次测试用例生成任务所属的项目。")

    projects = list_projects()

    if not projects:
        st.warning("当前没有可用项目，请先创建项目。")
        return

    project_options = {
        project["id"]: project
        for project in projects
    }

    selected_project_id = st.selectbox(
        "项目",
        options=list(project_options.keys()),
        format_func=lambda project_id: get_project_name(
            project_options[project_id]
        ),
        key="ai_generation_project_id",
    )

    # --------------------------------------------------------
    # 2. 需求分析选择
    # --------------------------------------------------------

    st.divider()
    st.subheader("2. 选择需求分析记录")
    st.caption("选择已完成结构化分析的需求记录。")

    analyses = list_requirement_analyses(
        selected_project_id
    )

    if not analyses:
        st.warning(
            "当前项目没有需求分析记录，请先完成结构化需求分析。"
        )
        return

    analysis_options = {
        item["id"]: item
        for item in analyses
    }

    selected_analysis_id = st.selectbox(
        "需求分析记录",
        options=list(analysis_options.keys()),
        format_func=lambda analysis_id: (
            f"{analysis_options[analysis_id].get('module', '未命名模块')} "
            f"| {analysis_options[analysis_id].get('created_at', '')} "
            f"| {analysis_id[:8]}"
        ),
        key="ai_generation_analysis_id",
    )

    analysis = analysis_options[selected_analysis_id]

    with st.expander("查看需求分析摘要"):
        st.write(analysis.get("summary") or "暂无摘要")

    # --------------------------------------------------------
    # 3. 测试点生成批次选择
    # --------------------------------------------------------

    st.divider()
    st.subheader("3. 选择测试点生成批次")
    st.caption("选择与当前需求分析记录关联的测试点生成批次。")

    batches = list_test_point_generation_batches(
        selected_project_id,
        requirement_analysis_id=selected_analysis_id,
    )

    if not batches:
        st.warning(
            "当前需求分析没有测试点生成批次，请先完成测试点生成。"
        )
        return

    batch_options = {
        item["id"]: item
        for item in batches
    }

    selected_point_batch_id = st.selectbox(
        "测试点生成批次",
        options=list(batch_options.keys()),
        format_func=lambda batch_id: (
            f"{get_status_label(batch_options[batch_id].get('final_status'))} "
            f"| {batch_options[batch_id].get('generated_at', '')} "
            f"| {batch_id[:8]}"
        ),
        key="ai_generation_point_batch_id",
    )

    point_batch = batch_options[selected_point_batch_id]

    col1, col2 = st.columns(2)

    with col1:
        render_info_card(
            "测试点批次状态",
            get_status_label(point_batch.get("final_status")),
        )

    with col2:
        render_info_card(
            "测试点批次 ID",
            selected_point_batch_id,
        )

    # --------------------------------------------------------
    # 4. 获取人工审核通过的测试点
    # --------------------------------------------------------

    st.divider()
    st.subheader("4. 检查可生成的测试点")
    st.caption("系统只会使用当前批次中未删除且人工审核通过的测试点。")

    approved_points = list_test_points(
        batch_id=selected_point_batch_id,
        include_deleted=False,
        manual_review_status="approved",
    )

    approved_points = approved_points or []

    total_approved = len(approved_points)

    render_stat_card(
        "人工审核通过的测试点数量",
        total_approved,
    )

    st.write("")

    if not approved_points:
        st.warning(
            "当前批次没有人工审核通过的测试点，"
            "暂时不能生成测试用例。"
        )
        return

    st.success(
        f"当前批次有 {total_approved} 个测试点可以用于 AI 测试用例生成。"
    )

    with st.expander(
        f"查看全部待生成测试点（{total_approved} 个）"
    ):
        for index, point in enumerate(
            approved_points,
            start=1,
        ):
            show_test_point(point, index)

    # --------------------------------------------------------
    # 5. 生成规则说明
    # --------------------------------------------------------

    st.divider()
    st.subheader("5. 生成规则与费用提示")

    st.markdown("""
    本次生成遵循以下规则：

    1. 仅使用人工审核状态为「已通过」的测试点。
    2. 一次处理当前选中的测试点生成批次内全部通过审核的测试点。
    3. 每个测试点由 AI 生成测试用例候选集。
    4. 后端会执行集合校验、候选用例校验和 AI Reviewer。
    5. 生成结果会写入数据库，供测试用例管理页面使用。
    """)

    st.warning(
        "开始生成后将调用真实 AI 接口，可能产生 API 费用，"
        "并创建测试用例生成批次、候选用例及质量报告记录。"
        "请确认所选批次和测试点无误后再执行。"
    )

    # --------------------------------------------------------
    # 6. 执行 AI 测试用例生成
    # --------------------------------------------------------

    st.divider()
    st.subheader("6. 确认并开始生成")
    st.caption(
        f"本次将处理当前批次内的 {total_approved} 个人工审核通过的测试点。"
    )

    confirm_generation = st.checkbox(
        "我已确认，本次将处理当前批次内全部人工审核通过的测试点，"
        "并允许调用 AI 接口生成测试用例。",
        key="ai_generation_confirm",
    )

    generate_clicked = st.button(
        "🚀 开始 AI 测试用例生成",
        type="primary",
        disabled=not confirm_generation,
        width="stretch",
    )

    if generate_clicked:
        try:
            # 延迟导入，避免页面浏览时因 AI 配置问题而无法打开。
            from core.testcase_generation_service import (
                run_testcase_generation,
            )

            with st.spinner(
                "AI 正在生成测试用例，请耐心等待。"
            ):
                result = run_testcase_generation(
                    project_id=selected_project_id,
                    requirement_analysis_id=selected_analysis_id,
                    test_point_batch_id=selected_point_batch_id,
                )

            st.session_state[
                "ai_testcase_generation_result"
            ] = {
                "source_batch_id": selected_point_batch_id,
                "result": result,
            }

        except Exception as exc:
            st.error(
                f"测试用例生成执行异常：{exc}"
            )

    # --------------------------------------------------------
    # 7. 展示本次生成结果
    # --------------------------------------------------------

    saved_result = st.session_state.get(
        "ai_testcase_generation_result"
    )

    if (
        saved_result
        and saved_result.get("source_batch_id")
        == selected_point_batch_id
    ):
        show_generation_result(
            saved_result.get("result") or {}
        )

    # --------------------------------------------------------
    # 8. 后续操作
    # --------------------------------------------------------

    st.divider()
    st.subheader("7. 下一步")

    st.write(
        "测试用例生成完成后，可以进入测试用例管理工作台，"
        "查看候选用例、执行质量复检、人工编辑和审核。"
    )

    st.info(
        "请从左侧页面导航进入「08 测试用例管理」。"
    )


if __name__ == "__main__":
    main()
