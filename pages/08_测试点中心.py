
import html
import streamlit as st
from pydantic import ValidationError

from components.header import render_header

from database.repositories.project_repository import list_projects
from database.repositories.document_repository import list_documents

from database.repositories.generation_batch_repository import (
    get_generation_batch,
    list_generation_batches,
)

from database.repositories.test_point_repository import (
    get_test_point,
    list_test_points,
    list_test_point_history,
)
from database.connection import get_connection

from core.schemas import TestPointEditableContent
from core.time_utils import format_local_datetime
from core.testpoint_edit_service import edit_test_point
from core.testpoint_review_service import (
    approve_test_point,
    reject_test_point,
    batch_approve_test_points,
    batch_reject_test_points,
)


# ============================================================
# 页面样式
# ============================================================

st.html("""
<style>
.tp-page-intro {
    color: #77758b;
    font-size: 0.88rem;
    margin-top: -0.35rem;
    margin-bottom: 1.2rem;
}

.tp-section-title {
    font-size: 1.08rem;
    font-weight: 700;
    color: #29263d;
    margin: 0.4rem 0 0.8rem 0;
}

.tp-stat-card {
    background: linear-gradient(145deg, #ffffff, #f8f7ff);
    border: 1px solid #e9e6f5;
    border-radius: 13px;
    padding: 15px 17px;
    min-height: 100px;
}

.tp-stat-label {
    color: #77758b;
    font-size: 0.82rem;
    margin-bottom: 8px;
}

.tp-stat-value {
    color: #302b50;
    font-size: 1.8rem;
    font-weight: 750;
    line-height: 1.2;
}

.tp-panel {
    background: #ffffff;
    border: 1px solid #e9e6f5;
    border-radius: 13px;
    padding: 16px;
    margin-bottom: 12px;
}

.tp-muted {
    color: #858298;
    font-size: 0.82rem;
}

.tp-status {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 20px;
    background: #f0eef8;
    color: #6254a4;
    font-size: 0.78rem;
    font-weight: 600;
}

.tp-detail-label {
    color: #858298;
    font-size: 0.8rem;
    margin-bottom: 3px;
}

.tp-detail-value {
    color: #302d43;
    font-weight: 600;
    overflow-wrap: anywhere;
}
.tp-record {border:1px solid #e8e6f0;border-radius:12px;padding:14px 16px;margin:8px 0;background:#fff;}
.tp-record-title {font-size:1rem;font-weight:700;color:#302b50;}
.tp-record-meta {color:#77758b;font-size:.82rem;margin-top:6px;}
.tp-pill {display:inline-block;border-radius:999px;padding:3px 9px;font-size:.76rem;font-weight:650;background:#f0eef8;color:#6254a4;margin-left:6px;}
.tp-pill.pending {background:#fff4d6;color:#8a6200}.tp-pill.approved {background:#e6f6ee;color:#18794e}.tp-pill.rejected {background:#fdeaea;color:#a83232}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell {position:relative!important;height:132px!important;min-height:132px!important;max-height:132px!important;box-sizing:border-box;overflow:visible!important;background:#fff!important;border:1px solid #E7EAF1!important;border-radius:12px!important;padding:12px 18px!important;box-shadow:0 2px 8px rgba(23,32,51,.04);transition:border-color .15s,box-shadow .15s;}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell:hover {border-color:#C9C4E8!important;box-shadow:0 3px 10px rgba(23,32,51,.06);}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell::after {content:"⌄";position:absolute;right:16px;bottom:12px;z-index:3;color:#8490A3;font-size:20px;line-height:1;font-weight:600;pointer-events:none;}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell [data-testid="stPopover"] {position:static!important;z-index:2!important;}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell [data-testid="stPopover"] button[aria-haspopup="dialog"] {position:absolute!important;inset:0!important;z-index:5!important;display:block!important;width:100%!important;height:132px!important;min-height:132px!important;max-height:132px!important;max-width:none!important;margin:0!important;padding:0!important;opacity:0!important;color:transparent!important;background:transparent!important;border:0!important;box-shadow:none!important;cursor:pointer!important;}

</style>
""")





