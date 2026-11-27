
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
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell {position:relative!important;height:132px!important;min-height:132px!important;max-height:132px!important;box-sizing:border-box;overflow:visible!important;background:#fff!important;border:1px solid #E7EAF1!important;border-radius:12px!important;padding:12px 18px!important;box-shadow:0 2px 8px rgba(23,32,51,.04);transition:border-color .15s,box-shadow .15s;}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell:hover {border-color:#C9C4E8!important;box-shadow:0 3px 10px rgba(23,32,51,.06);}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell::after {content:"⌄";position:absolute;right:16px;bottom:12px;z-index:3;color:#8490A3;font-size:20px;line-height:1;font-weight:600;pointer-events:none;}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell [data-testid="stPopover"] {position:static!important;z-index:2!important;}
div[data-testid="stVerticalBlock"].st-key-test_point_project_picker_shell [data-testid="stPopover"] button[aria-haspopup="dialog"] {position:absolute!important;inset:0!important;z-index:5!important;display:block!important;width:100%!important;height:132px!important;min-height:132px!important;max-height:132px!important;max-width:none!important;margin:0!important;padding:0!important;opacity:0!important;color:transparent!important;background:transparent!important;border:0!important;box-shadow:none!important;cursor:pointer!important;}

</style>
""")


# ============================================================
# 页面 Header
# ============================================================

render_header(
    title="测试点中心",
    description="统一查看、筛选和维护 AI 生成的游戏测试点，支持人工编辑、单条审核和批量审核。",
    breadcrumb=["测试点中心"],
)


st.html("""
<div class="tp-page-intro">
    集中管理测试点记录，跟踪 AI 审核与人工审核状态，并保留完整操作历史。
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
    st.session_state["test_point_center_project"] = context_project_id

if st.session_state.get("test_point_center_project") not in project_options:
    st.session_state["test_point_center_project"] = next(iter(project_options))

selected_project_id = st.selectbox(
    "所属项目",
    options=list(project_options.keys()),
    format_func=lambda value: (
        project_options[value].get("project_name")
        or project_options[value].get("name")
        or "未命名项目"
    ),
    key="test_point_center_project",
)
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

# 侧边栏入口默认不展示已删除版本；若从需求详情页明确进入某个已删除版本，
# 则保留该版本，避免静默回退到其他版本。
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
context_document_id = str(navigation_context.get("document_id") or "")
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

if context_document:
    context_document_key = str(
        context_document.get("document_key") or context_document.get("id")
    )
    st.session_state["test_point_center_document_key"] = context_document_key

document_key_widget = "test_point_center_document_key"
if st.session_state.get(document_key_widget) not in documents_by_key:
    st.session_state[document_key_widget] = document_keys[0]

selected_document_key = st.selectbox(
    "需求文档",
    options=document_keys,
    format_func=lambda value: (
        documents_by_key[value][0].get("document_name")
        or value
    ),
    key=document_key_widget,
)

version_options = {
    str(document["id"]): document
    for document in documents_by_key[selected_document_key]
}
if (
    context_document
    and str(context_document.get("document_key") or context_document.get("id"))
    == selected_document_key
    and context_document_id in version_options
):
    st.session_state[
        f"test_point_center_version_{selected_project_id}_{selected_document_key}"
    ] = context_document_id

version_widget_key = (
    f"test_point_center_version_{selected_project_id}_{selected_document_key}"
)
if st.session_state.get(version_widget_key) not in version_options:
    active_version_id = next(
        (
            document_id for document_id, document in version_options.items()
            if document.get("is_active")
        ),
        None,
    )
    st.session_state[version_widget_key] = (
        active_version_id or next(iter(version_options))
    )

selected_document_id = st.selectbox(
    "需求文档版本",
    options=list(version_options.keys()),
    format_func=lambda value: (
        f"V{version_options[value].get('version', '?')}"
        f"{'（当前有效）' if version_options[value].get('is_active') else ''}"
        f" · {version_options[value].get('document_name') or '未命名文档'}"
    ),
    key=version_widget_key,
)
selected_document = version_options[selected_document_id]

project_name = html.escape(str(
    selected_project.get("project_name")
    or selected_project.get("name")
    or "未命名项目"
))
document_name = html.escape(str(
    selected_document.get("document_name") or "未命名文档"
))
st.caption(
    f"当前范围：{project_name} / {document_name} / "
    f"V{selected_document.get('version', '?')}。"
    "仅展示当前选中版本关联的测试点。"
)


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
    f"批次有效总数：{statistics['total']} 条 | "
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
    st.subheader("测试点记录")

    for index, point in enumerate(test_points, start=1):
        point_id = point.get(
            "point_id",
            "未知编号",
        )

        point_title = get_point_title(point)

        status = point.get("manual_review_status", "未知")
        status_label = {"pending":"待审核", "approved":"已通过", "rejected":"已驳回"}.get(status, status)
        with st.container(border=True):
            st.markdown(f'<div class="tp-record-title">{point_title}<span class="tp-pill {status}">{status_label}</span></div><div class="tp-record-meta">{point_id} · AI审核：{point.get("ai_review_status", "未知")}</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)

            col1.write(
                f"AI审核状态："
                f"{point.get('ai_review_status', '未知')}"
            )

            col2.write(
                f"人工审核状态：{status_label}"
            )

            col3.write(
                f"逻辑删除："
                f"{'是' if point.get('is_deleted') else '否'}"
            )

            st.caption(f"内部 ID：{point.get('id', '')}")


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
        # 基本信息和审核信息
        # ----------------------------------------------------

        with st.container(border=True):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("基本信息")

                st.write(
                    "内部 ID：",
                    test_point.get("id"),
                )

                st.write(
                    "测试点编号：",
                    test_point.get("point_id"),
                )

                st.write(
                    "所属批次：",
                    test_point.get("batch_id"),
                )

                st.write(
                    "创建时间：",
                    format_local_datetime(
                        test_point.get("created_at")
                    ),
                )

                st.write(
                    "更新时间：",
                    format_local_datetime(
                        test_point.get("updated_at")
                    ),
                )

            with col2:
                st.subheader("审核信息")

                st.write(
                    "AI 审核状态：",
                    test_point.get(
                        "ai_review_status",
                        "未知",
                    ),
                )

                st.write(
                    "人工审核状态：",
                    test_point.get(
                        "manual_review_status",
                        "未知",
                    ),
                )

                st.write(
                    "人工审核意见 / 驳回原因：",
                    test_point.get("manual_comment") or "暂无",
                )

                st.write(
                    "审核时间：",
                    format_local_datetime(
                        test_point.get("reviewed_at")
                    ),
                )

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
        # 人工编辑
        # ----------------------------------------------------

        st.divider()

        with st.container(border=True):
            st.subheader("人工编辑测试点")
            render_edit_form(test_point)

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
