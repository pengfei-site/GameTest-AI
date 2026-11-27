
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
    soft_delete_test_point,
    restore_test_point,
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
/* 当前查看范围卡片：沿用需求版本管理中需求文档卡片的视觉样式。 */
.tp-scope-summary {
    margin: 7px 0;
    padding: 10px 12px;
    border: 1px solid #E8EAF2;
    border-radius: 10px;
    background: #FFFFFF;
}
.tp-scope-summary-label {
    color: #172033;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
}
.tp-scope-summary-value {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 7px;
    color: #172033;
    font-size: 13px;
    font-weight: 700;
}
.tp-scope-separator { color: #8490A3; font-weight: 400; }
.tp-scope-version {
    padding: 2px 8px;
    border-radius: 6px;
    background: #F3F5F9;
    color: #64748B;
    font-size: 11px;
    font-weight: 500;
}
.tp-scope-active, .tp-scope-history {
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
}
.tp-scope-active { background: #F0F9EB; color: #67C23A; }
.tp-scope-history { background: #F1F5F9; color: #64748B; }
.tp-scope-summary-hint {
    margin-top: 4px;
    color: #8490A3;
    font-size: 11px;
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

delete_success_message = st.session_state.pop(
    "test_point_delete_success_message",
    None,
)
if delete_success_message:
    st.success(delete_success_message)

restore_success_message = st.session_state.pop(
    "test_point_restore_success_message",
    None,
)
if restore_success_message:
    st.success(restore_success_message)

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

def render_test_point_meta_cards(point):
    """紧凑展示测试点基本信息与审核信息。"""

    def safe_text(value, fallback="暂无"):
        if value is None or not str(value).strip():
            return fallback
        return html.escape(str(value))

    def status_pill(value):
        raw = str(value or "").strip()
        labels = {
            "pending": "待审核",
            "approved": "已通过",
            "rejected": "已驳回",
        }
        css_class = {
            "pending": "pending",
            "approved": "approved",
            "rejected": "rejected",
        }.get(raw, "neutral")
        label = labels.get(raw, raw or "未知")
        return (
            f'<span class="tp-meta-status {css_class}">'
            f'{html.escape(label)}</span>'
        )

    basic_items = [
        ("内部 ID", point.get("id")),
        ("测试点编号", point.get("point_id")),
        ("所属批次", point.get("batch_id")),
        ("创建时间", format_local_datetime(point.get("created_at"))),
        ("更新时间", format_local_datetime(point.get("updated_at"))),
    ]
    basic_html = "".join(
        f'<div class="tp-meta-item">'
        f'<div class="tp-meta-label">{label}</div>'
        f'<div class="tp-meta-value">{safe_text(value)}</div>'
        f'</div>'
        for label, value in basic_items
    )

    comment = safe_text(point.get("manual_comment"))
    reviewed_at = safe_text(
        format_local_datetime(point.get("reviewed_at"))
    )
    ai_status = status_pill(point.get("ai_review_status"))
    manual_status = status_pill(point.get("manual_review_status"))

    st.html(f"""
    <style>
    .tp-meta-card {{
        height: 100%;
        box-sizing: border-box;
        padding: 13px 15px;
        border: 1px solid #E8E6F0;
        border-radius: 9px;
        background: #FFFFFF;
        color: #303133;
    }}
    .tp-meta-card-title {{
        margin: 0 0 11px;
        color: #302B50;
        font-size: 14px;
        line-height: 1.4;
        font-weight: 700;
    }}
    .tp-meta-grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px 14px;
    }}
    .tp-meta-item {{ min-width: 0; }}
    .tp-meta-label {{
        margin-bottom: 3px;
        color: #858298;
        font-size: 11px;
        line-height: 1.4;
    }}
    .tp-meta-value {{
        color: #302D43;
        font-size: 12px;
        line-height: 1.5;
        font-weight: 600;
        overflow-wrap: anywhere;
        word-break: break-word;
    }}
    .tp-meta-status-row {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        margin-bottom: 11px;
    }}
    .tp-meta-status-block {{
        min-width: 0;
        padding: 8px 9px;
        border-radius: 7px;
        background: #F7F7FA;
    }}
    .tp-meta-status {{
        display: inline-block;
        max-width: 100%;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 11px;
        line-height: 1.5;
        font-weight: 650;
        overflow-wrap: anywhere;
    }}
    .tp-meta-status.pending {{ color: #A66A00; background: #FFF3D6; }}
    .tp-meta-status.approved {{ color: #18794E; background: #E6F6EE; }}
    .tp-meta-status.rejected {{ color: #A83232; background: #FDEAEA; }}
    .tp-meta-status.neutral {{ color: #77758B; background: #F0EFF4; }}
    .tp-meta-review-detail {{
        padding-top: 9px;
        margin-top: 9px;
        border-top: 1px solid #EEEFF2;
    }}
    @media (max-width: 640px) {{
        .tp-meta-grid {{ grid-template-columns: minmax(0, 1fr); }}
        .tp-meta-status-row {{ grid-template-columns: minmax(0, 1fr); }}
    }}
    </style>
    <div class="tp-meta-card">
        <div class="tp-meta-card-title">基本信息</div>
        <div class="tp-meta-grid">{basic_html}</div>
    </div>
    """)
    st.html(f"""
    <div class="tp-meta-card">
        <div class="tp-meta-card-title">审核信息</div>
        <div class="tp-meta-status-row">
            <div class="tp-meta-status-block">
                <div class="tp-meta-label">AI 审核状态</div>
                {ai_status}
            </div>
            <div class="tp-meta-status-block">
                <div class="tp-meta-label">人工审核状态</div>
                {manual_status}
            </div>
        </div>
        <div class="tp-meta-review-detail">
            <div class="tp-meta-label">人工审核意见 / 驳回原因</div>
            <div class="tp-meta-value">{comment}</div>
        </div>
        <div class="tp-meta-review-detail">
            <div class="tp-meta-label">审核时间</div>
            <div class="tp-meta-value">{reviewed_at}</div>
        </div>
    </div>
    """)

def render_structured_test_point_content(content, point_id):
    """以紧凑的结构化卡片展示测试点业务内容，不展示原始 JSON。"""

    if not isinstance(content, dict):
        content = {}

    category_labels = {
        "positive": "正向测试",
        "negative": "反向测试",
        "boundary": "边界测试",
        "exception": "异常测试",
        "state": "状态测试",
        "data": "数据测试",
    }

    def display_value(value):
        if value is None or not str(value).strip():
            return "暂无内容"
        return html.escape(str(value)).replace("\n", "<br>")

    category = str(content.get("category") or "").strip()
    priority = str(content.get("priority") or "").strip()
    category_label = category_labels.get(category, category or "未分类")
    priority_label = priority or "未设置"
    title = display_value(content.get("title"))
    objective = display_value(content.get("test_objective"))
    coverage = display_value(content.get("coverage_description"))
    source_rule = display_value(content.get("source_rule"))
    requirement_id = display_value(content.get("requirement_id"))
    safe_point_id = html.escape(str(point_id or "未知编号"))

    st.html(f"""
    <style>
    .tp-content-card {{
        color: #303133;
        font-size: 13px;
        line-height: 1.65;
    }}
    .tp-content-heading {{
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 7px;
        margin-bottom: 5px;
    }}
    .tp-content-tag {{
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        background: #EEF2FF;
        color: #5145A5;
        font-size: 11px;
        font-weight: 600;
    }}
    .tp-content-tag-priority {{
        background: #FFF4E5;
        color: #A15C00;
    }}
    .tp-content-id {{
        color: #909399;
        font-size: 11px;
    }}
    .tp-content-title {{
        color: #25243A;
        font-size: 17px;
        font-weight: 700;
        line-height: 1.45;
        overflow-wrap: anywhere;
        margin-bottom: 12px;
    }}
    .tp-content-section {{
        padding: 9px 11px;
        margin-top: 7px;
        border: 1px solid #ECEBF2;
        border-radius: 7px;
        background: #FFFFFF;
    }}
    .tp-content-section-label {{
        color: #77758B;
        font-size: 11px;
        font-weight: 650;
        margin-bottom: 3px;
    }}
    .tp-content-section-value {{
        color: #303133;
        overflow-wrap: anywhere;
        white-space: normal;
    }}
    .tp-content-footer {{
        display: flex;
        justify-content: flex-end;
        align-items: center;
        gap: 6px;
        padding-top: 9px;
        margin-top: 9px;
        border-top: 1px solid #ECEBF2;
        color: #77758B;
        font-size: 11px;
    }}
    .tp-content-footer strong {{
        color: #4B4860;
        font-weight: 600;
    }}
    </style>
    <div class="tp-content-card">
        <div class="tp-content-heading">
            <span class="tp-content-tag">{html.escape(category_label)}</span>
            <span class="tp-content-tag tp-content-tag-priority">{html.escape(priority_label)}</span>
            <span class="tp-content-id">{safe_point_id}</span>
        </div>
        <div class="tp-content-title">{title}</div>
        <div class="tp-content-section">
            <div class="tp-content-section-label">测试目标</div>
            <div class="tp-content-section-value">{objective}</div>
        </div>
        <div class="tp-content-section">
            <div class="tp-content-section-label">覆盖描述</div>
            <div class="tp-content-section-value">{coverage}</div>
        </div>
        <div class="tp-content-section">
            <div class="tp-content-section-label">来源规则</div>
            <div class="tp-content-section-value">{source_rule}</div>
        </div>
        <div class="tp-content-footer">
            <span>需求编号</span>
            <strong>{requirement_id}</strong>
        </div>
    </div>
    """)

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

@st.dialog("测试点操作历史", width="large")
def render_test_point_history_dialog(test_point_id, point_label):
    """在弹窗中展示单个测试点的操作历史及其数据快照。"""

    st.caption(f"测试点编号：{point_label}")
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

@st.dialog("确认逻辑删除测试点", width="small")
def render_delete_test_point_dialog(test_point_id, point_label):
    """确认后执行逻辑删除，并由 Repository 同步写入操作历史。"""

    st.warning(
        f"确定要逻辑删除测试点「{point_label}」吗？"
        "删除后该测试点将从默认列表中隐藏，但记录和操作历史会保留。"
    )

    if st.button(
        "确认删除",
        key=f"confirm_delete_test_point_{test_point_id}",
        type="primary",
        width="stretch",
    ):
        try:
            soft_delete_test_point(test_point_id)
        except Exception as exc:
            st.error(f"逻辑删除测试点失败：{exc}")
            return

        st.session_state["test_point_delete_success_message"] = (
            f"测试点 {point_label} 已逻辑删除，操作历史已保存。"
        )
        if st.session_state.get("expanded_test_point_id") == test_point_id:
            st.session_state.pop("expanded_test_point_id", None)
        st.rerun()


@st.dialog("确认恢复测试点", width="small")
def render_restore_test_point_dialog(test_point_id, point_label):
    """确认后恢复已逻辑删除的测试点，并由 Repository 同步写入操作历史。"""

    st.warning(
        f"确定要恢复测试点「{point_label}」吗？"
        "恢复后该测试点将重新出现在默认列表中，并保留原有内容和审核状态。"
    )

    if st.button(
        "确认恢复",
        key=f"confirm_restore_test_point_{test_point_id}",
        type="primary",
        width="stretch",
    ):
        try:
            restore_test_point(test_point_id)
        except Exception as exc:
            st.error(f"恢复测试点失败：{exc}")
            return

        st.session_state["test_point_restore_success_message"] = (
            f"测试点 {point_label} 已恢复，操作历史已保存。"
        )
        st.rerun()


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
document_status = (
    "已删除" if selected_document.get("is_deleted")
    else ("有效" if selected_document.get("is_active") else "已废弃")
)
document_created_at = html.escape(str(
    format_local_datetime(selected_document.get("created_at")) or "暂无"
))

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

batch_count = len({
    str(point.get("batch_id"))
    for point in all_document_points
    if point.get("batch_id") not in (None, "")
})
st.html(f"""
<div class="tp-scope-summary">
    <div class="tp-scope-summary-value">
        <span>▤&nbsp;{document_name}</span>
    </div>
    <div class="tp-scope-summary-value">
        <span>所属项目：{project_name}</span>
        <span class="tp-scope-separator">·</span>
        <span class="tp-scope-version">{version_label}</span>
        <span class="tp-scope-separator">·</span>
        <span>版本状态：{document_status}</span>
        <span class="tp-scope-separator">·</span>
        <span>创建时间：{document_created_at}</span>
        <span class="tp-scope-separator">·</span>
        <span>测试点批次数：{batch_count} 个</span>
    </div>
</div>
""")

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

search_col, filter_col = st.columns(
    [12, 1],
    vertical_alignment="center",
    gap="small",
)
with search_col:
    test_point_search = st.text_input(
        "搜索测试点",
        placeholder="搜索测试点编号或名称…",
        key=f"test_point_list_search_{selected_document_id}",
        label_visibility="collapsed",
        width="stretch",
    )

status_options = {
    "全部": None,
    "待审核": "pending",
    "已通过": "approved",
    "已驳回": "rejected",
}
with filter_col:
    with st.popover(
        "筛选",
        icon=":material/filter_list:",
        help="筛选测试点",
        width="stretch",
    ):
        st.markdown("**人工审核状态**")
        selected_status_label = st.radio(
            "人工审核状态筛选",
            options=list(status_options.keys()),
            key=f"test_point_status_filter_v2_{selected_document_id}",
            label_visibility="collapsed",
        )

selected_status = status_options[selected_status_label]

include_deleted_key = f"test_point_include_deleted_{selected_document_id}"
include_deleted = bool(st.session_state.get(include_deleted_key, False))

try:
    test_points = list_test_points_by_document_version(
        project_id=selected_project_id,
        document_id=selected_document_id,
        include_deleted=include_deleted,
    )
except Exception as exc:
    st.error(f"读取测试点列表失败：{exc}")
    st.stop()

search_text = test_point_search.strip().lower()
filtered_test_points = []
for point in test_points:
    point_content = point.get("current_content") or {}
    point_name = get_point_title(point)
    point_id_text = str(point.get("point_id") or point.get("id") or "")
    matches_search = (
        not search_text
        or search_text in point_id_text.lower()
        or search_text in str(point_name).lower()
    )
    matches_status = (
        selected_status is None
        or point.get("manual_review_status") == selected_status
    )
    if matches_search and matches_status:
        filtered_test_points.append(point)

test_points = filtered_test_points

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

statistics_cols = st.columns([10.8, 1.2], vertical_alignment="center")
with statistics_cols[0]:
    st.caption(
        f"当前筛选结果：{len(test_points)} 条 | "
        f"当前需求版本有效总数：{statistics['total']} 条 | "
        f"已删除总数：{statistics['deleted']} 条"
    )
with statistics_cols[1]:
    st.checkbox(
        "显示已删除",
        key=include_deleted_key,
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
        /* 整行内容容器必须高于透明展开按钮；否则子级操作按钮的 z-index
           会被父级层叠上下文限制，无法真正覆盖透明点击层。 */
        z-index: 3;
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
    /* 操作列按钮整体提升到透明点击层上方，确保编辑、查看历史和删除均可点击。 */
    [class*="st-key-tp-list-row-"] [class*="st-key-open_edit_test_point_"],
    [class*="st-key-tp-list-row-"] [class*="st-key-edit_test_point_disabled_"],
    [class*="st-key-tp-list-row-"] [class*="st-key-open_test_point_history_"],
    [class*="st-key-tp-list-row-"] [class*="st-key-open_delete_test_point_"],
    [class*="st-key-tp-list-row-"] [class*="st-key-open_restore_test_point_"],
    [class*="st-key-tp-list-row-"] [class*="st-key-delete_test_point_disabled_"] {
        position: relative;
        z-index: 3;
        pointer-events: auto;
    }
    [class*="st-key-tp-list-row-"] [data-testid="stButton"] button:not([kind="secondary"]) {
        min-height: 30px;
        padding: 0 10px;
        font-size: 12px;
    }

    /* 删除与恢复属于危险/状态变更操作，统一使用红色按钮。 */
    [class*="st-key-tp-list-row-"] [class*="st-key-open_delete_test_point_"] [data-testid="stButton"] button,
    [class*="st-key-tp-list-row-"] [class*="st-key-open_restore_test_point_"] [data-testid="stButton"] button {
        color: #FFFFFF !important;
        background: #F56C6C !important;
        border-color: #F56C6C !important;
    }
    [class*="st-key-tp-list-row-"] [class*="st-key-open_delete_test_point_"] [data-testid="stButton"] button:hover,
    [class*="st-key-tp-list-row-"] [class*="st-key-open_restore_test_point_"] [data-testid="stButton"] button:hover {
        color: #FFFFFF !important;
        background: #F78989 !important;
        border-color: #F78989 !important;
    }
    [class*="st-key-tp-list-row-"] [class*="st-key-open_delete_test_point_"] [data-testid="stButton"] button:active,
    [class*="st-key-tp-list-row-"] [class*="st-key-open_restore_test_point_"] [data-testid="stButton"] button:active {
        background: #DD6161 !important;
        border-color: #DD6161 !important;
    }
    </style>
    """)

    header_cols = st.columns([14, 36, 14, 14, 22], gap="small")
    for col, label in zip(
        header_cols,
        ("测试点编号", "测试点名称", "人工审核状态", "AI审核状态", "操作"),
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

            row_cols = st.columns([14, 36, 14, 14, 22], gap="small")
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
                action_cols = st.columns(3, gap="small")
                with action_cols[0]:
                    if is_deleted:
                        st.button(
                            "编辑",
                            key=f"edit_test_point_disabled_{point_internal_id}",
                            disabled=True,
                            type="primary",
                            width="stretch",
                            help="已逻辑删除的测试点不能直接编辑",
                        )
                    elif st.button(
                        "编辑",
                        key=f"open_edit_test_point_{point_internal_id}",
                        type="primary",
                        width="stretch",
                        help="编辑当前测试点",
                    ):
                        render_edit_dialog(point)
                with action_cols[1]:
                    if st.button(
                        "查看历史",
                        key=f"open_test_point_history_{point_internal_id}",
                        type="primary",
                        width="stretch",
                        help="查看当前测试点的操作历史记录",
                    ):
                        render_test_point_history_dialog(
                            point_internal_id,
                            point.get("point_id") or point_internal_id,
                        )
                with action_cols[2]:
                    if is_deleted:
                        if st.button(
                            "恢复",
                            key=f"open_restore_test_point_{point_internal_id}",
                            type="primary",
                            width="stretch",
                            help="恢复当前已逻辑删除的测试点",
                        ):
                            render_restore_test_point_dialog(
                                point_internal_id,
                                point.get("point_id") or point_internal_id,
                            )
                    elif st.button(
                        "删除",
                        key=f"open_delete_test_point_{point_internal_id}",
                        type="primary",
                        width="stretch",
                        help="逻辑删除当前测试点，保留记录和操作历史",
                    ):
                        render_delete_test_point_dialog(
                            point_internal_id,
                            point.get("point_id") or point_internal_id,
                        )

            if is_expanded:
                with st.container(border=True):
                    render_structured_test_point_content(
                        point.get("current_content"),
                        point.get("point_id"),
                    )

                    st.divider()
                    render_test_point_meta_cards(point)