# ============================================================
# 操作成功反馈
# ============================================================

review_success_message = st.session_state.pop(
    "test_point_review_success_message",
    None,
)

if review_success_message:
    st.success(review_success_message)

if st.session_state.pop("test_point_edit_success", False):
    st.success(
        "测试点编辑成功，修改历史已保存。"
        "人工审核状态已重置为 pending，AI 审核状态保持不变。"
    )


# ============================================================
# 通用函数
# ============================================================

def format_project(project):
    name = (
        project.get("project_name")
        or project.get("name")
        or "未命名项目"
    )

    return f"{name}（{project.get('id', '')}）"


def format_batch(batch):
    return (
        f"{format_local_datetime(batch.get('generated_at'))} | "
        f"{batch.get('id', '')}"
    )


def format_test_point(point):
    point_id = (
        point.get("point_id")
        or point.get("id")
        or "未知编号"
    )

    return (
        f"{point_id} | "
        f"人工审核：{point.get('manual_review_status', '未知')} | "
        f"AI审核：{point.get('ai_review_status', '未知')}"
    )


def get_point_title(point):
    content = point.get("current_content") or {}

    if isinstance(content, dict):
        return (
            content.get("title")
            or content.get("name")
            or content.get("description")
            or "未命名测试点"
        )

    return "测试点内容"


def show_content(title, content):
    st.subheader(title)

    if content is None:
        st.info("暂无内容")

    elif isinstance(content, (dict, list)):
        st.json(content, expanded=True)

    else:
        st.code(str(content))


def calculate_statistics(points):
    """
    根据测试点实际记录计算统计数据。
    逻辑删除记录单独统计，不计入有效测试点总数。
    """

    statistics = {
        "total": 0,
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "other": 0,
        "deleted": 0,
    }

    for point in points:
        is_deleted = bool(point.get("is_deleted", 0))

        if is_deleted:
            statistics["deleted"] += 1
            continue

        statistics["total"] += 1

        status = point.get("manual_review_status")

        if status == "pending":
            statistics["pending"] += 1

        elif status == "approved":
            statistics["approved"] += 1

        elif status == "rejected":
            statistics["rejected"] += 1

        else:
            statistics["other"] += 1

    return statistics


# ============================================================
# 测试点操作历史
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


def render_test_point_history(test_point_id):
    """展示单个测试点的操作历史及其数据快照。"""

    st.divider()
    st.subheader("操作历史")

    try:
        history_records = list_test_point_history(test_point_id)

    except Exception as exc:
        st.error(f"读取测试点操作历史失败：{exc}")
        return

    if not history_records:
        st.info("该测试点暂无操作历史记录。")
        return

    history_records = list(reversed(history_records))

    st.caption(
        f"共 {len(history_records)} 条历史记录，"
        "按操作时间倒序排列（最新记录在前）。"
    )

    for index, record in enumerate(history_records, start=1):
        action_type = record.get("action_type") or "unknown"

        action_label = HISTORY_ACTION_LABELS.get(
            action_type,
            f"其他操作（{action_type}）",
        )

        created_at = format_local_datetime(
            record.get("created_at")
        )

        title = f"{index}. {action_label} | {created_at}"

        with st.expander(title, expanded=False):
            st.write("操作类型：", action_label)
            st.write("操作时间：", created_at)

            comment = record.get("comment")

            if comment:
                st.write("操作意见 / 原因：", comment)
            else:
                st.caption("无操作意见或原因。")

            before_data = record.get("before_data")
            after_data = record.get("after_data")

            if action_type == "edited":
                show_content("修改前快照", before_data)
                show_content("修改后快照", after_data)

            else:
                if before_data is not None:
                    show_content("操作前快照", before_data)

                if after_data is not None:
                    show_content("操作后快照", after_data)

                if before_data is None and after_data is None:
                    st.info("该条历史记录没有可展示的快照数据。")


