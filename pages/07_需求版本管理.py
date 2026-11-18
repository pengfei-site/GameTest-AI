
import streamlit as st

from components.header import render_header
from core.time_utils import format_local_datetime

from database.repositories.project_repository import list_projects

from database.repositories.document_repository import (
    list_documents,
    get_document,
    soft_delete_document,
    restore_document,
)


# ============================================================
# 页面初始化
# ============================================================

render_header(
    title="需求版本管理",
    description="集中查看需求文档的历史版本，支持版本内容查看、逻辑删除和恢复。",
    breadcrumb=["需求中心", "需求版本管理"],
)


# ============================================================
# 一、选择项目
# ============================================================

st.subheader("一、选择项目")

try:
    projects = list_projects()
except Exception as e:
    st.error(f"项目列表加载失败：{e}")
    st.stop()

if not projects:
    st.info("当前没有可用项目，请先创建项目。")
    st.stop()

project_map = {
    project["id"]: project
    for project in projects
}

project_ids = list(project_map.keys())

selected_project_id = st.selectbox(
    "选择所属游戏项目",
    options=project_ids,
    format_func=lambda project_id: project_map[project_id]["name"],
    key="version_project_id",
)


# ============================================================
# 二、读取文档版本
# ============================================================

st.divider()
st.subheader("二、需求文档版本")

try:
    saved_documents = list_documents(
        project_id=selected_project_id,
        include_deleted=True,
    )
except Exception as e:
    st.error(f"需求文档版本加载失败：{e}")
    st.stop()


# ============================================================
# 三、操作消息
# ============================================================

action_message = st.session_state.pop(
    "document_version_action_message",
    None,
)

if action_message:
    st.success(action_message)


# ============================================================
# 四、版本统计
# ============================================================

if not saved_documents:
    st.info("当前项目还没有导入需求文档。")
    st.stop()


document_groups = {}

for document in saved_documents:
    key = document["document_key"]

    if key not in document_groups:
        document_groups[key] = []

    document_groups[key].append(document)


total_document_count = len(document_groups)
total_history_versions = len(saved_documents)

total_active_versions = sum(
    1
    for doc in saved_documents
    if not doc["is_deleted"]
)

col1, col2, col3 = st.columns(3)

col1.metric("需求文档数量", total_document_count)
col2.metric("有效版本数量", total_active_versions)
col3.metric("历史版本总数", total_history_versions)


# ============================================================
# 五、搜索与筛选
# ============================================================

st.divider()

col1, col2 = st.columns([2, 1])

with col1:
    search_keyword = st.text_input(
        "搜索文档名称或标识",
        placeholder="输入文档名称或 document_key",
        key="version_search_keyword",
    )

with col2:
    document_status_filter = st.selectbox(
        "版本显示范围",
        options=["有效版本", "全部版本"],
        key="version_status_filter",
    )


# ============================================================
# 六、整理展示数据
# ============================================================

filtered_groups = []

for key, all_versions in document_groups.items():

    active_versions = [
        doc for doc in all_versions
        if not doc["is_deleted"]
    ]

    latest = (
        active_versions[0]
        if active_versions
        else None
    )

    if document_status_filter == "有效版本":
        visible_versions = active_versions
    else:
        visible_versions = all_versions

    if not visible_versions:
        continue

    display_document = latest if latest else all_versions[0]

    keyword = search_keyword.strip().lower()

    document_name = display_document["document_name"].lower()

    if (
        not keyword
        or keyword in document_name
        or keyword in key.lower()
    ):
        filtered_groups.append(
            (
                key,
                visible_versions,
                all_versions,
                latest,
                display_document,
            )
        )


st.caption(
    f"当前项目共 {total_document_count} 份需求文档，"
    f"有效版本 {total_active_versions} 条，"
    f"历史版本总数 {total_history_versions} 条。"
)


# ============================================================
# 七、展示每份文档的版本历史
# ============================================================

if not filtered_groups:
    st.warning("没有找到符合条件的需求文档。")

