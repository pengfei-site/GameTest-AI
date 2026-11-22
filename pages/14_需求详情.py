import html
import streamlit as st

from components.header import render_header
from database.repositories.project_repository import list_projects
from database.repositories.document_repository import list_documents


project_id = st.query_params.get("project_id", "")
document_key = st.query_params.get("document_key", "")


def render_back_action():
    if st.button("← 返回需求列表", use_container_width=True):
        st.switch_page("pages/05_需求文档.py")


render_header(
    title="需求详情",
    description="查看需求文档信息、正文内容与历史版本。",
    breadcrumb=["需求中心", "需求文档", "需求详情"],
    actions=render_back_action,
)

if not project_id or not document_key:
    st.warning("缺少需求文档定位信息，请从需求文档列表重新进入。")
    if st.button("返回需求列表"):
        st.switch_page("pages/05_需求文档.py")
    st.stop()

try:
    projects = list_projects()
    project_map = {str(item["id"]): item for item in projects}
    project = project_map.get(str(project_id))
    if project is None:
        st.error("所属项目不存在或已不可用。")
        st.stop()
    versions = list_documents(project_id=str(project_id), document_key=str(document_key), include_deleted=True)
except Exception as exc:
    st.error(f"需求详情加载失败：{exc}")
    st.stop()

if not versions:
    st.warning("未找到对应的需求文档版本。")
    st.stop()

active_versions = [item for item in versions if not item.get("is_deleted")]
current = active_versions[0] if active_versions else versions[0]
name = str(current.get("document_name") or "未命名文档")
project_name = str(project.get("name") or "未命名项目")
status = "有效" if active_versions else "已删除"
status_color = "#15803D" if active_versions else "#B45309"
status_bg = "#DCFCE7" if active_versions else "#FEF3C7"

st.html(f"""
<style>
.gt-detail-hero {{ background:#fff; border:1px solid #E7EAF1; border-radius:14px; padding:20px 22px; margin:8px 0 18px; }}
.gt-detail-title {{ font-size:22px; font-weight:750; color:#24213F; overflow-wrap:anywhere; }}
.gt-detail-sub {{ color:#778196; font-size:13px; margin-top:7px; }}
.gt-detail-badge {{ display:inline-block; border-radius:20px; padding:4px 10px; color:{status_color}; background:{status_bg}; font-size:12px; font-weight:650; }}
.gt-detail-section {{ color:#292746; font-size:16px; font-weight:700; margin:22px 0 10px; }}
.gt-detail-version {{ border:1px solid #E7EAF1; border-radius:10px; padding:12px 14px; margin:7px 0; background:#fff; }}
</style>
<div class="gt-detail-hero">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
    <div class="gt-detail-title">▤ {html.escape(name)}</div>
    <span class="gt-detail-badge">{status}</span>
  </div>
  <div class="gt-detail-sub">所属项目：{html.escape(project_name)}　·　当前版本：V{current.get("version", 1)}　·　历史版本：{len(versions)} 个</div>
</div>
""")

st.markdown('<div class="gt-detail-section">基本信息</div>', unsafe_allow_html=True)
meta = st.columns(4)
meta[0].metric("当前版本", f'V{current.get("version", 1)}')
meta[1].metric("文件类型", str(current.get("file_type") or "未知").upper())
meta[2].metric("字符数", f'{(current.get("char_count") or 0):,}')
meta[3].metric("版本数量", len(versions))

with st.container(border=True):
    info_cols = st.columns(2)
    info_cols[0].caption("创建时间")
    info_cols[0].write(str(current.get("created_at") or "暂无"))
    info_cols[1].caption("文件名称")
    info_cols[1].write(str(current.get("file_name") or current.get("file_path") or "暂无"))

st.markdown('<div class="gt-detail-section">需求正文</div>', unsafe_allow_html=True)
content = current.get("parsed_content") or ""
if content:
    st.text_area("需求正文内容", value=content, height=520, disabled=True, label_visibility="collapsed")
else:
    st.info("当前版本没有可展示的解析正文。")

st.markdown('<div class="gt-detail-section">版本历史</div>', unsafe_allow_html=True)
for item in versions:
    deleted = bool(item.get("is_deleted"))
    version_status = "已删除" if deleted else "有效"
    st.html(f"""
    <div class="gt-detail-version">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
        <strong style="color:#302D50;">V{item.get("version", 1)}</strong>
        <span style="font-size:12px;color:{"#B45309" if deleted else "#15803D"};">{version_status}</span>
      </div>
      <div style="font-size:12px;color:#8490A3;margin-top:5px;">{html.escape(str(item.get("created_at") or "创建时间未知"))}　·　{str(item.get("file_type") or "未知").upper()}　·　{(item.get("char_count") or 0):,} 字符</div>
    </div>
    """)
    with st.expander(f"查看 V{item.get('version', 1)} 内容"):
        st.text_area(
            f"V{item.get('version', 1)} 正文",
            value=item.get("parsed_content") or "",
            height=260,
            disabled=True,
            key=f"detail_version_content_{item.get('id')}",
        )
