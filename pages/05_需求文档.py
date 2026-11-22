
import hashlib
import html
import streamlit as st

from core.document_parser import parse_document
from database.repositories.project_repository import list_projects
from database.repositories.document_repository import create_document_version, list_documents
from core.document_storage import save_original_document
from components.header import render_header


# ============================================================
# 页面初始化
# ============================================================

def sync_document_name_from_file():
    """选择文件后，自动使用不含扩展名的文件名填充文档名称。"""
    selected = st.session_state.get("requirement_document_dialog")
    if selected is not None:
        import os
        st.session_state["document_name"] = os.path.splitext(selected.name)[0]


@st.dialog("上传游戏策划需求文档", width="large")
def show_requirement_upload_dialog():
    st.caption("填写文档信息并选择文件，支持 DOCX、PDF、Markdown 和 TXT 格式。")

    selected_file = st.file_uploader(
        "选择需求文档",
        type=["docx", "pdf", "md", "txt"],
        key="requirement_document_dialog",
        on_change=sync_document_name_from_file,
    )
    document_name_input = st.text_input(
        "文档名称",
        placeholder="选择文件后自动识别，也可手动修改",
        key="document_name",
    )
    document_key_input = st.text_input(
        "文档标识（document_key）",
        placeholder="例如：LOGIN_REQUIREMENT",
        key="document_key",
    )

    if st.button(
        "确认上传",
        type="primary",
        width="stretch",
        disabled=selected_file is None,
    ):
        if not document_name_input.strip():
            st.error("请输入文档名称。")
        elif not document_key_input.strip():
            st.error("请输入文档标识。")
        else:
            import uuid

            file_bytes = selected_file.getvalue()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            project_id = st.session_state.get("document_project_id")

            try:
                with st.spinner("正在解析并保存需求文档，请稍候..."):
                    result = parse_document(selected_file.name, file_bytes)
                    document_id = str(uuid.uuid4())
                    original_file_path = save_original_document(
                        project_id=str(project_id),
                        document_id=document_id,
                        file_name=selected_file.name,
                        file_bytes=file_bytes,
                    )
                    saved_document = create_document_version(
                        project_id=project_id,
                        document_key=document_key_input.strip(),
                        document_name=document_name_input.strip(),
                        file_type=result["file_type"],
                        file_path=original_file_path,
                        parsed_content=result["content"],
                        file_hash=file_hash,
                        page_count=result["page_count"],
                        char_count=result["char_count"],
                        document_id=document_id,
                    )

                st.session_state["document_upload_notice"] = {
                    "success": True,
                    "message": (
                        f"需求文档「{document_name_input.strip()}」解析并保存成功，"
                        f"已创建版本 V{saved_document['version']}。"
                    ),
                }
                st.rerun()

            except Exception as e:
                st.error(f"上传失败：文档解析或保存过程中发生错误。{e}")


def render_upload_action():
    """在页面标题右侧显示宽度缩小三分之一、右对齐的需求上传入口。"""
    _, _, button_col = st.columns([1, 1, 1])
    with button_col:
        if st.button("＋ 需求上传", type="primary", width="stretch"):
            show_requirement_upload_dialog()


render_header(
    title="需求文档",
    description="导入和管理游戏策划需求文档，为后续结构化分析提供原始需求依据。",
    breadcrumb=["需求中心", "需求文档"],
    actions=render_upload_action,
)


# ============================================================
# 页面专属样式
# ============================================================