else:

    for (
        key,
        versions,
        all_versions,
        latest,
        display_document,
    ) in filtered_groups:

        latest_label = (
            f"最新有效版本 V{latest['version']}"
            if latest
            else "暂无有效版本"
        )

        with st.expander(
            f"{display_document['document_name']}（{latest_label}）",
            key=f"version_expander_{key}",
        ):

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "最新有效版本",
                f"V{latest['version']}" if latest else "无",
            )

            col2.metric(
                "有效版本数",
                len([
                    doc for doc in all_versions
                    if not doc["is_deleted"]
                ]),
            )

            col3.metric(
                "历史版本总数",
                len(all_versions),
            )

            col4.metric(
                "文件类型",
                display_document["file_type"].upper(),
            )

            st.write(f"**文档标识：** `{key}`")
            st.write(f"**文档 ID：** `{display_document['id']}`")
            st.write(
                f"**创建时间：** "
                f"{format_local_datetime(display_document.get('created_at'))}"
            )

            st.markdown("#### 历史版本列表")

            version_options = {
                (
                    f"V{doc['version']}（"
                    f"{format_local_datetime(doc.get('created_at'))}）"
                    + (" [已删除]" if doc["is_deleted"] else "")
                ): doc["id"]
                for doc in versions
            }

            selected_version_label = st.selectbox(
                "选择要管理的文档版本",
                options=list(version_options.keys()),
                key=f"manage_version_{key}",
            )

            selected_version_id = version_options[
                selected_version_label
            ]

            selected_version_record = next(
                doc for doc in versions
                if doc["id"] == selected_version_id
            )

            st.divider()

            # ====================================================
            # 版本操作
            # ====================================================

            if not selected_version_record["is_deleted"]:

                confirm_delete = st.checkbox(
                    f"确认逻辑删除 V{selected_version_record['version']}？",
                    key=f"confirm_version_delete_{selected_version_id}",
                )

                if st.button(
                    "删除所选版本",
                    key=f"delete_version_{selected_version_id}",
                    type="secondary",
                    disabled=not confirm_delete,
                ):
                    try:
                        deleted = soft_delete_document(
                            selected_version_id
                        )

                        if deleted:
                            st.session_state[
                                "document_version_action_message"
                            ] = (
                                f"V{selected_version_record['version']} "
                                "已成功逻辑删除。"
                            )
                            st.rerun()
                        else:
                            st.warning(
                                "删除未生效，该版本可能已经被删除。"
                            )

                    except Exception as e:
                        st.error(f"删除文档版本失败：{e}")

            else:

                st.warning("该版本已逻辑删除。")

                if st.button(
                    f"恢复 V{selected_version_record['version']}",
                    key=f"restore_version_{selected_version_id}",
                    type="primary",
                ):
                    try:
                        restored = restore_document(
                            selected_version_id
                        )

                        if restored:
                            st.session_state[
                                "document_version_action_message"
                            ] = (
                                f"V{selected_version_record['version']} "
                                "已成功恢复。"
                            )
                            st.rerun()
                        else:
                            st.warning(
                                "恢复未生效，该版本可能已经恢复。"
                            )

                    except Exception as e:
                        st.error(f"恢复文档版本失败：{e}")

            # ====================================================
            # 查看版本内容
            # ====================================================

            if st.button(
                "查看该版本内容",
                key=f"view_version_{selected_version_id}",
            ):
                try:
                    selected_document = get_document(
                        selected_version_id
                    )

                    if selected_document is None:
                        st.error("未找到该文档版本。")
                    else:
                        st.session_state[
                            f"viewed_version_{key}"
                        ] = selected_document

                except Exception as e:
                    st.error(f"读取文档版本失败：{e}")

            viewed_document = st.session_state.get(
                f"viewed_version_{key}"
            )

            if (
                viewed_document is not None
                and viewed_document["id"] == selected_version_id
            ):
                st.divider()

                st.markdown(
                    f"#### 当前查看版本：V{viewed_document['version']}"
                )

                col1, col2 = st.columns(2)

                col1.metric(
                    "文件类型",
                    viewed_document["file_type"].upper(),
                )

                col2.metric(
                    "字符数量",
                    viewed_document["char_count"],
                )

                st.text_area(
                    "需求文档完整内容",
                    value=viewed_document["parsed_content"] or "",
                    height=350,
                    disabled=True,
                    key=f"version_content_{selected_version_id}",
                )


st.divider()
st.caption("GameTest AI · 需求版本管理")
