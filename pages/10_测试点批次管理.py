
import json
import streamlit as st

from components.header import render_header
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
# 页面 Header
# ============================================================

render_header(
    title="测试点批次管理",
    description="统一查看 AI 测试点生成批次、质量报告、测试点统计和人工操作历史。",
    breadcrumb=["测试点中心", "测试点批次管理"],
)


# ============================================================
# 状态标签
# ============================================================

STATUS_LABELS = {
    "ready_for_manual_review": "待人工审核",
    "needs_manual_review": "需要人工审核",
    "review_failed": "AI 审核失败",
    "validation_failed": "校验失败",
}

MANUAL_STATUS_LABELS = {
    "pending": "待审核",
    "approved": "已通过",
    "rejected": "已驳回",
}


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


# ============================================================
# 通用展示辅助函数
# ============================================================

def display_value(value, default="-"):
    if value is None or value == "":
        return default
    return value


def format_project(project):
    name = (
        project.get("name")
        or project.get("project_name")
        or project.get("title")
        or "未命名项目"
    )
    return f"{name}（{project.get('id', '')}）"


def format_batch(batch):
    created_at = format_local_datetime(
        batch.get("generated_at")
        or batch.get("created_at")
    )

    batch_id = batch.get("id", "")

    status = batch.get("final_status") or batch.get("status")

    status_label = STATUS_LABELS.get(
        status,
        status or "未知状态",
    )

    return f"{created_at} | {status_label} | {batch_id}"


def format_analysis(analysis):
    module = analysis.get("module") or "未命名模块"
    analysis_id = analysis.get("id", "")
    return f"{module} | 分析 ID：{analysis_id}"


def format_test_point(point):
    point_id = (
        point.get("point_id")
        or point.get("id")
        or "未知编号"
    )

    content = point.get("current_content") or {}

    if isinstance(content, dict):
        title = content.get("title") or "未命名测试点"
    else:
        title = "测试点"

    status = MANUAL_STATUS_LABELS.get(
        point.get("manual_review_status"),
        point.get("manual_review_status", "未知"),
    )

    return f"{point_id} | {title} | {status}"


def to_display_data(value):
    """将常见数据类型转换为可供 Streamlit 展示的结构。"""

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

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def show_json(title, data):
    st.markdown(f"**{title}**")

    if data is None:
        st.info("暂无数据")
        return

    st.json(to_display_data(data), expanded=True)


def show_status(status):
    return STATUS_LABELS.get(
        status,
        status or "未知状态",
    )


# ============================================================
# 1. 项目选择
# ============================================================

st.subheader("一、选择项目")

try:
    projects = list_projects()

except Exception as exc:
    st.error(f"读取项目列表失败：{exc}")
    st.stop()


if not projects:
    st.info("当前没有可用项目，请先创建项目。")
    st.stop()


project_map = {
    project["id"]: project
    for project in projects
}

selected_project_id = st.selectbox(
    "选择项目",
    options=list(project_map.keys()),
    format_func=lambda value: format_project(
        project_map[value]
    ),
    key="testpoint_batch_project",
)


# ============================================================
# 2. 需求分析筛选
# ============================================================

st.divider()
st.subheader("二、需求分析筛选")

try:
    requirement_analyses = list_requirement_analyses(
        project_id=selected_project_id
    )

except Exception as exc:
    st.error(f"读取需求分析列表失败：{exc}")
    st.stop()


analysis_map = {
    analysis["id"]: analysis
    for analysis in requirement_analyses
}

analysis_filter_options = {
    "全部需求分析": None,
}

for analysis_id, analysis in analysis_map.items():
    analysis_filter_options[
        format_analysis(analysis)
    ] = analysis_id


selected_analysis_label = st.selectbox(
    "按需求分析筛选批次",
    options=list(analysis_filter_options.keys()),
    key=f"testpoint_batch_analysis_filter_{selected_project_id}",
)

analysis_filter_id = analysis_filter_options[
    selected_analysis_label
]


# ============================================================
# 3. 查询生成批次
# ============================================================

st.divider()
st.subheader("三、生成批次列表")

try:
    batches = list_generation_batches(
        project_id=selected_project_id,
        requirement_analysis_id=analysis_filter_id,
    )

