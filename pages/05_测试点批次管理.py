
import streamlit as st

from core.time_utils import format_local_datetime
from database.repositories.project_repository import list_projects
from database.repositories.requirement_repository import (
    get_requirement_analysis,
    list_requirement_analyses,
)
from database.repositories.generation_batch_repository import (
    get_generation_batch,
    list_generation_batches,
)
from database.repositories.test_point_repository import (
    get_test_point_review_statistics,
    list_test_points,
)


# ============================================================
# 页面配置
# ============================================================

st.set_page_config(
    page_title="测试点批次管理 - GameTest AI",
    page_icon="📚",
    layout="wide",
)

st.title("📚 测试点生成批次管理")
st.caption("查看测试点生成历史、质量报告、需求来源及人工审核进度。")


# ============================================================
# 通用展示方法
# ============================================================

STATUS_LABELS = {
    "ready_for_manual_review": "待人工审核（质量检查通过）",
    "needs_manual_review": "需要人工复核",
    "review_failed": "AI Reviewer 检查未通过",
    "validation_failed": "Python Validator 检查未通过",
}

MANUAL_STATUS_LABELS = {
    "pending": "待审核",
    "approved": "已通过",
    "rejected": "已驳回",
}


def show_json(title: str, data):
    st.subheader(title)

    if data is None:
        st.info("暂无报告数据。")
    else:
        st.json(data, expanded=2)


def format_project(project: dict) -> str:
    return project.get("name") or project.get("id", "未命名项目")


def format_analysis(analysis: dict) -> str:
    module = analysis.get("module") or "未命名模块"
    summary = (analysis.get("summary") or "无摘要").replace("\n", " ").strip()

    if len(summary) > 45:
        summary = summary[:45] + "..."

    created_at = format_local_datetime(
        analysis.get("created_at")
    )

    return f"{module} | {summary} | {created_at}"


def format_batch(batch: dict) -> str:
    batch_id = batch.get("id", "未知批次")

    generated_at = format_local_datetime(
        batch.get("generated_at")
    )

    status = STATUS_LABELS.get(
        batch.get("final_status"),
        batch.get("final_status") or "未知状态",
    )

    return f"{generated_at} | {status} | {batch_id[:8]}"


def get_batch_statistics(batch_id: str) -> dict:
    """
    统计当前有效测试点数量及人工审核进度。
    list_test_points 默认不包含逻辑删除的数据。
    """

    points = list_test_points(batch_id=batch_id)
    review_stats = get_test_point_review_statistics(batch_id)

    return {
        "active_count": len(points),
        "pending": review_stats.get("pending", 0),
        "approved": review_stats.get("approved", 0),
        "rejected": review_stats.get("rejected", 0),
        "total": review_stats.get("total", 0),
    }


# ============================================================
# 加载项目
# ============================================================

try:
    projects = list_projects()
except Exception as exc:
    st.error(f"读取项目列表失败：{exc}")
    st.stop()

if not projects:
    st.warning("当前没有可用的游戏项目。")
    st.stop()


# ============================================================
# 一、项目筛选
# ============================================================

st.header("一、筛选条件")

project = st.selectbox(
    "游戏项目",
    options=projects,
    format_func=format_project,
    key="testpoint_batch_project",
)

project_id = project["id"]


# ============================================================
# 二、需求分析筛选
# ============================================================

try:
    analyses = list_requirement_analyses(project_id=project_id)
except Exception as exc:
    st.error(f"读取需求分析记录失败：{exc}")
    st.stop()

analysis_options = [None] + analyses


def format_analysis_filter(analysis):
    if analysis is None:
        return "全部需求分析记录"

    return format_analysis(analysis)


selected_analysis = st.selectbox(
    "按需求分析筛选（可选）",
    options=analysis_options,
    format_func=format_analysis_filter,
    key=f"testpoint_batch_analysis_filter_{project_id}",
)

analysis_filter_id = (
    selected_analysis.get("id")
    if selected_analysis is not None
    else None
)


# ============================================================
# 三、加载批次历史
# ============================================================

try:
    batches = list_generation_batches(
        project_id=project_id,
        requirement_analysis_id=analysis_filter_id,
    )
except Exception as exc:
    st.error(f"读取生成批次失败：{exc}")
    st.stop()

st.divider()
st.header("二、批次历史")


if not batches:
    st.info("当前筛选条件下没有测试点生成批次。")
    st.stop()


# ============================================================
# 四、统计批次信息
# ============================================================

batch_rows = []
batch_statistics_map = {}

with st.spinner("正在统计批次测试点及审核进度……"):
    for batch in batches:
        batch_id = batch["id"]

        try:
            stats = get_batch_statistics(batch_id)
        except Exception as exc:
            st.warning(
                f"批次 {batch_id} 的测试点统计读取失败：{exc}"
            )
            stats = {
                "active_count": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "total": 0,
            }

        batch_statistics_map[batch_id] = stats

        batch_rows.append({
            "生成时间": format_local_datetime(
                batch.get("generated_at")
            ),
            "批次 ID": batch_id,
            "需求分析 ID": batch.get("requirement_analysis_id") or "",
            "生成状态": STATUS_LABELS.get(
                batch.get("final_status"),
                batch.get("final_status") or "未知状态",
            ),
            "有效测试点数": stats["active_count"],
            "待审核": stats["pending"],
            "已通过": stats["approved"],
            "已驳回": stats["rejected"],
        })


# ============================================================
# 五、批次列表
# ============================================================