st.html("""
<style>

/* 页面区块 */
.gt-section {
    margin: 1.5rem 0 0.8rem 0;
}

.gt-section-title {
    font-size: 1.05rem;
    font-weight: 650;
    color: #292746;
    margin-bottom: 0.25rem;
}

.gt-section-desc {
    font-size: 0.85rem;
    color: #85839a;
    margin-bottom: 0.8rem;
}

/* 通用卡片 */
.gt-panel {
    background: #ffffff;
    border: 1px solid #eeeafd;
    border-radius: 14px;
    padding: 1.2rem 1.35rem;
    margin-bottom: 1rem;
}

.gt-panel-title {
    font-size: 0.95rem;
    font-weight: 650;
    color: #302d50;
    margin-bottom: 0.45rem;
}

.gt-panel-desc {
    color: #85839a;
    font-size: 0.82rem;
    line-height: 1.6;
}

/* 文件信息 */
.gt-file-info {
    background: #f8f7ff;
    border: 1px solid #eae7fc;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin-top: 0.7rem;
}

.gt-file-name {
    color: #39345f;
    font-weight: 650;
    font-size: 0.92rem;
    overflow-wrap: anywhere;
}

.gt-file-meta {
    color: #85839a;
    font-size: 0.8rem;
    margin-top: 0.3rem;
}

/* 结果统计 */
.gt-stat-card {
    background: #ffffff;
    border: 1px solid #eeeafd;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    min-height: 92px;
}

.gt-stat-label {
    font-size: 0.78rem;
    color: #85839a;
    margin-bottom: 0.4rem;
}

.gt-stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #39345f;
    overflow-wrap: anywhere;
}

/* 状态说明 */
.gt-status-panel {
    background: #f6f4ff;
    border: 1px solid #e9e5ff;
    border-radius: 12px;
    padding: 1rem 1.15rem;
    margin: 0.8rem 0;
}

.gt-status-title {
    color: #5143a3;
    font-weight: 650;
    font-size: 0.92rem;
    margin-bottom: 0.25rem;
}

.gt-status-desc {
    color: #77728f;
    font-size: 0.83rem;
    line-height: 1.6;
}


/* 项目选择与概览：与需求版本管理页面保持一致 */
.gt-version-project-picker {
    position: relative;
    box-sizing: border-box;
    width: 100%;
}
.gt-version-project-title { color:#172033; font-size:19px; line-height:1.45; font-weight:750; margin-bottom:5px; }
.gt-version-project-desc { color:#64748B; font-size:13px; line-height:1.6; }
.gt-version-project-id { display:inline-block; margin-top:8px; padding:4px 9px; color:#64748B; background:#F3F5F9; border-radius:6px; font-size:11px; }

/* 项目卡片容器结构与需求版本管理页面保持一致。 */
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell {
    position: relative !important;
    height: 132px !important;
    min-height: 132px !important;
    max-height: 132px !important;
    box-sizing: border-box;
    overflow: visible !important;
    background: #FFFFFF !important;
    border: 1px solid #E7EAF1 !important;
    border-radius: 12px !important;
    padding: 12px 18px !important;
    box-shadow: 0 2px 8px rgba(23, 32, 51, 0.04);
    transition: border-color .15s, box-shadow .15s;
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell:hover {
    border-color: #C9C4E8 !important;
    box-shadow: 0 3px 10px rgba(23, 32, 51, 0.06);
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell::after {
    content: "⌄";
    position: absolute;
    right: 16px;
    bottom: 12px;
    z-index: 3;
    color: #8490A3;
    font-size: 20px;
    line-height: 1;
    font-weight: 600;
    pointer-events: none;
    transition: color .15s, transform .15s;
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell:hover::after {
    color: #6D5CE7;
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell:has([data-testid="stPopover"] button[aria-expanded="true"])::after {
    content: "⌃";
    color: #6D5CE7;
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell > div {
    gap: 0;
}
.gt-version-project-title { color:#172033; font-size:19px; line-height:1.45; font-weight:750; margin-bottom:5px; }
.gt-version-project-desc { color:#64748B; font-size:13px; line-height:1.6; }
.gt-version-project-id { display:inline-block; margin-top:8px; padding:4px 9px; color:#64748B; background:#F3F5F9; border-radius:6px; font-size:11px; }
div[data-testid="stVerticalBlock"].st-key-document_project_stats [data-testid="stMetric"] {
    height:132px; min-height:132px; box-sizing:border-box;
    display:flex; flex-direction:column; justify-content:center;
}

/* 项目卡片整卡透明点击层：不显示独立的“切换项目”按钮。 */
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell {
    position: relative !important;
    overflow: visible !important;
    z-index: 1;
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell [data-testid="stPopover"] {
    position: static !important;
    z-index: 2 !important;
}
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell [data-testid="stPopover"] button[aria-haspopup="dialog"] {
    position: absolute !important;
    inset: 0 !important;
    z-index: 5 !important;
    display: block !important;
    width: 100% !important;
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
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell [data-testid="stPopover"] [data-baseweb="popover"],
div[data-testid="stVerticalBlock"].st-key-document_project_picker_shell [data-testid="stPopover"] [role="dialog"] {
    position: relative !important;
    z-index: 1000 !important;
}

/* 小屏适配 */
@media (max-width: 768px) {
    .gt-panel {
        padding: 1rem;
    }
}
</style>
""")


