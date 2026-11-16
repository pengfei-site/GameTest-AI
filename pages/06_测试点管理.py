import streamlit as st
from pydantic import ValidationError

from database.repositories.project_repository import list_projects

from database.repositories.generation_batch_repository import (
    get_generation_batch,
    list_generation_batches,
)

from database.repositories.test_point_repository import (
    get_test_point,
    list_test_points,
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
# 页面配置
# ============================================================

st.set_page_config(
    page_title="测试点管理",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 测试点管理")
st.caption("查看、编辑测试点，以及管理 AI 和人工审核状态")


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

st.divider()


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

    # Repository 按 created_at ASC、rowid ASC 返回；页面反转后，
    # 最新操作显示在最上方，同时保留同一时间戳下的写入先后关系（新记录优先）。
    history_records = list(reversed(history_records))
    st.caption(f"共 {len(history_records)} 条历史记录，按操作时间倒序排列（最新记录在前）。")

    for index, record in enumerate(history_records, start=1):
        action_type = record.get("action_type") or "unknown"
        action_label = HISTORY_ACTION_LABELS.get(
            action_type, f"其他操作（{action_type}）"
        )
        created_at = format_local_datetime(record.get("created_at"))
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
            use_container_width=True,
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
        use_container_width=True,
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
        use_container_width=True,
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
        use_container_width=True,
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
        use_container_width=True,
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

projects = list_projects()

if not projects:
    st.warning("当前没有可用项目，请先创建项目。")
    st.stop()


project_options = {
    project["id"]: project
    for project in projects
}

selected_project_id = st.selectbox(
    "选择项目",
    options=list(project_options.keys()),
    format_func=lambda x: format_project(
        project_options[x]
    ),
)


# ============================================================
# 2. 批次选择
# ============================================================

batches = list_generation_batches(
    selected_project_id
)

if not batches:
    st.warning("当前项目暂无测试点生成批次。")
    st.stop()


batch_options = {
    batch["id"]: batch
    for batch in batches
}

selected_batch_id = st.selectbox(
    "选择测试点生成批次",
    options=list(batch_options.keys()),
    format_func=lambda x: format_batch(
        batch_options[x]
    ),
)


batch = get_generation_batch(
    selected_batch_id
)

if not batch:
    st.error("无法读取所选批次。")
    st.stop()


# ============================================================
# 3. 获取批次全部测试点并计算统计
# ============================================================

all_batch_points = list_test_points(
    selected_batch_id,
    include_deleted=True,
)

statistics = calculate_statistics(
    all_batch_points
)


# ============================================================
# 4. 测试点统计
# ============================================================

st.divider()
st.header("测试点统计")


col1, col2, col3 = st.columns(3)

col1.metric(
    "有效测试点总数",
    statistics["total"],
)

col2.metric(
    "待审核测试点",
    statistics["pending"],
)

col3.metric(
    "已删除测试点",
    statistics["deleted"],
)


stat_cols = st.columns(3)

stat_cols[0].metric(
    "已通过",
    statistics["approved"],
)

stat_cols[1].metric(
    "已驳回",
    statistics["rejected"],
)

stat_cols[2].metric(
    "其他状态",
    statistics["other"],
)


expected_total = (
    statistics["pending"]
    + statistics["approved"]
    + statistics["rejected"]
    + statistics["other"]
)

if statistics["total"] == expected_total:
    st.success("测试点统计数据校验通过。")
else:
    st.error(
        "测试点统计数据不一致，请检查测试点记录。"
    )


if statistics["other"] > 0:
    st.warning(
        f"发现 {statistics['other']} 条其他审核状态的测试点，"
        "请检查数据库中的 manual_review_status。"
    )


# ============================================================
# 5. 测试点筛选
# ============================================================

st.divider()
st.header("测试点列表")


filter_col1, filter_col2 = st.columns(2)


with filter_col1:
    include_deleted = st.checkbox(
        "显示已逻辑删除的测试点",
        value=False,
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
    )


selected_status = status_options[
    selected_status_label
]


test_points = list_test_points(
    selected_batch_id,
    include_deleted=include_deleted,
    manual_review_status=selected_status,
)


with st.expander("批量人工审核", expanded=False):
    render_batch_review_actions(
        all_batch_points,
        selected_batch_id,
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

    for index, point in enumerate(
        test_points,
        start=1,
    ):

        point_id = point.get(
            "point_id",
            "未知编号",
        )

        point_title = get_point_title(point)

        with st.expander(
            f"{index}. {point_id} — {point_title}",
            expanded=False,
        ):

            col1, col2, col3 = st.columns(3)

            col1.write(
                f"AI审核状态："
                f"{point.get('ai_review_status', '未知')}"
            )

            col2.write(
                f"人工审核状态："
                f"{point.get('manual_review_status', '未知')}"
            )

            col3.write(
                f"逻辑删除："
                f"{'是' if point.get('is_deleted') else '否'}"
            )

            st.caption(
                f"内部 ID：{point.get('id', '')}"
            )


# ============================================================
# 7. 测试点详情
# ============================================================

st.divider()
st.header("测试点详情")


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
    )


    test_point = get_test_point(
        selected_test_point_id
    )


    if not test_point:

        st.error("无法读取测试点详情。")

    else:

        # ----------------------------------------------------
        # 基本信息和审核信息
        # ----------------------------------------------------

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
        render_single_review_actions(test_point)


        # ----------------------------------------------------
        # 当前内容
        # ----------------------------------------------------

        show_content(
            "当前测试点内容",
            test_point.get("current_content"),
        )


        # ----------------------------------------------------
        # 人工编辑
        # ----------------------------------------------------

        st.divider()
        st.subheader("人工编辑测试点")

        render_edit_form(test_point)




        # ----------------------------------------------------
        # 操作历史
        # ----------------------------------------------------

        render_test_point_history(test_point["id"])

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
