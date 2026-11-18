
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
    list_batch_test_point_history,
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


# ============================================================
# 十二、当前批次操作历史
# ============================================================

HISTORY_ACTION_LABELS = {
    "created": "创建测试点",
    "edited": "编辑测试点",
    "approved": "人工审核通过",
    "rejected": "人工审核驳回",
    "batch_approved": "批量审核通过",
    "batch_rejected": "批量审核驳回",
    "deleted": "删除测试点",
    "restored": "恢复测试点",
}


def get_history_point_label(history: dict) -> str:
    """优先使用快照中的业务测试点编号，缺失时回退到内部 UUID。"""
    for snapshot_name in ("after_data", "before_data"):
        snapshot = history.get(snapshot_name)
        if isinstance(snapshot, dict):
            point_id = snapshot.get("point_id")
            if point_id:
                return str(point_id)

    return str(history.get("test_point_id") or "未知测试点")


def history_matches_point_filter(history: dict, selected_value: str) -> bool:
    """筛选值可以是业务测试点编号，也可以是内部记录 UUID。"""
    if selected_value == "全部测试点":
        return True

    if str(history.get("test_point_id") or "") == selected_value:
        return True

    return get_history_point_label(history) == selected_value


def render_history_snapshot(title: str, snapshot):
    st.markdown(f"**{title}**")
    if snapshot is None:
        st.caption("无快照数据。")
    else:
        st.json(snapshot, expanded=2)


st.divider()
st.subheader("7.6 批次操作历史")

try:
    batch_history = list_batch_test_point_history(selected_batch_id)
except Exception as exc:
    st.error(f"读取批次操作历史失败：{exc}")
    batch_history = None

if batch_history is None:
    # 查询异常时不把异常误报成“暂无历史”。
    pass
elif not batch_history:
    st.info("该批次暂无操作历史记录。")
else:
    # Repository 按 created_at、rowid 正序返回。
    # 反转后，时间较新及同一时间后写入的记录均置顶。
    batch_history = list(reversed(batch_history))

    action_values = sorted({
        str(item.get("action_type") or "unknown")
        for item in batch_history
    })
    action_options = ["全部操作"] + action_values

    point_values = set()
    for item in batch_history:
        point_values.add(get_history_point_label(item))
        internal_id = item.get("test_point_id")
        if internal_id:
            point_values.add(str(internal_id))

    point_options = ["全部测试点"] + sorted(point_values)

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        selected_action = st.selectbox(
            "按操作类型筛选",
            options=action_options,
            format_func=lambda value: (
                "全部操作"
                if value == "全部操作"
                else HISTORY_ACTION_LABELS.get(
                    value,
                    f"其他操作（{value}）",
                )
            ),
            key=f"batch_history_action_{selected_batch_id}",
        )

    with filter_col2:
        selected_point = st.selectbox(
            "按测试点编号 / 内部 ID 筛选",
            options=point_options,
            key=f"batch_history_point_{selected_batch_id}",
        )

    filtered_history = [
        item
        for item in batch_history
        if (
            selected_action == "全部操作"
            or item.get("action_type") == selected_action
        )
        and history_matches_point_filter(item, selected_point)
    ]

    st.caption(
        f"当前批次共 {len(batch_history)} 条历史记录，"
        f"筛选后显示 {len(filtered_history)} 条。最新操作置顶。"
    )

    if not filtered_history:
        st.info("没有符合当前筛选条件的操作历史。")
    else:
        for index, history in enumerate(filtered_history, start=1):
            action_type = str(history.get("action_type") or "unknown")
            action_label = HISTORY_ACTION_LABELS.get(
                action_type,
                f"其他操作（{action_type}）",
            )
            point_label = get_history_point_label(history)
            created_at = format_local_datetime(history.get("created_at"))
            comment = history.get("comment") or "无操作意见"

            with st.expander(
                f"{action_label} | {point_label} | {created_at}",
                expanded=(index == 1),
            ):
                st.write(f"**操作类型：** {action_label}")
                st.write(f"**测试点编号：** {point_label}")
                st.caption(
                    f"测试点内部 ID：{history.get('test_point_id') or '未知'}"
                )
                st.write(f"**操作时间：** {created_at}")
                st.write(f"**操作意见：** {comment}")

                before_data = history.get("before_data")
                after_data = history.get("after_data")

                if action_type == "edited":
                    st.markdown("**编辑前后内容对比**")
                    render_history_snapshot("修改前", before_data)
                    render_history_snapshot("修改后", after_data)
                else:
                    if before_data is not None:
                        render_history_snapshot("操作前快照", before_data)
                    if after_data is not None:
                        render_history_snapshot("操作后快照", after_data)
                    if before_data is None and after_data is None:
                        st.caption("该操作没有可展示的快照数据。")

st.divider()
st.caption(
    "STEP 11.2.6.3.2：当前批次操作历史支持查询、筛选及快照查看。"
)