# ============================================================
# 一、选择项目
# ============================================================



try:
    projects = list_projects()
except Exception as e:
    st.error(f"项目列表加载失败：{e}")
    st.stop()

if not projects:
    st.warning("当前没有可用的游戏项目，请先创建项目。")
    st.stop()

project_map = {
    project["id"]: project
    for project in projects
}

project_ids = list(project_map.keys())
if st.session_state.get("document_project_id") not in project_map:
    st.session_state["document_project_id"] = project_ids[0]

selected_project_id = st.session_state["document_project_id"]
selected_project = project_map[selected_project_id]

try:
    project_documents = list_documents(
        project_id=selected_project_id,
        include_deleted=True,
    )
except Exception as e:
    st.error(f"项目需求文档概览加载失败：{e}")
    st.stop()

document_groups = {}
for item in project_documents:
    document_groups.setdefault(item["document_key"], []).append(item)

total_document_count = len(document_groups)
total_active_versions = sum(1 for item in project_documents if not item["is_deleted"] and item.get("is_effective", 0))
total_history_versions = len(project_documents)

project_name = html.escape(str(selected_project.get("name") or "未命名项目"))
project_description = html.escape(str(selected_project.get("description") or "暂无项目描述"))
project_status = selected_project.get("status", "active")
status_label = "已归档" if project_status == "archived" else "进行中"
status_color = "#64748B" if project_status == "archived" else "#15803D"
status_bg = "#F1F5F9" if project_status == "archived" else "#DCFCE7"

project_col, stats_col = st.columns([1.53, 1.47], gap="medium", vertical_alignment="center")
with project_col:
    with st.container(key="document_project_picker_shell"):
        st.html(f"""
        <div class="gt-version-project-picker">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;">
                <div class="gt-version-project-title">🎮 {project_name}</div>
                <span style="white-space:nowrap;border-radius:20px;padding:3px 8px;color:{status_color};background:{status_bg};font-size:11px;">● {status_label}</span>
            </div>
            <div class="gt-version-project-desc">{project_description}</div>
            <div class="gt-version-project-id">项目 ID：{html.escape(str(selected_project_id))}</div>
        </div>
        """)
        with st.popover("切换项目", width="stretch"):
            for project_id in project_ids:
                project = project_map[project_id]
                is_current = project_id == selected_project_id
                option_name = html.escape(str(project.get("name") or "未命名项目"))
                option_desc = html.escape(str(project.get("description") or "暂无项目描述"))
                option_id = html.escape(str(project_id))
                option_status = "已归档" if project.get("status") == "archived" else "进行中"
                option_color = "#64748B" if project.get("status") == "archived" else "#15803D"
                option_bg = "#F1F5F9" if project.get("status") == "archived" else "#DCFCE7"
                border = "#8B7CF6" if is_current else "#E5E7EB"
                bg = "#F8F7FF" if is_current else "#FFFFFF"
                with st.container():
                    st.html(f"""
                    <div style="border:1px solid {border};background:{bg};border-radius:11px;padding:13px 15px 10px;margin:5px 0 0;">
                        <div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">
                            <strong style="font-size:14px;color:#172033;">🎮 {option_name}</strong>
                            <span style="white-space:nowrap;border-radius:20px;padding:3px 8px;color:{option_color};background:{option_bg};font-size:11px;">{option_status}</span>
                        </div>
                        <div style="color:#64748B;font-size:12px;line-height:1.55;margin-top:7px;">{option_desc}</div>
                        <div style="color:#94A3B8;font-size:10px;margin-top:7px;">项目 ID：{option_id}</div>
                    </div>
                    """)
                    if not is_current and st.button("选择此项目", key=f"choose_document_project_{project_id}", width="stretch"):
                        st.session_state["document_project_id"] = project_id
                        st.rerun()

with stats_col:
    with st.container(key="document_project_stats"):
        metric_cols = st.columns(3, gap="small")
        for col, value, label in zip(
            metric_cols,
            [total_document_count, total_active_versions, total_history_versions],
            ["需求文档", "有效版本", "历史版本"],
        ):
            with col:
                st.metric(label, value)




# ============================================================
# 二、需求列表（TAPD 风格）
# ============================================================

st.markdown("""
<div class="gt-section">
    <div class="gt-section-title">需求列表</div>
    <div class="gt-section-desc">集中查看当前项目的需求文档，支持关键词检索和状态筛选。</div>
</div>
""", unsafe_allow_html=True)

