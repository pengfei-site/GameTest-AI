
import hashlib

import streamlit as st

from core.document_parser import parse_document
from core.time_utils import format_local_datetime

from database.repositories.project_repository import list_projects
from database.repositories.document_repository import (
    create_document_version,
    get_document,
    list_documents,
    soft_delete_document,
    restore_document,
)

st.set_page_config(
    page_title="GameTest AI",
    page_icon="🎮",
    layout="wide"
)


# ============================================================
# 页面初始化
# ============================================================

st.title("🎮 GameTest AI")
st.caption("AI 驱动的游戏测试用例生成平台")

st.divider()


# ============================================================
# 加载项目列表
# ============================================================

st.subheader("项目概览")

try:
    projects = list_projects()
except Exception as e:
    st.error(f"项目列表加载失败：{e}")
    st.stop()

col1, col2, col3 = st.columns(3)

col1.metric("游戏项目", len(projects))
col2.metric("需求文档", 0)
col3.metric("测试用例", 0)

st.divider()


# ============================================================
# 需求文档导入
# ============================================================

st.subheader("📄 需求文档导入与解析")

if not projects:
    st.warning("当前没有可用的游戏项目，请先创建项目，再导入需求文档。")
    st.stop()


# ------------------------------------------------------------
# 1. 选择所属项目
# ------------------------------------------------------------

project_map = {
    project["id"]: project
    for project in projects
}

project_ids = list(project_map.keys())

selected_project_id = st.selectbox(
    "选择所属游戏项目",
    options=project_ids,
    format_func=lambda project_id: project_map[project_id]["name"],
    key="document_project_id"
)


# ============================================================
# 已导入需求文档列表
# ============================================================

st.subheader("📚 已导入需求文档")