total_batches = len(batches)
total_points = sum(
    row["有效测试点数"]
    for row in batch_rows
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("生成批次数", total_batches)

with col2:
    st.metric("当前有效测试点总数", total_points)

with col3:
    st.metric(
        "待人工审核测试点",
        sum(row["待审核"] for row in batch_rows),
    )

st.dataframe(
    batch_rows,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "说明：有效测试点数默认排除已逻辑删除的数据；"
    "批次列表按生成时间倒序排列。"
)


# ============================================================
# 六、选择批次查看详情
# ============================================================

st.divider()
st.header("三、批次详情")

selected_batch = st.selectbox(
    "选择需要查看的生成批次",
    options=batches,
    format_func=format_batch,
    key=f"testpoint_batch_detail_{project_id}",
)

selected_batch_id = selected_batch["id"]


# 重新读取详情，确保展示数据库中的当前记录
try:
    batch_detail = get_generation_batch(selected_batch_id)
except Exception as exc:
    st.error(f"读取批次详情失败：{exc}")
    st.stop()

if batch_detail is None:
    st.error("该生成批次不存在。")
    st.stop()


# ============================================================
# 七、批次基本信息
# ============================================================

st.subheader("7.1 批次基本信息")

detail_col1, detail_col2 = st.columns(2)

with detail_col1:
    st.text("批次 ID")
    st.code(batch_detail.get("id", ""))

    st.text("项目 ID")
    st.code(batch_detail.get("project_id", ""))

    st.text("需求分析 ID")
    st.code(batch_detail.get("requirement_analysis_id", ""))

with detail_col2:
    st.metric(
        "批次状态",
        STATUS_LABELS.get(
            batch_detail.get("final_status"),
            batch_detail.get("final_status") or "未知状态",
        ),
    )

    st.text("生成时间")
    st.write(
        format_local_datetime(
            batch_detail.get("generated_at")
        )
    )


# ============================================================
# 八、测试点及审核统计
# ============================================================

st.subheader("7.2 测试点及人工审核统计")

stats = batch_statistics_map.get(selected_batch_id)

if stats is None:
    try:
        stats = get_batch_statistics(selected_batch_id)
    except Exception as exc:
        st.error(f"读取测试点统计失败：{exc}")
        stats = {
            "active_count": 0,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "total": 0,
        }

stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

with stat_col1:
    st.metric("有效测试点", stats["active_count"])

with stat_col2:
    st.metric("待审核", stats["pending"])

with stat_col3:
    st.metric("已通过", stats["approved"])

with stat_col4:
    st.metric("已驳回", stats["rejected"])


# ============================================================
# 九、关联需求分析来源
# ============================================================

st.subheader("7.3 关联需求分析")

requirement_analysis_id = batch_detail.get(
    "requirement_analysis_id"
)

try:
    source_analysis = get_requirement_analysis(
        requirement_analysis_id
    )
except Exception as exc:
    source_analysis = None
    st.warning(f"读取关联需求分析失败：{exc}")

if source_analysis is None:
    st.warning("未找到关联的需求分析记录。")
else:
    source_col1, source_col2 = st.columns(2)

    with source_col1:
        st.write("**需求模块**")
        st.write(source_analysis.get("module") or "未指定")

    with source_col2:
        st.write("**分析时间**")
        st.write(
            format_local_datetime(
                source_analysis.get("created_at")
            )
        )

    st.write("**需求摘要**")
    st.write(source_analysis.get("summary") or "暂无摘要")

    with st.expander("查看完整结构化需求分析", expanded=False):
        analysis_data = source_analysis.get("analysis_data")

        if analysis_data is None:
            st.info("该需求分析记录没有可展示的结构化数据。")
        else:
            st.json(analysis_data, expanded=2)


# ============================================================
# 十、质量检查报告
# ============================================================

st.divider()
st.subheader("7.4 质量检查报告")

report_tab1, report_tab2 = st.tabs([
    "Python Validator",
    "AI Reviewer",
])

with report_tab1:
    show_json(
        "Python Validator 质量校验报告",
        batch_detail.get("validation_report"),
    )

with report_tab2:
    show_json(
        "AI Reviewer 审查报告",
        batch_detail.get("review_report"),
    )


# ============================================================
# 十一、当前批次测试点预览
# ============================================================

st.divider()
st.subheader("7.5 当前批次测试点预览")

try:
    points = list_test_points(
        batch_id=selected_batch_id,
    )
except Exception as exc:
    st.error(f"读取批次测试点失败：{exc}")
    points = []

if not points:
    st.info("该批次当前没有有效测试点。")
else:
    st.caption(
        f"当前展示 {len(points)} 条有效测试点。"
        "本区域暂时只提供只读预览，编辑及审核操作将在后续步骤建设。"
    )

    for index, point in enumerate(points, start=1):
        point_id = point.get("point_id") or f"测试点 {index}"

        ai_status = point.get("ai_review_status") or "未知"
        manual_status = point.get("manual_review_status") or "未知"

        with st.expander(
            f"{point_id} | AI：{ai_status} | 人工："
            f"{MANUAL_STATUS_LABELS.get(manual_status, manual_status)}",
            expanded=(index == 1),
        ):
            st.json(
                point.get("current_content"),
                expanded=2,
            )

            st.caption(f"内部记录 ID：{point.get('id', '')}")

st.divider()
st.caption(
    "STEP 11.2.2 当前版本为批次历史只读管理页面。"
    "测试点编辑、人工审核和操作历史将在后续子步骤中实现。"
)