except Exception as exc:
    st.error(f"读取生成批次失败：{exc}")
    st.stop()


if not batches:
    st.info("当前筛选条件下没有生成批次。")
    st.stop()


# ============================================================
# 4. 统计每个批次
# ============================================================

batch_statistics = {}

for batch in batches:
    batch_id = batch["id"]

    try:
        points = list_test_points(
            batch_id=batch_id
        )

        review_statistics = get_test_point_review_statistics(
            batch_id=batch_id
        )

        valid_points = [
            point
            for point in points
            if not point.get("is_deleted")
        ]

        batch_statistics[batch_id] = {
            "point_count": len(valid_points),
            "review_statistics": review_statistics or {},
        }

    except Exception as exc:
        batch_statistics[batch_id] = {
            "point_count": 0,
            "review_statistics": {},
            "error": str(exc),
        }


# ============================================================
# 5. 批次概览统计
# ============================================================

total_batches = len(batches)

total_points = sum(
    item["point_count"]
    for item in batch_statistics.values()
)

total_pending = 0

for item in batch_statistics.values():
    statistics = item.get("review_statistics") or {}

    total_pending += (
        statistics.get("pending", 0)
        or statistics.get("pending_count", 0)
        or 0
    )


metric_col1, metric_col2, metric_col3 = st.columns(3)

metric_col1.metric(
    "生成批次总数",
    total_batches,
)

metric_col2.metric(
    "有效测试点总数",
    total_points,
)

metric_col3.metric(
    "待人工审核",
    total_pending,
)


# ============================================================
# 6. 批次列表
# ============================================================

st.divider()
st.subheader("批次列表")

batch_rows = []

for batch in batches:
    batch_id = batch["id"]
    statistics = batch_statistics.get(batch_id, {})
    review_statistics = statistics.get(
        "review_statistics",
        {},
    )

    status = (
        batch.get("final_status")
        or batch.get("status")
    )

    batch_rows.append({
        "生成时间": format_local_datetime(
            batch.get("generated_at")
            or batch.get("created_at")
        ),
        "批次 ID": batch_id,
        "需求分析 ID": batch.get("requirement_analysis_id", "-"),
        "状态": show_status(status),
        "有效测试点": statistics.get("point_count", 0),
        "待审核": (
            review_statistics.get("pending", 0)
            or review_statistics.get("pending_count", 0)
        ),
        "通过": (
            review_statistics.get("approved", 0)
            or review_statistics.get("approved_count", 0)
        ),
        "驳回": (
            review_statistics.get("rejected", 0)
            or review_statistics.get("rejected_count", 0)
        ),
    })


