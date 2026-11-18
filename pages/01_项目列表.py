
import streamlit as st

from database.repositories.project_repository import list_projects
from components.header import render_header


render_header(
    title="项目列表",
    description="查看和筛选工作空间中的游戏测试项目。",
    breadcrumb=["项目中心", "项目列表"],
)


# ============================================================
# 一、加载项目数据
# ============================================================

@st.cache_data(ttl=0)
def _unused_cache_placeholder():
    return None


try:
    projects = list_projects(include_archived=True)
except Exception as exc:
    st.error(f"项目列表读取失败：{exc}")
    st.stop()


active_projects = [
    p for p in projects
    if p["status"] == "active"
]

archived_projects = [
    p for p in projects
    if p["status"] == "archived"
]


# ============================================================
# 二、项目概览
# ============================================================

st.markdown("### 📊 项目概览")
st.caption("快速查看当前工作空间中的项目状态。")

col1, col2, col3 = st.columns(3)

col1.metric("📁 项目总数", len(projects))
col2.metric("🚀 进行中项目", len(active_projects))
col3.metric("📦 已归档项目", len(archived_projects))

st.divider()


# ============================================================
# 三、项目筛选
# ============================================================

st.markdown("### 📚 全部项目")

filter_col, count_col = st.columns([3, 1])

with filter_col:
    status_filter = st.radio(
        "项目状态",
        options=["全部项目", "进行中", "已归档"],
        horizontal=True,
        key="project_status_filter",
    )

if status_filter == "进行中":
    displayed_projects = active_projects
elif status_filter == "已归档":
    displayed_projects = archived_projects
else:
    displayed_projects = projects

with count_col:
    st.metric("当前显示", len(displayed_projects))


# ============================================================
# 四、项目列表
# ============================================================

if not displayed_projects:
    st.info("当前筛选条件下没有项目。")

else:
    for project in displayed_projects:

        is_active = project["status"] == "active"

        status_label = "🟢 进行中" if is_active else "⚪ 已归档"

        with st.container(border=True):

            col_info, col_status = st.columns([5, 1])

            with col_info:
                st.markdown(
                    f"### 🎮 {project.get('name', '未命名项目')}"
                )

                st.write(
                    project.get("description") or "暂无项目描述"
                )

                st.caption(
                    f"项目 ID：{project.get('id', '未知')}"
                )

                st.caption(
                    f"创建时间：{project.get('created_at', '未知')} "
                    f"| 最近更新：{project.get('updated_at', '未知')}"
                )

            with col_status:
                st.write("")
                st.write(status_label)


st.divider()

st.markdown("### 🚀 项目操作")

col_create, col_edit, col_archive = st.columns(3)

with col_create:
    st.page_link(
        "pages/02_项目创建.py",
        label="＋ 创建项目",
        icon="✨",
        width="stretch",
    )

with col_edit:
    st.page_link(
        "pages/03_项目编辑.py",
        label="✏️ 编辑项目",
        icon="✏️",
        width="stretch",
    )

with col_archive:
    st.page_link(
        "pages/04_项目归档.py",
        label="📦 归档管理",
        icon="📦",
        width="stretch",
    )