requirement_groups = {}
for item in project_documents:
    requirement_groups.setdefault(item["document_key"], []).append(item)

requirement_items = []
for key, versions in requirement_groups.items():
    active_versions = [item for item in versions if not item["is_deleted"] and item.get("is_effective", 0)]
    display_version = active_versions[0] if active_versions else versions[0]
    requirement_items.append({
        "document": display_version,
        "version_count": len(versions),
        "active": bool(active_versions),
    })

search_col, filter_col, count_col = st.columns([2.4, 1, 1], vertical_alignment="center")
with search_col:
    requirement_search = st.text_input(
        "搜索需求文档",
        placeholder="搜索文档名称…",
        key="requirement_list_search",
        label_visibility="collapsed",
    )
with filter_col:
    requirement_filter = st.selectbox(
        "文档状态",
        ["全部状态", "有效", "已废弃", "已删除"],
        key="requirement_list_filter",
        label_visibility="collapsed",
    )
with count_col:
    st.markdown(
        f'<div style="text-align:right;color:#64748B;font-size:13px;padding-top:8px;">共 {len(requirement_items)} 条</div>',
        unsafe_allow_html=True,
    )

search_text = requirement_search.strip().lower()
filtered_requirements = []
for entry in requirement_items:
    doc = entry["document"]
    matches_search = (
        not search_text
        or search_text in str(doc.get("document_name") or "").lower()
    )
    matches_filter = (
        requirement_filter == "全部状态"
        or (requirement_filter == "有效" and entry["active"])
        or (requirement_filter == "已废弃" and not entry["active"] and not entry["document"].get("is_deleted", 0))
            or (requirement_filter == "已删除" and bool(entry["document"].get("is_deleted", 0)))
    )
    if matches_search and matches_filter:
        filtered_requirements.append(entry)

if not filtered_requirements:
    st.info("暂无符合条件的需求文档。点击右上角「需求上传」添加文档。")
else:
    table_rows = []
    for entry in filtered_requirements:
        doc = entry["document"]
        name = str(doc.get("document_name") or "未命名文档")
        version = f"V{doc.get('version') or 1}"
        file_type = str(doc.get("file_type") or "未知").upper()
        document_key_value = str(doc.get("document_key") or "")
        detail_url = (
            "/requirement-detail"
            f"?project_id={__import__('urllib.parse', fromlist=['quote']).quote(str(selected_project_id))}"
            f"&document_key={__import__('urllib.parse', fromlist=['quote']).quote(document_key_value)}"
        )
        if entry["active"]:
            status_html = '<span class="gt-tapd-status gt-tapd-status-active">有效</span>'
        else:
            status_html = (
                '<span class="gt-tapd-status gt-tapd-status-deleted">已删除</span>'
                if doc.get("is_deleted", 0)
                else '<span class="gt-tapd-status gt-tapd-status-deprecated">已废弃</span>'
            )
        table_rows.append(
            "<tr>"
            f'<td class="gt-tapd-name"><a href="{html.escape(detail_url, quote=True)}">{html.escape(name)}</a></td>'
            f'<td class="gt-tapd-version">{html.escape(version)}</td>'
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
    .gt-tapd-table tbody td:nth-child(1) { width: 65%; }
    .gt-tapd-table thead th:nth-child(2),
    .gt-tapd-table tbody td:nth-child(2) { width: 12%; color: #606266; }
    .gt-tapd-table thead th:nth-child(3),
    .gt-tapd-table tbody td:nth-child(3) { width: 12%; color: #606266; }
    .gt-tapd-table thead th:nth-child(4),
    .gt-tapd-table tbody td:nth-child(4) { width: 11%; }
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
    .gt-tapd-status-deprecated { color: #909399; background: #F4F4F5; }
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

st.caption("提示：有效版本设定、历史版本查看、恢复和删除操作请前往「需求版本管理」页面。")


# ============================================================
# 三、上传结果提示
# ============================================================

upload_notice = st.session_state.pop("document_upload_notice", None)
if upload_notice:
    if upload_notice.get("success"):
        st.toast(upload_notice.get("message", "需求文档上传成功。"), icon="✅")
    else:
        st.error(upload_notice.get("message", "需求文档上传失败。"))


st.divider()
st.caption("GameTest AI · 需求文档管理")