# ============================================================
# 测试点编辑
# ============================================================

def render_edit_form(test_point):
    """
    渲染测试点编辑表单。
    只允许修改 TestPointEditableContent 中定义的七个字段。
    """

    if test_point.get("is_deleted"):
        st.warning("该测试点已逻辑删除，不能直接编辑，请先恢复。")
        return

    current_content = test_point.get("current_content")

    if not isinstance(current_content, dict):
        st.error(
            "当前测试点内容不是有效的结构化对象，"
            "暂时无法进行编辑。"
        )
        return

    category_options = [
        "positive",
        "negative",
        "boundary",
        "exception",
        "state",
        "data",
    ]

    priority_options = [
        "P0",
        "P1",
        "P2",
        "P3",
    ]

    current_category = current_content.get("category")
    current_priority = current_content.get("priority")

    if current_category not in category_options:
        st.error(
            f"当前测试点类型不符合编辑规则：{current_category}"
        )
        return

    if current_priority not in priority_options:
        st.error(
            f"当前测试点优先级不符合编辑规则：{current_priority}"
        )
        return

    st.info(
        "编辑说明：测试点编号和原始内容不可修改。"
        "保存后会记录修改前后的完整快照，"
        "并将人工审核状态重置为 pending。"
    )

    with st.form(
        key=f"edit_test_point_{test_point['id']}"
    ):

        st.text_input(
            "测试点编号（不可修改）",
            value=str(test_point.get("point_id", "")),
            disabled=True,
        )

        edit_requirement_id = st.text_input(
            "需求编号",
            value=current_content.get("requirement_id", ""),
        )

        edit_category = st.selectbox(
            "测试点类型",
            options=category_options,
            index=category_options.index(current_category),
            format_func=lambda value: {
                "positive": "正向测试",
                "negative": "反向测试",
                "boundary": "边界测试",
                "exception": "异常测试",
                "state": "状态测试",
                "data": "数据测试",
            }.get(value, value),
        )

        edit_title = st.text_input(
            "测试点标题",
            value=current_content.get("title", ""),
        )

        edit_objective = st.text_area(
            "测试目标",
            value=current_content.get("test_objective", ""),
            height=100,
        )

        edit_coverage = st.text_area(
            "覆盖描述",
            value=current_content.get("coverage_description", ""),
            height=120,
        )

        edit_priority = st.selectbox(
            "优先级",
            options=priority_options,
            index=priority_options.index(current_priority),
        )

        edit_source_rule = st.text_area(
            "来源规则",
            value=current_content.get("source_rule", ""),
            height=120,
        )

        submitted = st.form_submit_button(
            "保存测试点修改",
            type="primary",
            width="stretch",
        )

        if submitted:
            try:
                updated_content = TestPointEditableContent(
                    requirement_id=edit_requirement_id,
                    category=edit_category,
                    title=edit_title,
                    test_objective=edit_objective,
                    coverage_description=edit_coverage,
                    priority=edit_priority,
                    source_rule=edit_source_rule,
                )

                result = edit_test_point(
                    test_point["id"],
                    updated_content,
                )

                if result.get("success"):
                    st.session_state[
                        "test_point_edit_success"
                    ] = True

                    st.rerun()

                else:
                    st.error("测试点编辑未成功，请检查服务返回结果。")

            except ValidationError as exc:
                st.error("编辑内容校验失败：")

                for error in exc.errors():
                    field_name = ".".join(
                        str(item) for item in error["loc"]
                    )

                    st.write(
                        f"- {field_name}: {error['msg']}"
                    )

            except (ValueError, TypeError, RuntimeError) as exc:
                st.error(f"测试点编辑失败：{exc}")


# ============================================================
# 单条人工审核
# ============================================================

