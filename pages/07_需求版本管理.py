import html
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
.gt-version-page { color: #172033; }
.gt-version-project {
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; flex-wrap: wrap; padding: 2px 0;
}
.gt-version-project-main { min-width: 220px; flex: 1 1 360px; }
/* 项目概览卡片固定使用白底，不跟随主题的容器底色变化。 */
div[data-testid="stVerticalBlock"].st-key-version_project_overview {
    background: #FFFFFF !important;
    border: 1px solid #E7EAF1 !important;
    border-radius: 14px !important;
    padding: 18px 20px !important;
    box-shadow: 0 2px 8px rgba(23, 32, 51, 0.04);
}
div[data-testid="stVerticalBlock"].st-key-version_project_overview > div {
    background: #FFFFFF;
}
.gt-version-project-title {
    color: #172033; font-size: 19px; line-height: 1.45; font-weight: 750;
    margin-bottom: 5px;
}
.gt-version-project-desc { color: #64748B; font-size: 13px; line-height: 1.6; }
.gt-version-project-id {
    display: inline-block; margin-top: 8px; padding: 4px 9px;
    color: #64748B; background: #F3F5F9; border-radius: 6px; font-size: 11px;
}
/* 项目中心卡片：可见内容与透明整卡点击层分离。 */
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell {
    position: relative;
    height: 132px !important;
    min-height: 132px !important;
    max-height: 132px !important;
    box-sizing: border-box;
    /* Popover 浮层必须允许溢出卡片，否则标题和项目选择按钮会被裁切。 */
    overflow: visible !important;
    background: #FFFFFF !important;
    border: 1px solid #E7EAF1 !important;
    border-radius: 12px !important;
    padding: 12px 18px !important;
    box-shadow: 0 2px 8px rgba(23, 32, 51, 0.04);
    transition: border-color .15s, box-shadow .15s;
}
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell:hover {
    border-color: #C9C4E8 !important;
    box-shadow: 0 3px 10px rgba(23, 32, 51, 0.06);
}
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell > div {
    gap: 0;
}
/* Popover 的真实 DOM 层级随 Streamlit 版本可能变化，因此使用后代选择器定位触发按钮。
   触发按钮脱离文档流并铺满卡片；按钮本身完全透明，但仍保留点击能力。 */
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell {
    position: relative !important;
    overflow: visible !important;
    z-index: 1;
}
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell [data-testid="stPopover"] {
    position: static !important;
    z-index: 2 !important;
}
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell [data-testid="stPopover"] button {
    position: absolute !important;
    inset: 0 !important;
    z-index: 2 !important;
    display: block !important;
    width: 100% !important;
    height: 100% !important;
    height: 132px !important;
    min-height: 132px !important;
    max-height: 132px !important;
    max-width: none !important;
    margin: 0 !important;
    padding: 0 !important;
    opacity: 0 !important;
    color: transparent !important;
    background: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
    cursor: pointer !important;
}
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell [data-testid="stPopover"] [data-baseweb="popover"],
div[data-testid="stVerticalBlock"].st-key-version_project_picker_shell [data-testid="stPopover"] [role="dialog"] {
    position: relative !important;
    z-index: 1000 !important;
}
.gt-version-project-stats {
    display: flex; gap: 0; align-items: stretch; flex: 0 1 auto;
}
/* 项目卡片与右侧统计卡片统一高度，保持同一水平基线。 */
div[data-testid="stVerticalBlock"].st-key-version_project_stats_shell {
    height: 132px !important;
    min-height: 132px !important;
    max-height: 132px !important;
}
div[data-testid="stVerticalBlock"].st-key-version_project_stats_shell [data-testid="stMetric"] {
    height: 132px !important;
    min-height: 132px !important;
    max-height: 132px !important;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
    justify-content: center;
}
.gt-version-stat {
    min-width: 104px; padding: 3px 18px; text-align: center;
    border-left: 1px solid #E9ECF3;
}
.gt-version-stat strong { display:block; color:#243B82; font-size:22px; line-height:1.35; }
.gt-version-stat span { color:#64748B; font-size:11px; }
.gt-version-section-title { font-size:16px; font-weight:750; color:#172033; }
.gt-version-section-hint { color:#8A93A5; font-size:12px; margin-top:3px; }
.gt-version-doc {
    padding: 10px 12px; border: 1px solid #E8EAF2; border-radius: 10px;
    background: #FFFFFF; margin: 7px 0;
}
.gt-version-doc-active { border-color:#9A8BFA; background:#F8F7FF; }
.gt-version-doc-name { font-size:13px; color:#172033; font-weight:700; }
.gt-version-doc-meta { font-size:11px; color:#8490A3; margin-top:4px; }
.gt-version-detail-head {
    padding: 13px 15px; border-radius: 10px; background:#F7F8FC;
    border:1px solid #EAECF4; margin-bottom:12px;
}
.gt-version-detail-title { font-size:17px; color:#172033; font-weight:750; }
.gt-version-detail-key { font-size:11px; color:#8490A3; margin-top:5px; }
.gt-version-content {
    border:1px solid #EAECF4; background:#FAFBFD; border-radius:10px;
    padding:14px; color:#334155; font-size:13px; line-height:1.8;
    white-space:pre-wrap; overflow-wrap:anywhere;
}
div[data-testid="stVerticalBlock"] div:has(> .gt-version-doc) { gap: 0; }
@media (max-width: 760px) {
    .gt-version-project-stats { width:100%; }
    .gt-version-stat { min-width:0; flex:1; padding:4px 8px; }
}
</style>
""")

try:
    projects = list_projects()
except Exception as exc:
    st.error(f"项目列表加载失败：{exc}")
    st.stop()

if not projects:
    st.info("当前没有可用项目，请先创建项目。")
    st.stop()

project_map = {str(project["id"]): project for project in projects}
project_ids = list(project_map)
if st.session_state.get("version_project_id") not in project_map:
    st.session_state["version_project_id"] = project_ids[0]

selected_project_id = st.session_state["version_project_id"]
selected_project = project_map[selected_project_id]
project_name = html.escape(str(selected_project.get("name") or "未命名项目"))
project_description = html.escape(str(selected_project.get("description") or "暂无项目描述"))
project_status = selected_project.get("status", "active")
status_html = (
    '<span class="gt-status gt-status-neutral">● 已归档</span>'
    if project_status == "archived"
    else '<span class="gt-status gt-status-success">● 进行中</span>'
)

try:
    saved_documents = list_documents(project_id=selected_project_id, include_deleted=True)
except Exception as exc:
    st.error(f"需求文档版本加载失败：{exc}")
    st.stop()

document_groups = {}
for document in saved_documents:
    document_groups.setdefault(document["document_key"], []).append(document)

total_document_count = len(document_groups)
total_history_versions = len(saved_documents)
total_active_versions = sum(1 for doc in saved_documents if not doc["is_deleted"])

# 项目卡片与统计指标并列：左侧独立项目卡片，右侧三项统计。
overview_project_col, overview_stats_col = st.columns(
    [1.53, 1.47],
    gap="medium",
    vertical_alignment="center",
)

with overview_project_col:
    # 卡片内容沿用项目中心卡片的 HTML 结构与全局样式。
    with st.container(key="version_project_picker_shell"):
        st.html(
            f"""
            <div style="
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                margin-bottom: 10px;
            ">
                <div class="gt-card-title" style="margin-bottom: 0;">
                    🎮 {project_name}
                </div>
                {status_html}
            </div>
            <div class="gt-card-description">
                {project_description}
            </div>
            <div class="gt-info-card-footer">
                <div>项目 ID：{html.escape(selected_project_id)}</div>
            </div>
            """
        )
        # 透明 Popover 触发器覆盖整张卡片，点击后在卡片下方显示悬浮项目列表。
        with st.popover(
            "切换项目",
            use_container_width=True,
        ):
            for project_id in project_ids:
                project = project_map[project_id]
                option_status = "已归档" if project.get("status") == "archived" else "进行中"
                option_name = html.escape(str(project.get("name") or "未命名项目"))
                option_description = html.escape(str(project.get("description") or "暂无项目描述"))
                option_id = html.escape(str(project_id))
                is_current = project_id == selected_project_id
                status_color = "#64748B" if project.get("status") == "archived" else "#15803D"
                status_bg = "#F1F5F9" if project.get("status") == "archived" else "#DCFCE7"
                card_border = "#8B7CF6" if is_current else "#E5E7EB"
                card_bg = "#F8F7FF" if is_current else "#FFFFFF"
                with st.container(key=f"version_project_option_{project_id}"):
                    st.html(f"""
                    <div style="
                        border: 1px solid {card_border};
                        background: {card_bg};
                        border-radius: 11px;
                        padding: 13px 15px 10px;
                        margin: 5px 0 0;
                    ">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <strong style="font-size:14px;color:#172033;">🎮 {option_name}</strong>
                            <span style="
                                white-space:nowrap;border-radius:20px;padding:3px 8px;
                                color:{status_color};background:{status_bg};font-size:11px;
                            ">{option_status}</span>
                        </div>
                        <div style="color:#64748B;font-size:12px;line-height:1.55;margin-top:7px;">
                            {option_description}
                        </div>
                        <div style="color:#94A3B8;font-size:10px;margin-top:7px;">
                            项目 ID：{option_id}
                        </div>
                    </div>
                    """)
                    if not is_current and st.button(
                        "选择此项目",
                        key=f"choose_version_project_{project_id}",
                        use_container_width=True,
                        type="secondary",
                    ):
                        st.session_state["version_project_id"] = project_id
                        st.rerun()


with overview_stats_col:
    with st.container(key="version_project_stats_shell"):
        stat_cols = st.columns(3, gap="small")
        for col, value, label in zip(
            stat_cols,
            [total_document_count, total_active_versions, total_history_versions],
            ["需求文档", "有效版本", "历史版本"],
        ):
            with col:
                st.metric(label, value)

action_message = st.session_state.pop("document_version_action_message", None)
if action_message:
    st.success(action_message)

if not saved_documents:
    st.info("当前项目还没有导入需求文档。")
    st.stop()

st.markdown("")
left_col, right_col = st.columns([0.39, 0.61], gap="large")

with left_col:
    st.html("""
    <div class="gt-version-section-title">▤ 需求文档列表</div>
    <div class="gt-version-section-hint">搜索并选择文档，查看对应版本详情。</div>
    """)
    search_keyword = st.text_input(
        "搜索需求文档",
        placeholder="输入文档名称或 document_key",
        key="version_search_keyword",
        label_visibility="collapsed",
    )
    document_status_filter = st.selectbox(
        "版本显示范围",
        options=["有效版本", "全部版本"],
        key="version_status_filter",
    )

    filtered_groups = []
    keyword = search_keyword.strip().lower()
    for key, all_versions in document_groups.items():
        active_versions = [doc for doc in all_versions if not doc["is_deleted"]]
        visible_versions = active_versions if document_status_filter == "有效版本" else all_versions
        if not visible_versions:
            continue
        display_document = active_versions[0] if active_versions else all_versions[0]
        if (
            not keyword
            or keyword in str(display_document["document_name"]).lower()
            or keyword in str(key).lower()
        ):
            filtered_groups.append((key, visible_versions, all_versions, active_versions, display_document))

    st.caption(f"共找到 {len(filtered_groups)} 份文档")
    if not filtered_groups:
        st.warning("没有找到符合条件的需求文档。")
        st.stop()

    group_map = {item[0]: item for item in filtered_groups}
    document_keys = list(group_map)
    selected_key = st.session_state.get("version_selected_document_key")
    if selected_key not in group_map:
        selected_key = document_keys[0]
        st.session_state["version_selected_document_key"] = selected_key

    for key, versions, all_versions, active_versions, display_document in filtered_groups:
        is_selected = key == selected_key
        latest_label = f"V{active_versions[0]['version']}" if active_versions else "暂无有效版本"
        doc_name = html.escape(str(display_document.get("document_name") or "未命名文档"))
        doc_key = html.escape(str(key))
        card_class = "gt-version-doc gt-version-doc-active" if is_selected else "gt-version-doc"
        st.html(f"""
        <div class="{card_class}">
            <div class="gt-version-doc-name">▤ {doc_name}</div>
            <div class="gt-version-doc-meta">{doc_key}</div>
            <div class="gt-version-doc-meta">最新有效：{latest_label}　·　历史版本：{len(all_versions)}</div>
        </div>
        """)
        if st.button(
            "当前选中" if is_selected else "查看文档",
            key=f"select_version_doc_{key}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            st.session_state["version_selected_document_key"] = key
            st.rerun()

with right_col:
    key, versions, all_versions, active_versions, display_document = group_map[selected_key]
    doc_name = html.escape(str(display_document.get("document_name") or "未命名文档"))
    doc_key_html = html.escape(str(key))
    st.html(f"""
    <div class="gt-version-detail-head">
        <div class="gt-version-detail-title">▤ {doc_name}</div>
        <div class="gt-version-detail-key">文档标识：{doc_key_html}</div>
    </div>
    """)

    meta_cols = st.columns(4)
    meta_cols[0].metric("最新有效版本", f"V{active_versions[0]['version']}" if active_versions else "无")
    meta_cols[1].metric("有效版本数", len(active_versions))
    meta_cols[2].metric("历史版本数", len(all_versions))
    meta_cols[3].metric("文件类型", str(display_document.get("file_type") or "未知").upper())

    with st.container(border=True):
        detail_cols = st.columns(2)
        detail_cols[0].caption("文档 ID")
        detail_cols[0].code(str(display_document["id"]))
        detail_cols[1].caption("创建时间")
        detail_cols[1].write(format_local_datetime(display_document.get("created_at")))

    st.markdown("#### 版本历史")
    version_options = {
        (
            f"V{doc['version']} · {format_local_datetime(doc.get('created_at'))}"
            + (" · 已删除" if doc["is_deleted"] else "")
        ): doc["id"]
        for doc in versions
    }
    selected_label = st.selectbox(
        "选择要查看和管理的版本",
        options=list(version_options),
        key=f"manage_version_{key}",
    )
    selected_version_id = version_options[selected_label]
    selected_version = next(doc for doc in versions if doc["id"] == selected_version_id)

    version_meta = st.columns(3)
    version_meta[0].metric("版本号", f"V{selected_version['version']}")
    version_meta[1].metric("创建时间", format_local_datetime(selected_version.get("created_at")))
    version_meta[2].metric("状态", "已删除" if selected_version["is_deleted"] else "有效")

    st.markdown("#### 版本管理")
    if not selected_version["is_deleted"]:
        st.success(f"V{selected_version['version']} · 有效版本")
        confirm_delete = st.checkbox(
            f"确认逻辑删除 V{selected_version['version']}？",
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
                        f"V{selected_version['version']} 已成功逻辑删除。"
                    )
                    st.rerun()
                st.warning("删除未生效，该版本可能已经被删除。")
            except Exception as exc:
                st.error(f"删除文档版本失败：{exc}")
    else:
        st.warning(f"V{selected_version['version']} · 已逻辑删除")
        if st.button(
            f"恢复 V{selected_version['version']}",
            key=f"restore_version_{selected_version_id}",
            type="primary",
            use_container_width=True,
        ):
            try:
                restored = restore_document(selected_version_id)
                if restored:
                    st.session_state["document_version_action_message"] = (
                        f"V{selected_version['version']} 已成功恢复。"
                    )
                    st.rerun()
                st.warning("恢复未生效，该版本可能已经恢复。")
            except Exception as exc:
                st.error(f"恢复文档版本失败：{exc}")

    st.markdown("#### 版本内容")
    st.caption("读取当前所选版本保存的完整需求文档内容。")
    if st.button("查看该版本完整内容", key=f"view_version_{selected_version_id}"):
        try:
            selected_document = get_document(selected_version_id)
            if selected_document is None:
                st.error("未找到该文档版本。")
            else:
                st.session_state[f"viewed_version_{key}"] = selected_document
        except Exception as exc:
            st.error(f"读取文档版本失败：{exc}")

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
