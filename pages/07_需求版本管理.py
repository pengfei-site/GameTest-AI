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


render_header(
    title="需求版本管理",
    description="集中查看需求文档的历史版本，支持版本内容查看、逻辑删除和恢复。",
    breadcrumb=["需求中心", "需求版本管理"],
)

st.html("""
<style>
.gt-section { margin: 1.2rem 0 0.65rem 0; }
.gt-section-title { font-size: 1.05rem; font-weight: 700; color: #292746; }
.gt-section-desc { font-size: .84rem; color: #85839a; line-height: 1.6; margin-top: .2rem; }
.gt-doc-item { padding: .75rem .85rem; border: 1px solid #eeeafd; border-radius: 10px; margin: .35rem 0; }
.gt-detail-head { background: linear-gradient(120deg,#f4f1ff 0%,#faf9ff 100%); border: 1px solid #e9e4ff; border-radius: 12px; padding: 1rem 1.1rem; margin-bottom: .8rem; }
.gt-muted { color: #77728f; font-size: .82rem; }
</style>
""")

st.markdown("""
<div class="gt-section">
  <div class="gt-section-title">当前工作项目</div>
  <div class="gt-section-desc">需求版本数据将按当前项目进行筛选和管理。</div>
</div>
""", unsafe_allow_html=True)

try:
    projects = list_projects()
except Exception as e:
    st.error(f"项目列表加载失败：{e}")
    st.stop()

if not projects:
    st.info("当前没有可用项目，请先创建项目。")
    st.stop()

project_map = {project["id"]: project for project in projects}
project_ids = list(project_map.keys())

# 首次进入时默认选择项目列表中的第一项；后续保留用户当前选择。
if st.session_state.get("version_project_id") not in project_map:
    st.session_state["version_project_id"] = project_ids[0]

selected_project_id = st.session_state["version_project_id"]
selected_project = project_map[selected_project_id]

# 当前项目卡片沿用「项目中心」的名称、状态、描述和元信息展示方式。
import html

project_name_html = html.escape(str(selected_project.get("name") or "未命名项目"))
project_description_html = html.escape(
    str(selected_project.get("description") or "暂无项目描述")
)
project_id_html = html.escape(str(selected_project_id))
project_status = selected_project.get("status", "active")
if project_status == "archived":
    project_status_html = '<span class="gt-project-status-archived">● 已归档</span>'
else:
    project_status_html = '<span class="gt-project-status-active">● 进行中</span>'

