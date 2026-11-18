
import streamlit as st

from database.repositories.project_repository import (
    list_projects,
    archive_project,
    restore_project,
)
from components.header import render_header


render_header(
    title="项目归档管理",
    description="归档不再进行中的项目，也可以恢复历史项目。",
    breadcrumb=["项目中心", "项目归档"],
)


# ============================================================
# 一、加载项目
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
# 二、项目状态概览
# ============================================================

col1, col2 = st.columns(2)

col1.metric("🚀 进行中项目", len(active_projects))
col2.metric("📦 已归档项目", len(archived_projects))

st.divider()


# ============================================================
# 三、归档与恢复
# ============================================================

col_archive, col_restore = st.columns(2)


# ----------------------------
# 归档项目
# ----------------------------

with col_archive:

    with st.container(border=True):

        st.markdown("### 📦 归档项目")
        st.caption("将不再进行中的项目移入归档状态。")

        if not active_projects:

            st.info("没有可归档的项目。")

        else:

            archive_map = {
                p["id"]: p
                for p in active_projects
            }

            archive_id = st.selectbox(
                "选择归档项目",
                options=list(archive_map.keys()),
                format_func=lambda pid: archive_map[pid]["name"],
                key="archive_project_selector",
            )

            st.warning(
                "归档后，该项目将不再出现在默认项目选择列表中。"
            )

            if st.button(
                "确认归档项目",
                key="archive_project_button",
                use_container_width=True,
            ):

                try:
                    result = archive_project(archive_id)

                    if result:
                        st.success("项目归档成功！")
                        st.rerun()

                    else:
                        st.warning("项目不存在或已经归档。")

                except Exception as exc:
                    st.error(f"归档项目失败：{exc}")


# ----------------------------
# 恢复项目
# ----------------------------

with col_restore:

    with st.container(border=True):

        st.markdown("### ♻️ 恢复项目")
        st.caption("将已归档项目恢复为进行中状态。")

        if not archived_projects:

            st.info("当前没有已归档项目。")

        else:

            restore_map = {
                p["id"]: p
                for p in archived_projects
            }

            restore_id = st.selectbox(
                "选择恢复项目",
                options=list(restore_map.keys()),
                format_func=lambda pid: restore_map[pid]["name"],
                key="restore_project_selector",
            )

            st.info(
                "恢复后，该项目将重新进入进行中项目列表。"
            )

            if st.button(
                "恢复项目",
                key="restore_project_button",
                type="primary",
                use_container_width=True,
            ):

                try:
                    result = restore_project(restore_id)

                    if result:
                        st.success("项目恢复成功！")
                        st.rerun()

                    else:
                        st.warning("项目不存在或已经恢复。")

                except Exception as exc:
                    st.error(f"恢复项目失败：{exc}")


st.divider()

st.page_link(
    "pages/01_项目列表.py",
    label="返回项目列表",
    icon="📚",
)