def render_single_review_actions(test_point):
    """
    渲染单条人工审核操作。
    AI 审核状态仅展示为参考，不作为人工审核的限制条件。
    """

    if test_point.get("is_deleted"):
        st.info("已逻辑删除的测试点不能进行人工审核。")
        return

    if test_point.get("manual_review_status") != "pending":
        st.info("该测试点当前不是 pending 状态，无需重复审核。")
        return

    st.subheader("人工审核")

    comment = st.text_input(
        "通过意见（可选）",
        key=f"single_review_comment_{test_point['id']}",
    )

    if st.button(
        "审核通过",
        key=f"approve_test_point_{test_point['id']}",
        type="primary",
        width="stretch",
    ):
        try:
            result = approve_test_point(
                test_point["id"],
                comment,
            )

            if result.get("success"):
                st.session_state[
                    "test_point_review_success_message"
                ] = "测试点人工审核通过。"

                st.rerun()

            else:
                st.error("审核未成功，请检查审核服务返回结果。")

        except Exception as exc:
            st.error(f"测试点审核失败：{exc}")

    reason = st.text_area(
        "驳回原因（必填）",
        key=f"single_review_reject_reason_{test_point['id']}",
    )

    if st.button(
        "驳回测试点",
        key=f"reject_test_point_{test_point['id']}",
        width="stretch",
    ):
        if not reason.strip():
            st.error("驳回原因不能为空。")

        else:
            try:
                result = reject_test_point(
                    test_point["id"],
                    reason,
                )

                if result.get("success"):
                    st.session_state[
                        "test_point_review_success_message"
                    ] = "测试点已驳回，审核历史已保存。"

                    st.rerun()

                else:
                    st.error("驳回未成功，请检查审核服务返回结果。")

            except Exception as exc:
                st.error(f"测试点驳回失败：{exc}")


# ============================================================
# 批量人工审核
# ============================================================

def render_batch_review_actions(batch_points, batch_id):
    """
    从当前批次全部记录中筛选可审核对象。
    不受列表当前的状态筛选影响。
    """

    pending_points = [
        point
        for point in batch_points
        if not point.get("is_deleted")
        and point.get("manual_review_status") == "pending"
    ]

    st.subheader("批量人工审核")

    if not pending_points:
        st.info("当前批次没有可批量审核的 pending 测试点。")
        return

    point_options = {
        point["id"]: point
        for point in pending_points
        if point.get("id")
    }

    selected_ids = st.multiselect(
        "选择待审核测试点",
        options=list(point_options.keys()),
        format_func=lambda point_id: format_test_point(
            point_options[point_id]
        ),
        key=f"batch_review_selection_{batch_id}",
    )

    approve_comment = st.text_input(
        "批量通过意见（可选）",
        key=f"batch_review_approve_comment_{batch_id}",
    )

    if st.button(
        "批量通过",
        key=f"batch_approve_test_points_{batch_id}",
        type="primary",
        width="stretch",
    ):
        if not selected_ids:
            st.error("请至少选择一条待审核测试点。")

        else:
            try:
                result = batch_approve_test_points(
                    selected_ids,
                    approve_comment,
                )

                if result.get("success"):
                    st.session_state[
                        "test_point_review_success_message"
                    ] = (
                        f"批量审核通过成功，共处理 "
                        f"{result.get('count', len(selected_ids))} 条测试点。"
                    )

                    st.rerun()

                else:
                    st.error("批量通过未成功，请检查审核服务返回结果。")

            except Exception as exc:
                st.error(f"批量审核失败：{exc}")

    reject_reason = st.text_area(
        "批量驳回原因（必填）",
        key=f"batch_review_reject_reason_{batch_id}",
    )

    if st.button(
        "批量驳回",
        key=f"batch_reject_test_points_{batch_id}",
        width="stretch",
    ):
        if not selected_ids:
            st.error("请至少选择一条待审核测试点。")

        elif not reject_reason.strip():
            st.error("批量驳回原因不能为空。")

        else:
            try:
                result = batch_reject_test_points(
                    selected_ids,
                    reject_reason,
                )

                if result.get("success"):
                    st.session_state[
                        "test_point_review_success_message"
                    ] = (
                        f"批量驳回成功，共处理 "
                        f"{result.get('count', len(selected_ids))} 条测试点。"
                    )

                    st.rerun()

                else:
                    st.error("批量驳回未成功，请检查审核服务返回结果。")

            except Exception as exc:
                st.error(f"批量审核失败：{exc}")