st.dataframe(
    batch_rows,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# 7. 选择批次并重新读取详情
# ============================================================

st.divider()
st.subheader("四、批次详情")

batch_map = {
    batch["id"]: batch
    for batch in batches
}

selected_batch_id = st.selectbox(
    "选择要查看的生成批次",
    options=list(batch_map.keys()),
    format_func=lambda value: format_batch(
        batch_map[value]
    ),
    key=f"testpoint_batch_detail_{selected_project_id}",
)


try:
    selected_batch = get_generation_batch(
        selected_batch_id
    )

except Exception as exc:
    st.error(f"读取批次详情失败：{exc}")
    st.stop()


if not selected_batch:
    st.error("无法读取所选批次详情。")
    st.stop()


# ============================================================
# 8. 批次基本信息
# ============================================================

st.markdown("### 批次基本信息")

basic_col1, basic_col2 = st.columns(2)

with basic_col1:
    st.write("**批次 ID：**", selected_batch.get("id"))
    st.write(
        "**所属项目：**",
        format_project(project_map[selected_project_id]),
    )
    st.write(
        "**需求分析 ID：**",
        selected_batch.get("requirement_analysis_id"),
    )

with basic_col2:
    batch_status = (
        selected_batch.get("final_status")
        or selected_batch.get("status")
    )

    st.write(
        "**批次状态：**",
        show_status(batch_status),
    )

    st.write(
        "**生成时间：**",
        format_local_datetime(
            selected_batch.get("generated_at")
            or selected_batch.get("created_at")
        ),
    )


# ============================================================
# 9. 当前批次测试点及审核统计
# ============================================================

st.divider()
st.markdown("### 当前批次测试点及审核统计")

try:
    current_batch_points = list_test_points(
        batch_id=selected_batch_id
    )

    current_review_statistics = get_test_point_review_statistics(
        batch_id=selected_batch_id
    )

except Exception as exc:
    st.error(f"读取当前批次测试点统计失败：{exc}")
    st.stop()


review_statistics = current_review_statistics or {}

review_col1, review_col2, review_col3, review_col4 = st.columns(4)

review_col1.metric(
    "有效测试点",
    len([
        point
        for point in current_batch_points
        if not point.get("is_deleted")
    ]),
)

review_col2.metric(
    "待审核",
    review_statistics.get("pending", 0)
    or review_statistics.get("pending_count", 0),
)

review_col3.metric(
    "已通过",
    review_statistics.get("approved", 0)
    or review_statistics.get("approved_count", 0),
)

review_col4.metric(
    "已驳回",
    review_statistics.get("rejected", 0)
    or review_statistics.get("rejected_count", 0),
)


# ============================================================
# 10. 需求来源
# ============================================================

st.divider()
st.markdown("### 需求来源")

requirement_analysis_id = selected_batch.get(
    "requirement_analysis_id"
)

if requirement_analysis_id:

    try:
        requirement_analysis = get_requirement_analysis(
            requirement_analysis_id
        )

    except Exception as exc:
        requirement_analysis = None
        st.error(f"读取需求分析来源失败：{exc}")

    if requirement_analysis:
        st.write(
            "**需求模块：**",
            requirement_analysis.get("module") or "未填写",
        )

        st.write(
            "**需求摘要：**",
            requirement_analysis.get("summary") or "暂无摘要",
        )

        st.write(
            "**需求分析 ID：**",
            requirement_analysis_id,
        )

        with st.expander("查看完整需求分析数据"):
            show_json(
                "需求分析数据",
                requirement_analysis.get("analysis_data"),
            )

    else:
        st.warning("未找到该批次关联的需求分析记录。")

else:
    st.info("该批次没有关联需求分析记录。")


# ============================================================
# 11. Python Validator 和 AI Reviewer 报告
# ============================================================

st.divider()
st.markdown("### 质量检查报告")

validation_report = selected_batch.get(
    "validation_report"
)

review_report = selected_batch.get(
    "review_report"
)

report_tab1, report_tab2 = st.tabs(
    ["Python Validator", "AI Reviewer"]
)

with report_tab1:
    if validation_report is not None:
        show_json(
            "Python Validator 报告",
            validation_report,
        )
    else:
        st.info("当前批次没有 Python Validator 报告。")

with report_tab2:
    if review_report is not None:
        show_json(
            "AI Reviewer 报告",
            review_report,
        )
    else:
        st.info("当前批次没有 AI Reviewer 报告。")


# ============================================================
# 12. 当前批次测试点只读预览
# ============================================================

st.divider()
st.markdown("### 当前批次测试点预览")

if not current_batch_points:
    st.info("当前批次暂无测试点。")

else:
    st.caption(
        f"当前批次共读取到 {len(current_batch_points)} 条测试点记录。"
    )

    for index, point in enumerate(
        current_batch_points,
        start=1,
    ):
        point_content = point.get("current_content") or {}

        if isinstance(point_content, dict):
            title = point_content.get("title") or "未命名测试点"
            category = point_content.get("category") or "未分类"
            priority = point_content.get("priority") or "-"
        else:
            title = "测试点内容"
            category = "-"
            priority = "-"

        point_id = point.get(
            "point_id",
            point.get("id", "未知编号"),
        )

        with st.expander(
            f"{index}. {point_id} | {title}",
            expanded=False,
        ):
            col1, col2, col3 = st.columns(3)

            col1.write(f"类型：{category}")
            col2.write(f"优先级：{priority}")

            col3.write(
                "人工审核："
                + MANUAL_STATUS_LABELS.get(
                    point.get("manual_review_status"),
                    point.get("manual_review_status", "未知"),
                )
            )

            st.write(
                "**AI 审核状态：**",
                display_value(
                    point.get("ai_review_status")
                ),
            )

            show_json(
                "当前测试点内容",
                point_content,
            )


# ============================================================
# 13. 批次操作历史
# ============================================================

st.divider()
st.markdown("### 批次操作历史")

try:
    history_records = list_batch_test_point_history(
        selected_batch_id
    )

except Exception as exc:
    st.error(f"读取批次操作历史失败：{exc}")
    history_records = []


if not history_records:
    st.info("当前批次暂无测试点操作历史。")

else:
    # 最新记录在前
    history_records = list(reversed(history_records))

    st.caption(
        f"共 {len(history_records)} 条历史记录。"
    )

    # --------------------------------------------------------
    # 操作类型筛选
    # --------------------------------------------------------

    action_types = sorted({
        record.get("action_type", "unknown")
        for record in history_records
    })

    action_options = {
        "全部操作": None,
    }

    for action_type in action_types:
        action_options[
            HISTORY_ACTION_LABELS.get(
                action_type,
                action_type,
            )
        ] = action_type

    selected_action_label = st.selectbox(
        "按操作类型筛选",
        options=list(action_options.keys()),
        key=f"batch_history_action_{selected_batch_id}",
    )

    selected_action = action_options[
        selected_action_label
    ]

    # --------------------------------------------------------
    # 测试点编号 / 内部 ID 筛选
    # --------------------------------------------------------

    point_keyword = st.text_input(
        "按测试点业务编号或内部 ID 搜索",
        key=f"batch_history_keyword_{selected_batch_id}",
        placeholder="输入测试点编号或内部 ID",
    ).strip().lower()

    filtered_history = []

    for record in history_records:
        action_type = record.get("action_type", "unknown")

        if (
            selected_action is not None
            and action_type != selected_action
        ):
            continue

        record_point_id = str(
            record.get("test_point_id")
            or record.get("point_id")
            or ""
        ).lower()

        if point_keyword and point_keyword not in record_point_id:
            continue

        filtered_history.append(record)


    st.caption(
        f"当前筛选结果：{len(filtered_history)} 条历史记录"
    )


    # --------------------------------------------------------
    # 历史记录详情
    # --------------------------------------------------------

    if not filtered_history:
        st.info("没有符合当前筛选条件的历史记录。")

    else:
        for index, record in enumerate(
            filtered_history,
            start=1,
        ):
            action_type = record.get(
                "action_type",
                "unknown",
            )

            action_label = HISTORY_ACTION_LABELS.get(
                action_type,
                f"其他操作（{action_type}）",
            )

            created_at = format_local_datetime(
                record.get("created_at")
            )

            point_identifier = (
                record.get("point_id")
                or record.get("test_point_id")
                or "未知测试点"
            )

            with st.expander(
                f"{index}. {action_label} | "
                f"{point_identifier} | {created_at}",
                expanded=False,
            ):
                st.write("**操作类型：**", action_label)

                st.write(
                    "**测试点编号 / ID：**",
                    point_identifier,
                )

                st.write(
                    "**操作时间：**",
                    created_at,
                )

                comment = record.get("comment")

                if comment:
                    st.write("**操作意见 / 原因：**", comment)

                before_data = record.get("before_data")
                after_data = record.get("after_data")

                if action_type == "edited":
                    before_col, after_col = st.columns(2)

                    with before_col:
                        show_json(
                            "编辑前快照",
                            before_data,
                        )

                    with after_col:
                        show_json(
                            "编辑后快照",
                            after_data,
                        )

                else:
                    if before_data is not None:
                        show_json(
                            "操作前快照",
                            before_data,
                        )

                    if after_data is not None:
                        show_json(
                            "操作后快照",
                            after_data,
                        )

                    if (
                        before_data is None
                        and after_data is None
                    ):
                        st.info("该历史记录没有可展示的数据快照。")


# ============================================================
# 14. 页面说明
# ============================================================

st.divider()

st.info(
    "批次管理页面用于查看生成批次、需求来源、质量报告、"
    "测试点预览及人工操作历史。"
    "测试点编辑和人工审核请前往「测试点列表」页面操作。"
)
