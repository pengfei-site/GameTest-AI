
import streamlit as st

from database.repositories.project_repository import list_projects
from components.header import render_header


# ============================================================
# 一、页面初始化
# ============================================================

render_header(
    title="项目列表",
    description="查看和筛选工作空间中的游戏测试项目。",
    breadcrumb=["项目中心", "项目列表"],
)


# ============================================================
# 二、页面样式
# ============================================================

st.html("""
<style>
.project-overview {
    margin-bottom: 8px;
}

.project-card-title {
    font-size: 19px;
    font-weight: 650;
    color: #292746;
    margin-bottom: 8px;
}

.project-card-description {
    color: #626174;
    font-size: 14px;
    line-height: 1.7;
    margin-bottom: 12px;
}

.project-card-meta {
    color: #89879b;
    font-size: 12px;
    line-height: 1.8;
}

.project-section-caption {
    color: #858397;
    font-size: 13px;
    margin-top: -8px;
    margin-bottom: 16px;
}

.project-status-active {
    display: inline-block;
    background: #e8f6ed;
    color: #21834b;
    padding: 5px 11px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}

.project-status-archived {
    display: inline-block;
    background: #f0eff4;
    color: #777487;
    padding: 5px 11px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
</style>
""")


# ============================================================
# 三、加载项目数据
# ============================================================

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
# 四、项目概览
# ============================================================

st.markdown("### 📊 项目概览")
st.caption("快速了解当前工作空间中的项目情况。")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="📁 项目总数",
        value=len(projects),
    )

with col2:
    st.metric(
        label="🚀 进行中项目",
        value=len(active_projects),
    )

with col3:
    st.metric(
        label="📦 已归档项目",
        value=len(archived_projects),
    )


st.divider()


# ============================================================
# 五、项目筛选
# ============================================================

st.markdown("### 📚 全部项目")
st.markdown(
    '<div class="project-section-caption">'
    '根据项目状态筛选和查看工作空间中的项目。'
    '</div>',
    unsafe_allow_html=True,
)

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
    st.metric(
        label="当前显示",
        value=len(displayed_projects),
    )


# ============================================================
# 六、项目列表
# ============================================================

if not displayed_projects:

    st.info(
        "当前筛选条件下没有项目。",
        icon="📭",
    )

    if not projects:
        st.caption("可以通过下方的创建项目入口，建立第一个游戏测试项目。")

else:

    for project in displayed_projects:

        is_active = project["status"] == "active"

        project_name = project.get("name") or "未命名项目"
        project_description = (
            project.get("description") or "暂无项目描述"
        )

        project_id = project.get("id", "未知")
        created_at = project.get("created_at", "未知")
        updated_at = project.get("updated_at", "未知")

        with st.container(border=True):

            col_info, col_status = st.columns(
                [5, 1],
                vertical_alignment="center",
            )

            with col_info:

                st.subheader(
                    f"🎮 {project_name}"
                )

                st.write(project_description)

                st.caption(
                    f"项目 ID：{project_id}"
                )

                st.caption(
                    f"创建时间：{created_at}  |  "
                    f"最近更新：{updated_at}"
                )

            with col_status:

                if is_active:
                    st.markdown(
                        '<span class="project-status-active">'
                        '● 进行中'
                        '</span>',
                        unsafe_allow_html=True,
                    )

                else:
                    st.markdown(
                        '<span class="project-status-archived">'
                        '● 已归档'
                        '</span>',
                        unsafe_allow_html=True,
                    )


# ============================================================
# 七、项目操作入口
# ============================================================

st.divider()

st.markdown("### 🚀 项目操作")
st.caption("通过以下入口管理项目的创建、编辑和归档。")

col_create, col_edit, col_archive = st.columns(3)

with col_create:
    st.page_link(
        "pages/02_项目创建.py",
        label="创建项目",
        icon="✨",
        width="stretch",
    )

with col_edit:
    st.page_link(
        "pages/03_项目编辑.py",
        label="编辑项目",
        icon="✏️",
        width="stretch",
    )

with col_archive:
    st.page_link(
        "pages/04_项目归档.py",
        label="归档管理",
        icon="📦",
        width="stretch",
    )