# ============================================================
# 1. 项目选择
# ============================================================

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

project_ids = list(project_options)
if st.session_state.get("test_point_list_project") not in project_options:
    st.session_state["test_point_list_project"] = project_ids[0]
selected_project_id = st.session_state["test_point_list_project"]

# 需求表格中的名称链接通过当前页面查询参数触发页面跳转，
# 在这里恢复原有的 session_state 上下文后再进入测试点列表。
open_document_id = st.query_params.get("open_test_points_document")
if open_document_id:
    st.session_state["test_point_context"] = {
        "project_id": str(selected_project_id),
        "document_id": str(open_document_id),
    }
    del st.query_params["open_test_points_document"]
    st.switch_page("pages/15_测试点详情.py")

# 仅在确认不需要跳转后渲染当前页面标题，避免跳转时残留「测试点中心」标题。
render_header(
    title="测试点中心",
    description="按项目集中查看需求文档，并从需求入口进入对应的测试点详情。",
    breadcrumb=["测试点中心"],
)



selected_project = project_options[selected_project_id]
project_name = html.escape(str(selected_project.get("project_name") or selected_project.get("name") or "未命名项目"))
project_description = html.escape(str(selected_project.get("description") or "暂无项目描述"))
project_status = selected_project.get("status", "active")
status_label = "已归档" if project_status == "archived" else "进行中"
status_color, status_bg = ("#64748B", "#F1F5F9") if project_status == "archived" else ("#15803D", "#DCFCE7")
try:
    project_documents = list_documents(
        project_id=selected_project_id,
        include_deleted=True,
    )
except Exception as exc:
    st.error(f"读取项目需求列表失败：{exc}")
    st.stop()

requirement_groups = {}
for item in project_documents:
    requirement_groups.setdefault(item.get("document_key") or item.get("id"), []).append(item)

requirement_items = []
for key, versions in requirement_groups.items():
    active_versions = [
        item for item in versions
        if item.get("is_active") and not item.get("is_deleted")
    ]
    available_versions = [
        item for item in versions
        if not item.get("is_deleted")
    ]
    display_version = (
        active_versions[0]
        if active_versions
        else available_versions[0] if available_versions else versions[0]
    )
    requirement_items.append({
        "document": display_version,
        "version_count": len(versions),
        "active": bool(active_versions),
        "has_available": bool(available_versions),
    })