try:

    # 版本状态筛选

    # 删除或恢复操作后，恢复当前文档的展开状态
    reopen_document_key = st.session_state.pop(
        "reopen_document_key",
        None,
    )

    if reopen_document_key:
        st.session_state[
            f"document_expander_{reopen_document_key}"
        ] = True

        # 确保被删除的版本仍然出现在版本选择列表中
        st.session_state["document_status_filter"] = "全部版本"

    document_status_filter = st.radio(
        "版本显示范围",
        options=["有效版本", "全部版本"],
        horizontal=True,
        key="document_status_filter",
    )

    # 始终查询全部版本，确保历史版本统计完整
    saved_documents = list_documents(
        project_id=selected_project_id,
        include_deleted=True,
    )

    action_message = st.session_state.pop(
        "document_action_message",
        None,
    )

    if action_message:
        st.success(action_message)

    if not saved_documents:
        st.info("当前项目还没有导入需求文档。")

    else:
        # 按 document_key 分组，保留全部历史版本
        document_groups = {}

        for document in saved_documents:
            key = document["document_key"]

            if key not in document_groups:
                document_groups[key] = []

            document_groups[key].append(document)

        search_keyword = st.text_input(
            "搜索文档名称或标识",
            placeholder="输入文档名称或 document_key",
            key="document_search_keyword",
        )

        filtered_groups = []

        # 全局统计
        total_document_count = len(document_groups)
        total_history_versions = len(saved_documents)

        total_active_versions = sum(
            1
            for doc in saved_documents
            if not doc["is_deleted"]
        )

        for key, all_versions in document_groups.items():

            # 只统计有效版本
            active_versions = [
                doc for doc in all_versions
                if not doc["is_deleted"]
            ]

            # 最新有效版本
            latest = (
                active_versions[0]
                if active_versions
                else None
            )

            # 根据显示模式决定展示哪些版本
            if document_status_filter == "有效版本":
                visible_versions = active_versions
            else:
                visible_versions = all_versions

            # 有效版本模式下，全部删除的文档不展示
            if not visible_versions:
                continue

            # 用于展示文档基础信息
            display_document = latest if latest else all_versions[0]

            keyword = search_keyword.strip().lower()

            if (
                not keyword
                or keyword in display_document["document_name"].lower()
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

        # 统计信息
        st.caption(
            f"当前项目共 {total_document_count} 份需求文档，"
            f"有效版本 {total_active_versions} 条，"
            f"历史版本总数 {total_history_versions} 条"
        )

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
                    key=f"document_expander_{key}",
                    on_change="rerun",
                ):

                    col1, col2, col3, col4 = st.columns(4)

                    col1.metric(
                        "最新有效版本",
                        f"V{latest['version']}" if latest else "无"
                    )

                    col2.metric(
                        "有效版本数",
                        len([
                            doc for doc in all_versions
                            if not doc["is_deleted"]
                        ])
                    )

                    col3.metric(
                        "历史版本总数",
                        len(all_versions)
                    )

                    col4.metric(
                        "文件类型",
                        display_document["file_type"].upper()
                    )

                    st.write(f"**文档标识：** `{key}`")
                    st.write(f"**文档 ID：** `{display_document['id']}`")
                    st.write(
                        f"**创建时间：** "
                        f"{format_local_datetime(display_document.get('created_at'))}"
                    )

                    st.write("**历史版本：**")

                    version_options = {
                        (
                            f"V{doc['version']}（"
                            f"{format_local_datetime(doc.get('created_at'))}）"
                            + (" [已删除]" if doc["is_deleted"] else "")
                        ): doc["id"]
                        for doc in versions
                    }

                    selected_version_label = st.selectbox(
                        "选择要查看的文档版本",
                        options=list(version_options.keys()),
                        key=f"document_version_{key}",
                    )

                    selected_version_id = version_options[selected_version_label]

                    # 获取当前选中的版本记录
                    selected_version_record = next(
                        doc for doc in versions
                        if doc["id"] == selected_version_id
                    )

                    # 已删除版本不显示删除操作
                    if not selected_version_record["is_deleted"]:

                        confirm_delete = st.checkbox(
                            f"确认删除 V{selected_version_record['version']}？",
                            key=f"confirm_delete_{selected_version_id}",
                        )

                        if st.button(
                            "删除所选版本",
                            key=f"delete_document_{selected_version_id}",
                            type="secondary",
                            disabled=not confirm_delete,
                        ):
                            try:
                                deleted = soft_delete_document(selected_version_id)

                                if deleted:
                                    st.session_state["document_action_message"] = (
                                        f"V{selected_version_record['version']} "
                                        "已成功逻辑删除。"
                                    )

                                    st.session_state["reopen_document_key"] = key
                                    st.session_state["expanded_document_key"] = key

                                    st.rerun()
                                else:
                                    st.warning("删除未生效，该版本可能已经被删除。")

                            except Exception as e:
                                st.error(f"删除文档版本失败：{e}")

                    else:
                        st.caption("该版本已逻辑删除。")

                        if st.button(
                            f"恢复 V{selected_version_record['version']}",
                            key=f"restore_document_{selected_version_id}",
                            type="primary",
                        ):
                            try:
                                restored = restore_document(selected_version_id)

                                if restored:
                                    st.session_state["document_action_message"] = (
                                        f"V{selected_version_record['version']} "
                                        "已成功恢复。"
                                    )

                                    st.session_state["reopen_document_key"] = key
                                    st.session_state["expanded_document_key"] = key
                                    st.rerun()

                                else:
                                    st.warning("恢复未生效，该版本可能已经恢复。")

                            except Exception as e:
                                st.error(f"恢复文档版本失败：{e}")

                    if st.button(
                        "查看该版本内容",
                        key=f"view_document_{selected_version_id}",
                    ):
                        try:
                            selected_document = get_document(selected_version_id)

                            if selected_document is None:
                                st.error("未找到该文档版本。")
                            else:
                                st.session_state[
                                    f"viewed_document_{key}"
                                ] = selected_document

                        except Exception as e:
                            st.error(f"读取文档版本失败：{e}")

                    # 显示已经选择的版本内容
                    viewed_document = st.session_state.get(
                        f"viewed_document_{key}"
                    )

                    if viewed_document is not None:
                        st.divider()

                        st.write(
                            f"**当前查看版本：V{viewed_document['version']}**"
                        )

                        st.write(
                            f"**文件类型：** {viewed_document['file_type'].upper()}"
                        )

                        st.write(
                            f"**字符数量：** {viewed_document['char_count']}"
                        )

                        st.text_area(
                            "需求文档完整内容",
                            value=viewed_document["parsed_content"] or "",
                            height=350,
                            disabled=True,
                            key=f"document_content_{key}",
                        )

except Exception as e:
    st.error(f"需求文档列表加载失败：{e}")


# ------------------------------------------------------------
# 2. 填写文档信息
# ------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    document_name = st.text_input(
        "文档名称",
        placeholder="例如：登录功能需求说明",
        key="document_name"
    )