with st.container(border=True):
    st.html(
        f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;">
            <div class="gt-project-card-title">🎮 {project_name_html}</div>
            {project_status_html}
        </div>
        <div class="gt-project-card-description">{project_description_html}</div>
        <div class="gt-project-card-meta">项目 ID：{project_id_html}</div>
        """
    )
    with st.popover("切换工作项目", use_container_width=True):
        st.caption("选择一个项目卡片，即可直接切换。")
        for project_id in project_ids:
            project = project_map[project_id]
            is_current = project_id == selected_project_id
            with st.container(border=True):
                if is_current:
                    st.markdown(f"**✓  {project['name']}**")
                    st.caption(f"当前项目 · {project_id}")
                else:
                    if st.button(
                        f"🎮  {project['name']}",
                        key=f"version_project_option_{project_id}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state["version_project_id"] = project_id
                        st.rerun()
                    st.caption(f"项目 ID：{project_id}")

try:
    saved_documents = list_documents(
        project_id=selected_project_id,
        include_deleted=True,
    )
except Exception as e:
    st.error(f"需求文档版本加载失败：{e}")
    st.stop()

action_message = st.session_state.pop("document_version_action_message", None)
if action_message:
    st.success(action_message)

if not saved_documents:
    st.info("当前项目还没有导入需求文档。")
    st.stop()

document_groups = {}
for document in saved_documents:
    document_groups.setdefault(document["document_key"], []).append(document)

total_document_count = len(document_groups)
total_history_versions = len(saved_documents)
total_active_versions = sum(1 for doc in saved_documents if not doc["is_deleted"])

st.markdown("""
<div class="gt-section">
  <div class="gt-section-title">版本概览</div>
  <div class="gt-section-desc">当前项目需求文档及版本记录统计。</div>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    metric_cols = st.columns(3)
    metric_cols[0].metric("需求文档数量", total_document_count)
    metric_cols[1].metric("有效版本数量", total_active_versions)
    metric_cols[2].metric("历史版本总数", total_history_versions)

st.markdown("""
<div class="gt-section">
  <div class="gt-section-title">文档版本管理</div>
  <div class="gt-section-desc">在左侧定位文档，在右侧查看版本详情并执行管理操作。</div>
</div>
""", unsafe_allow_html=True)

filter_col1, filter_col2 = st.columns([2, 1])
with filter_col1:
    search_keyword = st.text_input(
        "搜索文档名称或标识",
        placeholder="输入文档名称或 document_key",
        key="version_search_keyword",
    )
with filter_col2:
    document_status_filter = st.selectbox(
        "版本显示范围",
        options=["有效版本", "全部版本"],
        key="version_status_filter",
    )

filtered_groups = []
for key, all_versions in document_groups.items():
    active_versions = [doc for doc in all_versions if not doc["is_deleted"]]
    latest = active_versions[0] if active_versions else None
    visible_versions = active_versions if document_status_filter == "有效版本" else all_versions
    if not visible_versions:
        continue
    display_document = latest if latest else all_versions[0]
    keyword = search_keyword.strip().lower()
    document_name = display_document["document_name"].lower()
    if not keyword or keyword in document_name or keyword in key.lower():
        filtered_groups.append((key, visible_versions, all_versions, latest, display_document))

st.caption(
    f"筛选结果：{len(filtered_groups)} 份文档 · 当前项目共 {total_document_count} 份，"
    f"有效版本 {total_active_versions} 条，历史版本总数 {total_history_versions} 条。"
)

if not filtered_groups:
    st.warning("没有找到符合条件的需求文档。")
    st.stop()

group_map = {item[0]: item for item in filtered_groups}
document_keys = list(group_map.keys())

left_col, right_col = st.columns([0.38, 0.62], gap="large")

with left_col:
    st.markdown("#### 文档列表")
    st.caption("选择文档以查看对应的版本历史。")
    selected_document_key = st.selectbox(
        "选择需求文档",
        options=document_keys,
        format_func=lambda key: (
            f"{group_map[key][4]['document_name']} · "
            f"{len([v for v in group_map[key][2] if not v['is_deleted']])} 个有效版本"
        ),
        key="version_selected_document_key",
    )

    for key, versions, all_versions, latest, display_document in filtered_groups:
        latest_label = f"V{latest['version']}" if latest else "暂无有效版本"
        st.markdown(
            f"""<div class="gt-doc-item">
            <strong>{display_document['document_name']}</strong><br>
            <span class="gt-muted">{key}</span><br>
            <span class="gt-muted">最新有效：{latest_label} · 历史版本：{len(all_versions)}</span>
            </div>""",
            unsafe_allow_html=True,
        )

with right_col:
    key, versions, all_versions, latest, display_document = group_map[selected_document_key]

    st.markdown(
        f"""<div class="gt-detail-head">
        <strong>{display_document['document_name']}</strong><br>
        <span class="gt-muted">文档标识：{key}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    info_cols = st.columns(4)
    info_cols[0].metric("最新有效版本", f"V{latest['version']}" if latest else "无")
    info_cols[1].metric("有效版本数", sum(1 for doc in all_versions if not doc["is_deleted"]))
    info_cols[2].metric("历史版本总数", len(all_versions))
    info_cols[3].metric("文件类型", display_document["file_type"].upper())

    with st.container(border=True):
        st.write(f"**文档名称：** {display_document['document_name']}")
        st.write(f"**文档标识：** `{key}`")
        st.write(f"**文档 ID：** `{display_document['id']}`")
        st.write(f"**创建时间：** {format_local_datetime(display_document.get('created_at'))}")

    st.markdown("#### 版本历史")
    version_options = {
        (
            f"V{doc['version']}（{format_local_datetime(doc.get('created_at'))}）"
            + (" [已删除]" if doc["is_deleted"] else "")
        ): doc["id"]
        for doc in versions
    }
    selected_version_label = st.selectbox(
        "选择要管理的文档版本",
        options=list(version_options.keys()),
        key=f"manage_version_{key}",
    )
    selected_version_id = version_options[selected_version_label]
    selected_version_record = next(doc for doc in versions if doc["id"] == selected_version_id)

    st.markdown("#### 版本状态与操作")
    with st.container(border=True):
        if not selected_version_record["is_deleted"]:
            st.success(f"V{selected_version_record['version']} · 有效版本")
            confirm_delete = st.checkbox(
                f"确认逻辑删除 V{selected_version_record['version']}？",
                key=f"confirm_version_delete_{selected_version_id}",
            )
            if st.button(
                "删除所选版本",
                key=f"delete_version_{selected_version_id}",
                type="secondary",
                disabled=not confirm_delete,
                use_container_width=True,
            ):
                try:
                    deleted = soft_delete_document(selected_version_id)
                    if deleted:
                        st.session_state["document_version_action_message"] = (
                            f"V{selected_version_record['version']} 已成功逻辑删除。"
                        )
                        st.rerun()
                    else:
                        st.warning("删除未生效，该版本可能已经被删除。")
                except Exception as e:
                    st.error(f"删除文档版本失败：{e}")
        else:
            st.warning(f"V{selected_version_record['version']} · 已逻辑删除")
            if st.button(
                f"恢复 V{selected_version_record['version']}",
                key=f"restore_version_{selected_version_id}",
                type="primary",
                use_container_width=True,
            ):
                try:
                    restored = restore_document(selected_version_id)
                    if restored:
                        st.session_state["document_version_action_message"] = (
                            f"V{selected_version_record['version']} 已成功恢复。"
                        )
                        st.rerun()
                    else:
                        st.warning("恢复未生效，该版本可能已经恢复。")
                except Exception as e:
                    st.error(f"恢复文档版本失败：{e}")

    st.markdown("#### 版本内容")
    st.caption("读取当前所选版本保存的完整需求文档内容。")
    if st.button("查看该版本完整内容", key=f"view_version_{selected_version_id}"):
        try:
            selected_document = get_document(selected_version_id)
            if selected_document is None:
                st.error("未找到该文档版本。")
            else:
                st.session_state[f"viewed_version_{key}"] = selected_document
        except Exception as e:
            st.error(f"读取文档版本失败：{e}")

    viewed_document = st.session_state.get(f"viewed_version_{key}")
    if viewed_document is not None and viewed_document["id"] == selected_version_id:
        st.divider()
        st.markdown(f"**当前查看版本：V{viewed_document['version']}**")
        content_cols = st.columns(2)
        content_cols[0].metric("文件类型", viewed_document["file_type"].upper())
        content_cols[1].metric("字符数量", viewed_document["char_count"])
        st.text_area(
            "需求文档完整内容",
            value=viewed_document["parsed_content"] or "",
            height=350,
            disabled=True,
            key=f"version_content_{selected_version_id}",
        )

st.divider()
st.caption("GameTest AI · 需求版本管理")
