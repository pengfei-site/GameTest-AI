
import html
import streamlit as st
from pydantic import ValidationError

from components.header import render_header

from database.repositories.project_repository import list_projects

from database.repositories.document_repository import list_documents

from database.repositories.test_point_repository import (
    get_test_point,
    list_test_points_by_document_version,
    list_test_point_history,
)

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
.tp-scope-summary {
    margin-top: 0.9rem;
    padding: 12px 15px;
    border: 1px solid #e8e6f2;
    border-radius: 10px;
    background: linear-gradient(110deg, #faf9ff 0%, #ffffff 72%);
}
.tp-scope-summary-label {
    color: #858298;
    font-size: 0.76rem;
    margin-bottom: 5px;
}
.tp-scope-summary-value {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 7px;
    color: #302b50;
    font-size: 0.92rem;
    font-weight: 650;
}
.tp-scope-separator { color: #aaa6bb; font-weight: 400; }
.tp-scope-version {
    padding: 2px 8px;
    border-radius: 6px;
    background: #efedfb;
    color: #6254a4;
    font-size: 0.78rem;
}
.tp-scope-active, .tp-scope-history {
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.74rem;
    font-weight: 600;
}
.tp-scope-active { background: #e8f6ee; color: #18794e; }
.tp-scope-history { background: #f1f0f5; color: #77758b; }
.tp-scope-summary-hint {
    margin-top: 5px;
    color: #9290a2;
    font-size: 0.75rem;
}

/* 测试点列表：与需求列表保持一致的表格行样式。 */
.tp-list-wrap {
    width: 100%;
    overflow-x: auto;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    background: #FFFFFF;
}
.tp-list-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    table-layout: fixed;
    color: #303133;
    font-size: 13px;
}
.tp-list-table thead th {
    height: 42px;
    padding: 0 14px;
    text-align: left;
    white-space: nowrap;
    color: #606266;
    background: #F5F7FA;
    border-bottom: 1px solid #E4E7ED;
    font-weight: 600;
}
.tp-list-table tbody td {
    height: 48px;
    padding: 7px 14px;
    border-bottom: 1px solid #EBEEF5;
    vertical-align: middle;
    background: #FFFFFF;
    overflow-wrap: anywhere;
}
.tp-list-table tbody tr:last-child td { border-bottom: 0; }
.tp-list-table tbody tr:hover td { background: #F8FAFD; }
.tp-list-table th:nth-child(1), .tp-list-table td:nth-child(1) { width: 15%; }
.tp-list-table th:nth-child(2), .tp-list-table td:nth-child(2) { width: 43%; }
.tp-list-table th:nth-child(3), .tp-list-table td:nth-child(3) { width: 14%; }
.tp-list-table th:nth-child(4), .tp-list-table td:nth-child(4) { width: 14%; }
.tp-list-table th:nth-child(5), .tp-list-table td:nth-child(5) { width: 14%; }
.tp-list-tag {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 3px;
    font-size: 12px;
    line-height: 18px;
    white-space: nowrap;
}
.tp-list-tag-success { color: #67C23A; background: #F0F9EB; }
.tp-list-tag-warning { color: #E6A23C; background: #FDF6EC; }
.tp-list-tag-danger { color: #F56C6C; background: #FEF0F0; }
.tp-list-tag-neutral { color: #909399; background: #F4F4F5; }
.tp-list-id { color: #606266; white-space: nowrap; }
@media (max-width: 640px) {
    .tp-list-table { min-width: 760px; }
}

</style>
""")


# ============================================================
# 页面 Header
# ============================================================

render_header(
    title="测试点列表",
    description="按需求文档版本统一查看和维护 AI 生成的测试点，支持人工编辑、单条审核和批量审核。",
    breadcrumb=["测试点列表"],
)


st.html("""
<div class="tp-page-intro">
    先选择项目、需求文档及版本，再查看该版本下的测试点、审核状态和操作历史。
</div>
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


@st.dialog("人工编辑测试点", width="large")
def render_edit_dialog(test_point):
    """在弹窗中复用现有的人工编辑表单。"""
    st.caption(
        f"测试点编号：{test_point.get('point_id') or test_point.get('id')}"
    )
    render_edit_form(test_point)


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
# 1. 项目、需求文档及版本选择
# ============================================================

navigation_context = st.session_state.pop("test_point_context", None) or {}

try:
    projects = list_projects()
except Exception as exc:
    st.error(f"读取项目列表失败：{exc}")
    st.stop()

if not projects:
    st.warning("当前没有可用项目，请先创建项目。")
    st.stop()

project_options = {
    str(project["id"]): project
    for project in projects
}

context_project_id = str(navigation_context.get("project_id") or "")
if context_project_id in project_options:
    st.session_state["test_point_list_page_project"] = context_project_id

if st.session_state.get("test_point_list_page_project") not in project_options:
    st.session_state["test_point_list_page_project"] = next(iter(project_options))

# 保留当前查看范围摘要卡片，范围沿用页面状态或页面跳转上下文。
context_project_id = str(navigation_context.get("project_id") or "")
selected_project_id = (
    context_project_id
    if context_project_id in project_options
    else str(st.session_state.get("test_point_list_page_project") or "")
)
if selected_project_id not in project_options:
    selected_project_id = next(iter(project_options))
st.session_state["test_point_list_page_project"] = selected_project_id

selected_project = project_options[selected_project_id]

try:
    documents = list_documents(
        project_id=selected_project_id,
        include_deleted=True,
    )
except Exception as exc:
    st.error(f"读取需求文档失败：{exc}")
    st.stop()

if not documents:
    st.info("当前项目暂无需求文档，请先在需求中心创建或导入需求文档。")
    st.stop()

# 默认不展示已删除版本；若从需求详情页明确进入某个已删除版本，则保留该版本。
context_document_id = str(navigation_context.get("document_id") or "")
documents = [
    document for document in documents
    if not document.get("is_deleted")
    or str(document.get("id")) == context_document_id
]

documents_by_key = {}
for document in documents:
    document_key = str(document.get("document_key") or document.get("id"))
    documents_by_key.setdefault(document_key, []).append(document)

document_keys = list(documents_by_key.keys())
context_document = next(
    (
        document for document in documents
        if str(document.get("id")) == context_document_id
    ),
    None,
)
if context_document_id and not context_document:
    st.error("无法定位需求详情页选中的文档版本，请返回需求详情页重新进入。")
    st.stop()

document_key_widget = "test_point_list_page_document_key"
context_document_key = (
    str(context_document.get("document_key") or context_document.get("id"))
    if context_document else ""
)
selected_document_key = (
    context_document_key
    if context_document_key in documents_by_key
    else str(st.session_state.get(document_key_widget) or "")
)
if selected_document_key not in documents_by_key:
    selected_document_key = document_keys[0]
st.session_state[document_key_widget] = selected_document_key

version_options = {
    str(document["id"]): document
    for document in documents_by_key[selected_document_key]
}

# 当前需求没有有效版本时，不回退展示历史版本的测试点。
has_active_version = any(
    document.get("is_active")
    for document in version_options.values()
)
if not has_active_version:
    st.info("当前无有效需求版本的测试点可查看。")
    st.stop()

version_widget_key = (
    f"test_point_list_page_version_{selected_project_id}_{selected_document_key}"
)
saved_version_id = (
    context_document_id
    if context_document_id in version_options
    else str(st.session_state.get(version_widget_key) or "")
)
if saved_version_id not in version_options:
    active_version_id = next(
        (
            document_id for document_id, document in version_options.items()
            if document.get("is_active")
        ),
        None,
    )
    saved_version_id = active_version_id or next(iter(version_options))
selected_document_id = saved_version_id
st.session_state[version_widget_key] = selected_document_id

selected_document = version_options[selected_document_id]

project_name = html.escape(str(
    selected_project.get("project_name")
    or selected_project.get("name")
    or "未命名项目"
))
document_name = html.escape(str(
    selected_document.get("document_name") or "未命名文档"
))
version_label = html.escape(
    f"V{selected_document.get('version', '?')}"
)
active_label = (
    '<span class="tp-scope-active">当前有效版本</span>'
    if selected_document.get("is_active")
    else '<span class="tp-scope-history">历史版本</span>'
)
st.html(f"""
<div class="tp-scope-summary">
    <div class="tp-scope-summary-label">当前查看范围</div>
    <div class="tp-scope-summary-value">
        <span>{project_name}</span>
        <span class="tp-scope-separator">/</span>
        <span>{document_name}</span>
        <span class="tp-scope-version">{version_label}</span>
        {active_label}
    </div>
    <div class="tp-scope-summary-hint">测试点统计、审核和列表内容均限定在此需求文档版本内</div>
</div>
""")

# ============================================================
# 2. 查询当前需求版本的全部测试点
# ============================================================

try:
    all_document_points = list_test_points_by_document_version(
        project_id=selected_project_id,
        document_id=selected_document_id,
        include_deleted=True,
    )
except Exception as exc:
    st.error(f"读取当前需求版本测试点失败：{exc}")
    st.stop()

statistics = calculate_statistics(all_document_points)

# 批量审核服务要求同一次操作中的测试点属于同一个生成批次，
# 因此将当前需求版本的测试点按 batch_id 分组，分别提供批量审核入口。
document_batch_points = {}
for point in all_document_points:
    document_batch_points.setdefault(point.get("batch_id"), []).append(point)

if statistics["other"] > 0:
    st.warning(
        f"发现 {statistics['other']} 条其他人工审核状态的测试点，"
        "请检查数据库中的 manual_review_status。"
    )

metric_cols = st.columns(4, gap="small")
for col, label, value in zip(
    metric_cols,
    ("测试点总数", "待审核", "已通过", "已驳回"),
    ("total", "pending", "approved", "rejected"),
):
    with col:
        col.metric(label, statistics.get(value, 0))


# ============================================================
# 5. 测试点筛选
# ============================================================

st.divider()
st.subheader("测试点列表")

with st.container(border=True):
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        include_deleted = st.checkbox(
            "显示已逻辑删除的测试点",
            value=False,
            key=f"test_point_include_deleted_{selected_document_id}",
        )

    with filter_col2:
        status_options = {
            "全部": None,
            "待审核": "pending",
            "已通过": "approved",
            "已驳回": "rejected",
        }

        selected_status_label = st.selectbox(
            "人工审核状态筛选",
            options=list(status_options.keys()),
            key=f"test_point_status_filter_{selected_document_id}",
        )

selected_status = status_options[
    selected_status_label
]


try:
    test_points = list_test_points_by_document_version(
        project_id=selected_project_id,
        document_id=selected_document_id,
        include_deleted=include_deleted,
        manual_review_status=selected_status,
    )

except Exception as exc:
    st.error(f"读取测试点列表失败：{exc}")
    st.stop()


for batch_id, batch_points in document_batch_points.items():
    pending_batch_points = [
        point for point in batch_points
        if not point.get("is_deleted")
        and point.get("manual_review_status") == "pending"
    ]
    if not pending_batch_points:
        continue

    with st.expander(
        f"批量人工审核 · 批次 {str(batch_id)[:8]}",
        expanded=False,
    ):
        render_batch_review_actions(
            batch_points,
            batch_id,
        )


st.caption(
    f"当前筛选结果：{len(test_points)} 条 | "
    f"当前需求版本有效总数：{statistics['total']} 条 | "
    f"已删除总数：{statistics['deleted']} 条"
)


if include_deleted:
    st.info("当前已开启逻辑删除记录展示。")


# ============================================================
# 6. 测试点列表展示
# ============================================================

if not test_points:
    st.info("当前筛选条件下没有测试点。")

else:
    # 使用透明按钮覆盖每条测试点的列表行，点击行内空白/内容区域展开或收起。
    st.html("""
    <style>
    .tp-list-header-cell {
        min-height: 42px;
        display: flex;
        align-items: center;
        padding: 0 10px;
        color: #606266;
        background: #F5F7FA;
        border-bottom: 1px solid #E4E7ED;
        font-size: 13px;
        font-weight: 600;
        white-space: nowrap;
    }
    .tp-list-row-cell {
        height: 48px;
        min-height: 48px;
        box-sizing: border-box;
        display: flex;
        align-items: center;
        padding: 7px 10px;
        color: #303133;
        font-size: 13px;
        overflow-wrap: anywhere;
    }
    /* Streamlit 会在相邻容器之间额外插入默认纵向间距；
       通过行容器负外边距抵消该间距，避免依赖不稳定的父级 DOM 选择器。 */
    [class*="st-key-tp-list-row-"] {
        margin-bottom: -1rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    [class*="st-key-tp-list-row-"] > div[data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    .tp-list-id-cell { color: #606266; white-space: nowrap; }
    .tp-list-expand-arrow {
        display: inline-block;
        width: 18px;
        color: #909399;
        font-size: 12px;
        text-align: center;
        margin-right: 4px;
    }
    [class*="st-key-tp-list-row-"] {
        position: relative;
        border-bottom: 1px solid #EBEEF5;
        background: #FFFFFF;
        padding: 0 2px;
    }
    [class*="st-key-tp-list-row-"]:hover {
        background: #F8FAFD;
    }
    [class*="st-key-tp-list-row-"] [data-testid="stHorizontalBlock"] {
        align-items: center;
        gap: 0.35rem;
        position: relative;
        z-index: 1;
        pointer-events: none;
    }
    /* 透明点击层只覆盖列表行，不覆盖下方展开内容。 */
    [class*="st-key-tp-list-row-"] [class*="st-key-expand-test-point-"] {
        position: absolute !important;
        top: 0;
        left: 0;
        right: 0;
        height: 48px;
        z-index: 2;
        pointer-events: auto;
    }
    [class*="st-key-tp-list-row-"] [class*="st-key-expand-test-point-"] button {
        width: 100%;
        min-height: 48px;
        height: 48px;
        padding: 0;
        opacity: 0;
        border: 0;
        background: transparent;
        box-shadow: none;
        cursor: pointer;
    }
    /* 编辑按钮位于透明点击层上方，避免展开层影响编辑操作。 */
    [class*="st-key-tp-list-row-"] [class*="st-key-open_edit_test_point_"],
    [class*="st-key-tp-list-row-"] [class*="st-key-edit_test_point_disabled_"] {
        position: relative;
        z-index: 3;
        pointer-events: auto;
    }
    [class*="st-key-tp-list-row-"] [data-testid="stButton"] button:not([kind="secondary"]) {
        min-height: 30px;
        padding: 0 10px;
        font-size: 12px;
    }
    </style>
    """)

    header_cols = st.columns([15, 39, 14, 14, 9, 9], gap="small")
    for col, label in zip(
        header_cols,
        ("测试点编号", "测试点名称", "人工审核状态", "AI审核状态", "逻辑删除", "编辑"),
    ):
        with col:
            st.html(f'<div class="tp-list-header-cell">{label}</div>')

    expanded_test_point_id = st.session_state.get("expanded_test_point_id")

    for point in test_points:
        point_internal_id = point.get("id")
        point_id = html.escape(str(point.get("point_id") or "未知编号"))
        point_title = html.escape(str(get_point_title(point)))
        manual_status = point.get("manual_review_status", "未知")
        manual_status_label = {
            "pending": "待审核",
            "approved": "已通过",
            "rejected": "已驳回",
        }.get(manual_status, str(manual_status))
        ai_status = html.escape(str(point.get("ai_review_status") or "未知"))
        is_deleted = bool(point.get("is_deleted"))

        manual_status_class = {
            "pending": "tp-list-tag-warning",
            "approved": "tp-list-tag-success",
            "rejected": "tp-list-tag-danger",
        }.get(manual_status, "tp-list-tag-neutral")
        deleted_label = "是" if is_deleted else "否"
        deleted_class = "tp-list-tag-danger" if is_deleted else "tp-list-tag-neutral"
        is_expanded = expanded_test_point_id == point_internal_id
        arrow = "▾" if is_expanded else "▸"

        with st.container(key=f"tp-list-row-{point_internal_id}"):
            if st.button(
                "展开/收起测试点内容",
                key=f"expand-test-point-{point_internal_id}",
                help="点击此行展开或收起测试点内容",
                width="stretch",
            ):
                if is_expanded:
                    st.session_state.pop("expanded_test_point_id", None)
                else:
                    st.session_state["expanded_test_point_id"] = point_internal_id
                st.rerun()

            row_cols = st.columns([15, 39, 14, 14, 9, 9], gap="small")
            with row_cols[0]:
                st.html(
                    f'<div class="tp-list-row-cell tp-list-id-cell">'
                    f'<span class="tp-list-expand-arrow">{arrow}</span>{point_id}</div>'
                )
            with row_cols[1]:
                st.html(f'<div class="tp-list-row-cell">{point_title}</div>')
            with row_cols[2]:
                st.html(
                    f'<div class="tp-list-row-cell"><span class="tp-list-tag {manual_status_class}">'
                    f'{html.escape(manual_status_label)}</span></div>'
                )
            with row_cols[3]:
                st.html(f'<div class="tp-list-row-cell">{ai_status}</div>')
            with row_cols[4]:
                st.html(
                    f'<div class="tp-list-row-cell"><span class="tp-list-tag {deleted_class}">'
                    f'{deleted_label}</span></div>'
                )
            with row_cols[5]:
                if is_deleted:
                    st.button(
                        "编辑",
                        key=f"edit_test_point_disabled_{point_internal_id}",
                        disabled=True,
                        width="stretch",
                        help="已逻辑删除的测试点不能直接编辑",
                    )
                elif st.button(
                    "编辑",
                    key=f"open_edit_test_point_{point_internal_id}",
                    width="stretch",
                    help="编辑当前测试点",
                ):
                    render_edit_dialog(point)

            if is_expanded:
                with st.container(border=True):
                    info_col, review_col = st.columns(2)

                    with info_col:
                        st.subheader("基本信息")
                        st.write("内部 ID：", point.get("id"))
                        st.write("测试点编号：", point.get("point_id"))
                        st.write("所属批次：", point.get("batch_id"))
                        st.write(
                            "创建时间：",
                            format_local_datetime(point.get("created_at")),
                        )
                        st.write(
                            "更新时间：",
                            format_local_datetime(point.get("updated_at")),
                        )

                    with review_col:
                        st.subheader("审核信息")
                        st.write(
                            "AI 审核状态：",
                            point.get("ai_review_status", "未知"),
                        )
                        st.write(
                            "人工审核状态：",
                            point.get("manual_review_status", "未知"),
                        )
                        st.write(
                            "人工审核意见 / 驳回原因：",
                            point.get("manual_comment") or "暂无",
                        )
                        st.write(
                            "审核时间：",
                            format_local_datetime(point.get("reviewed_at")),
                        )

                    st.divider()
                    show_content(
                        "测试点内容",
                        point.get("current_content"),
                    )


# ============================================================
# 7. 测试点详情
# ============================================================

st.divider()
st.subheader("测试点详情")

if not test_points:
    st.info("没有可供查看详情的测试点。")

else:
    test_point_options = {
        point["id"]: point
        for point in test_points
    }

    selected_test_point_id = st.selectbox(
        "选择要查看的测试点",
        options=list(test_point_options.keys()),
        format_func=lambda x: format_test_point(
            test_point_options[x]
        ),
        key=f"test_point_detail_selection_{selected_document_id}",
    )

    try:
        test_point = get_test_point(
            selected_test_point_id
        )

    except Exception as exc:
        st.error(f"读取测试点详情失败：{exc}")
        st.stop()

    if not test_point:
        st.error("无法读取测试点详情。")

    else:
        # ----------------------------------------------------
        # 删除状态
        # ----------------------------------------------------

        if test_point.get("is_deleted"):
            st.warning(
                "该测试点已逻辑删除。"
                f"删除时间："
                f"{format_local_datetime(test_point.get('deleted_at'))}"
            )

        # ----------------------------------------------------
        # 单条人工审核
        # ----------------------------------------------------

        st.divider()

        with st.container(border=True):
            render_single_review_actions(test_point)

        # ----------------------------------------------------
        # 当前内容
        # ----------------------------------------------------

        with st.container(border=True):
            show_content(
                "当前测试点内容",
                test_point.get("current_content"),
            )

        # ----------------------------------------------------
        # 操作历史
        # ----------------------------------------------------

        with st.container(border=True):
            render_test_point_history(
                test_point["id"]
            )

        # ----------------------------------------------------
        # 原始内容
        # ----------------------------------------------------

        with st.expander("查看原始测试点内容"):
            show_content(
                "原始测试点内容",
                test_point.get("original_content"),
            )

        # ----------------------------------------------------
        # 完整数据库记录
        # ----------------------------------------------------

        with st.expander("查看完整数据库记录"):
            st.json(
                test_point,
                expanded=True,
            )


# ============================================================
# 8. 页面说明
# ============================================================

st.divider()

st.info(
    "当前页面支持测试点查看、人工编辑、单条人工审核和批量人工审核。"
    "人工审核独立于 AI 审核状态；编辑成功后人工审核状态重置为 pending，"
    "AI 审核状态保持不变。"
)