with col2:
    document_key = st.text_input(
        "文档标识（document_key）",
        placeholder="例如：LOGIN_REQUIREMENT",
        key="document_key"
    )


# ------------------------------------------------------------
# 3. 上传文档
# ------------------------------------------------------------

uploaded_file = st.file_uploader(
    "上传游戏策划需求文档",
    type=["docx", "pdf", "md", "txt"],
    key="requirement_document"
)


# ============================================================
# 解析文档
# ============================================================

if uploaded_file is not None:

    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    st.write(f"文件名称：{uploaded_file.name}")

    if st.button("开始解析文档", type="primary"):

        # 每次重新解析时，清除之前的解析和保存状态
        st.session_state.pop("parsed_document", None)

        if not selected_project_id:
            st.error("请选择所属游戏项目")

        elif not document_name.strip():
            st.error("请输入文档名称")

        elif not document_key.strip():
            st.error("请输入文档标识")

        else:
            try:
                with st.spinner("正在解析文档..."):

                    result = parse_document(
                        uploaded_file.name,
                        file_bytes
                    )

                st.session_state["parsed_document"] = {
                    "project_id": selected_project_id,
                    "document_name": document_name.strip(),
                    "document_key": document_key.strip(),
                    "file_name": uploaded_file.name,
                    "file_hash": file_hash,
                    "result": result,
                    "saved_document": None
                }

                st.success("文档解析成功！")

            except Exception as e:
                st.error(f"文档解析失败：{e}")


# ============================================================
# 展示解析结果
# ============================================================

parsed_document = st.session_state.get("parsed_document")

is_current_parse = False

if parsed_document is not None and uploaded_file is not None:

    is_current_parse = (
        parsed_document["project_id"] == selected_project_id
        and parsed_document["document_name"] == document_name.strip()
        and parsed_document["document_key"] == document_key.strip()
        and parsed_document["file_hash"] == file_hash
    )

    if not is_current_parse:
        st.warning("项目、文档信息或上传文件已发生变化，请重新解析后再保存。")


if is_current_parse:

    result = parsed_document["result"]

    st.divider()
    st.success("文档解析成功！")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "文件类型",
        result["file_type"]
    )

    col2.metric(
        "文本字符数",
        result["char_count"]
    )

    col3.metric(
        "PDF页数",
        result["page_count"]
        if result["page_count"] is not None
        else "不适用"
    )

    st.subheader("文档内容预览")

    st.text_area(
        "解析结果",
        value=result["content"],
        height=400,
        disabled=True
    )

    # ========================================================
    # 保存文档
    # ========================================================

    st.divider()
    st.subheader("💾 保存需求文档")

    saved_document = parsed_document.get("saved_document")

    if saved_document is None:

        if st.button("保存到项目文档库", type="primary"):

            try:
                with st.spinner("正在保存文档..."):

                    created_document = create_document_version(
                        project_id=parsed_document["project_id"],
                        document_key=parsed_document["document_key"],
                        document_name=parsed_document["document_name"],
                        file_type=result["file_type"],
                        file_path=None,
                        parsed_content=result["content"],
                        file_hash=parsed_document["file_hash"],
                        page_count=result["page_count"],
                        char_count=result["char_count"]
                    )

                parsed_document["saved_document"] = created_document
                st.session_state["parsed_document"] = parsed_document

                st.success("需求文档保存成功！")

                saved_document = created_document

            except Exception as e:
                st.error(f"文档保存失败：{e}")

    # ========================================================
    # 展示保存结果
    # ========================================================

    if saved_document is not None:

        st.success("文档已成功保存到项目文档库！")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "文档版本",
            f"V{saved_document['version']}"
        )

        col2.metric(
            "文档类型",
            saved_document["file_type"].upper()
        )

        col3.metric(
            "字符数量",
            saved_document["char_count"]
        )

        st.write("**保存信息**")

        st.code(
            f"文档 ID：{saved_document['id']}\n"
            f"项目 ID：{saved_document['project_id']}\n"
            f"文档标识：{saved_document['document_key']}\n"
            f"文档名称：{saved_document['document_name']}\n"
            f"版本号：V{saved_document['version']}"
        )


# ============================================================
# 页面底部
# ============================================================

st.divider()

st.info("GameTest AI V0.1 | 需求文档导入与解析")

st.caption("Local Development | GameTest AI")