with get_connection() as conn:
    project_stats_row = conn.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN tp.manual_review_status = 'approved' THEN 1 ELSE 0 END) AS approved,
               SUM(CASE WHEN tp.manual_review_status = 'pending' THEN 1 ELSE 0 END) AS pending
        FROM test_points tp
        JOIN generation_batches gb ON gb.id = tp.batch_id
        WHERE gb.project_id = ? AND tp.is_deleted = 0
    """, (selected_project_id,)).fetchone()
project_stats = dict(project_stats_row) if project_stats_row else {"total": 0, "approved": 0, "pending": 0}
project_col, stats_col = st.columns([1.15, 1.85], gap="medium", vertical_alignment="center")
with project_col:
    with st.container(key="test_point_project_picker_shell"):
        st.html(f'''<div style="color:#172033;padding:2px 2px 18px;min-height:92px;box-sizing:border-box"><div style="display:flex;align-items:center;justify-content:space-between;gap:12px"><strong>🎮 {project_name}</strong><span style="border-radius:20px;padding:3px 8px;color:{status_color};background:{status_bg};font-size:11px">● {status_label}</span></div><div style="color:#64748B;font-size:12px;margin-top:8px">{project_description}</div><div style="color:#94A3B8;font-size:10px;margin-top:7px">项目 ID：{html.escape(str(selected_project_id))}</div></div>''')
        with st.popover("切换项目", width="stretch"):
            for project_id in project_ids:
                project = project_options[project_id]
                name = html.escape(str(project.get("project_name") or project.get("name") or "未命名项目"))
                desc = html.escape(str(project.get("description") or "暂无项目描述"))
                current = project_id == selected_project_id
                color, bg = ("#64748B", "#F1F5F9") if project.get("status") == "archived" else ("#15803D", "#DCFCE7")
                with st.container():
                    st.html(f'<div style="border:1px solid {"#8B7CF6" if current else "#E5E7EB"};background:{"#F8F7FF" if current else "#FFF"};border-radius:11px;padding:13px 15px;margin:5px 0"><strong>🎮 {name}</strong><span style="float:right;color:{color};background:{bg};padding:3px 8px;border-radius:20px;font-size:11px">{"已归档" if project.get("status") == "archived" else "进行中"}</span><div style="color:#64748B;font-size:12px;margin-top:7px">{desc}</div><div style="color:#94A3B8;font-size:10px;margin-top:7px">项目 ID：{html.escape(str(project_id))}</div></div>')
                    if not current and st.button("选择此项目", key=f"choose_test_point_project_{project_id}", width="stretch"):
                        st.session_state["test_point_list_project"] = project_id
                        st.rerun()
with stats_col:
    metric_cols = st.columns(3, gap="small")
    for col, label, value in zip(metric_cols, ("测试点总数", "已通过", "待审核"), ("total", "approved", "pending")):
        with col:
            st.metric(label, project_stats.get(value) or 0)


# ============================================================
# 2. 需求列表
# ============================================================

st.markdown("""
<div class="gt-section">
    <div class="gt-section-title">需求列表</div>
    <div class="gt-section-desc">集中查看当前项目的需求文档，点击需求名称进入对应需求的测试点列表。</div>
</div>
""", unsafe_allow_html=True)

search_col, filter_col = st.columns(
    [12, 1],
    vertical_alignment="center",
    gap="small",
)
with search_col:
    requirement_search = st.text_input(
        "搜索需求文档",
        placeholder="搜索需求名称…",
        key="test_point_center_requirement_search",
        label_visibility="collapsed",
        width="stretch",
    )
with filter_col:
    with st.popover(
        "筛选",
        icon=":material/filter_list:",
        help="筛选需求文档",
        width="stretch",
    ):
        st.markdown("**文档状态**")
        requirement_filter = st.radio(
            "需求文档状态筛选",
            options=["全部状态", "有效版本", "暂无有效版本"],
            key="test_point_center_requirement_filter",
            label_visibility="collapsed",
        )

search_text = requirement_search.strip().lower()
filtered_requirements = []
for entry in requirement_items:
    document = entry["document"]
    matches_search = (
        not search_text
        or search_text in str(document.get("document_name") or "").lower()
        or search_text in str(document.get("document_key") or "").lower()
    )
    matches_filter = (
        requirement_filter == "全部状态"
        or (requirement_filter == "有效版本" and entry["active"])
        or (requirement_filter == "暂无有效版本" and not entry["active"])
    )
    if matches_search and matches_filter:
        filtered_requirements.append(entry)

if not filtered_requirements:
    st.info("暂无符合条件的需求文档。")
else:
    table_rows = []
    for entry in filtered_requirements:
        document = entry["document"]
        document_id = str(document.get("id") or "")
        document_name = str(document.get("document_name") or "未命名需求")
        version_label = f"Ver. {document.get('version') or 1}"
        file_type = str(document.get("file_type") or "未知").upper()
        detail_url = (
            "?open_test_points_document="
            + __import__("urllib.parse", fromlist=["quote"]).quote(document_id)
        )
        if entry["active"]:
            status_html = '<span class="gt-tapd-status gt-tapd-status-active">有效版本</span>'
        elif entry["has_available"]:
            status_html = '<span class="gt-tapd-status gt-tapd-status-deleted">暂无有效版本</span>'
        else:
            status_html = '<span class="gt-tapd-status gt-tapd-status-deleted">版本均已删除</span>'
        table_rows.append(
            "<tr>"
            f'<td class="gt-tapd-name"><a href="{html.escape(detail_url, quote=True)}" title="查看该需求版本下的测试点">{html.escape(document_name)}</a></td>'
            f'<td class="gt-tapd-version">{html.escape(version_label)}</td>'
            f'<td class="gt-tapd-type">{html.escape(file_type)}</td>'
            f'<td class="gt-tapd-state">{status_html}</td>'
            "</tr>"
        )

    st.html("""
    <style>
    .gt-tapd-wrap {
        width: 100%;
        overflow-x: auto;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        background: #FFFFFF;
    }
    .gt-tapd-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        table-layout: fixed;
        color: #303133;
        font-size: 13px;
    }
    .gt-tapd-table thead th {
        height: 42px;
        padding: 0 14px;
        text-align: left;
        white-space: nowrap;
        color: #606266;
        background: #F5F7FA;
        border-bottom: 1px solid #E4E7ED;
        font-weight: 600;
    }
    .gt-tapd-table tbody td {
        height: 48px;
        padding: 7px 14px;
        border-bottom: 1px solid #EBEEF5;
        vertical-align: middle;
        background: #FFFFFF;
    }
    .gt-tapd-table tbody tr:last-child td { border-bottom: 0; }
    .gt-tapd-table tbody tr:hover td { background: #F8FAFD; }
    .gt-tapd-table thead th:nth-child(1),
    .gt-tapd-table tbody td:nth-child(1) { width: 60%; }
    .gt-tapd-table thead th:nth-child(2),
    .gt-tapd-table tbody td:nth-child(2) { width: 12%; color: #606266; }
    .gt-tapd-table thead th:nth-child(3),
    .gt-tapd-table tbody td:nth-child(3) { width: 12%; color: #606266; }
    .gt-tapd-table thead th:nth-child(4),
    .gt-tapd-table tbody td:nth-child(4) { width: 16%; }
    .gt-tapd-table .gt-tapd-name a {
        color: #303133;
        text-decoration: none;
        font-weight: 500;
    }
    .gt-tapd-table .gt-tapd-name a:hover {
        color: #6D5CE7;
        text-decoration: underline;
    }
    .gt-tapd-status {
        display: inline-block;
        padding: 3px 9px;
        border-radius: 3px;
        font-size: 12px;
        line-height: 18px;
        white-space: nowrap;
    }
    .gt-tapd-status-active { color: #67C23A; background: #F0F9EB; }
    .gt-tapd-status-deleted { color: #E6A23C; background: #FDF6EC; }
    @media (max-width: 640px) {
        .gt-tapd-table { min-width: 560px; }
    }
    </style>
    """)
    table_html = (
        '<div class="gt-tapd-wrap"><table class="gt-tapd-table">'
        '<thead><tr><th>需求名称</th><th>当前版本</th><th>文件类型</th><th>状态</th></tr></thead>'
        '<tbody>' + "".join(table_rows) + '</tbody></table></div>'
    )
    st.html(table_html)

st.caption("提示：需求文档版本查看、恢复和删除操作请前往「需求版本管理」页面。")


# 8. 页面说明
# ============================================================

st.divider()

st.info(
    "当前页面以需求为入口组织测试点。选择需求名称后，将进入对应需求版本的测试点详情，"
    "测试点查看、编辑和审核操作均在测试点详情页面完成。"
)
