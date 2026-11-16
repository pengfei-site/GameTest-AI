
import streamlit as st

from database.repositories.project_repository import (
    archive_project,
    create_project,
    list_projects,
    restore_project,
    update_project,
)


st.set_page_config(
    page_title="项目管理 | GameTest AI",
    page_icon="📁",
    layout="wide",
)

st.title("📁 项目管理")
st.caption("创建、编辑、归档和恢复游戏测试项目")

st.divider()


def load_projects():
    """读取全部项目，包括已归档项目。"""
    return list_projects(include_archived=True)


def get_project_label(project):
    status_label = "已归档" if project["status"] == "archived" else "进行中"
    return f'{project["name"]}（{status_label}）'


# ============================================================
# 一、加载项目
# ============================================================

try:
    projects = load_projects()
except Exception as exc:
    st.error(f"项目列表读取失败：{exc}")
    st.stop()

active_projects = [
    project for project in projects
    if project["status"] == "active"
]

archived_projects = [
    project for project in projects
    if project["status"] == "archived"
]

# ============================================================
# 二、项目统计
# ============================================================

st.subheader("项目概览")

col1, col2, col3 = st.columns(3)

col1.metric("项目总数", len(projects))
col2.metric("进行中项目", len(active_projects))
col3.metric("已归档项目", len(archived_projects))

st.divider()

# ============================================================
# 三、创建项目
# ============================================================

st.subheader("创建新项目")

with st.form("create_project_form", clear_on_submit=True):
    new_name = st.text_input(
        "项目名称",
        placeholder="例如：三国策略手游",
    )

    new_description = st.text_area(
        "项目描述",
        placeholder="简单介绍游戏类型、项目背景或测试范围。",
        height=100,
    )

    create_submitted = st.form_submit_button(
        "创建项目",
        type="primary",
    )

    if create_submitted:
        if not new_name.strip():
            st.error("项目名称不能为空。")
        else:
            try:
                project = create_project(
                    name=new_name,
                    description=new_description,
                )
                st.success(f'项目「{project["name"]}」创建成功！')
                st.rerun()
            except Exception as exc:
                st.error(f"创建项目失败：{exc}")

st.divider()

# ============================================================
# 四、项目列表
# ============================================================

st.subheader("项目列表")

if not projects:
    st.info("当前还没有项目，请先创建一个项目。")
else:
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

    if not displayed_projects:
        st.info("当前筛选条件下没有项目。")
    else:
        for project in displayed_projects:
            status_label = (
                "🟢 进行中"
                if project["status"] == "active"
                else "⚪ 已归档"
            )

            with st.container(border=True):
                col_info, col_status = st.columns([4, 1])

                with col_info:
                    st.markdown(f'### {project["name"]}')
                    st.write(
                        project.get("description") or "暂无项目描述"
                    )
                    st.caption(
                        f'项目 ID：{project["id"]}'
                    )
                    st.caption(
                        f'创建时间：{project.get("created_at", "未知")} '
                        f'| 最近更新：{project.get("updated_at", "未知")}'
                    )

                with col_status:
                    st.write(status_label)

# ============================================================
# 五、编辑项目
# ============================================================

st.divider()
st.subheader("编辑项目信息")

if not active_projects:
    st.info("当前没有可编辑的进行中项目。")
else:
    edit_project_map = {
        project["id"]: project
        for project in active_projects
    }

    selected_edit_id = st.selectbox(
        "选择需要编辑的项目",
        options=list(edit_project_map.keys()),
        format_func=lambda project_id: edit_project_map[
            project_id
        ]["name"],
        key="edit_project_selector",
    )

    selected_edit_project = edit_project_map[selected_edit_id]

    with st.form("edit_project_form"):
        edit_name = st.text_input(
            "项目名称",
            value=selected_edit_project["name"],
        )

        edit_description = st.text_area(
            "项目描述",
            value=selected_edit_project.get("description") or "",
            height=100,
        )

        edit_submitted = st.form_submit_button(
            "保存修改",
            type="primary",
        )

        if edit_submitted:
            if not edit_name.strip():
                st.error("项目名称不能为空。")
            else:
                try:
                    updated = update_project(
                        project_id=selected_edit_id,
                        name=edit_name,
                        description=edit_description,
                    )

                    if updated:
                        st.success("项目资料修改成功！")
                        st.rerun()
                    else:
                        st.warning("项目不存在或没有完成修改。")

                except Exception as exc:
                    st.error(f"修改项目失败：{exc}")

# ============================================================
# 六、项目归档与恢复
# ============================================================

st.divider()
st.subheader("项目归档与恢复")

col_archive, col_restore = st.columns(2)

with col_archive:
    st.markdown("#### 归档项目")

    if not active_projects:
        st.info("没有可归档的项目。")
    else:
        archive_map = {
            project["id"]: project
            for project in active_projects
        }

        selected_archive_id = st.selectbox(
            "选择归档项目",
            options=list(archive_map.keys()),
            format_func=lambda project_id: archive_map[
                project_id
            ]["name"],
            key="archive_project_selector",
        )

        st.warning(
            "归档后，该项目将不再出现在默认项目选择列表中，"
            "但项目及其关联历史数据会保留。"
        )

        if st.button(
            "确认归档项目",
            key="archive_project_button",
            type="secondary",
        ):
            try:
                archived = archive_project(selected_archive_id)

                if archived:
                    st.success("项目归档成功！")
                    st.rerun()
                else:
                    st.warning("项目不存在或已经归档。")

            except Exception as exc:
                st.error(f"归档项目失败：{exc}")

with col_restore:
    st.markdown("#### 恢复项目")

    if not archived_projects:
        st.info("当前没有已归档项目。")
    else:
        restore_map = {
            project["id"]: project
            for project in archived_projects
        }

        selected_restore_id = st.selectbox(
            "选择恢复项目",
            options=list(restore_map.keys()),
            format_func=lambda project_id: restore_map[
                project_id
            ]["name"],
            key="restore_project_selector",
        )

        if st.button(
            "恢复项目",
            key="restore_project_button",
            type="primary",
        ):
            try:
                restored = restore_project(selected_restore_id)

                if restored:
                    st.success("项目恢复成功！")
                    st.rerun()
                else:
                    st.warning("项目不存在或已经恢复。")

            except Exception as exc:
                st.error(f"恢复项目失败：{exc}")

st.divider()

st.caption(
    "GameTest AI · 项目管理 · 项目归档不会删除项目关联的历史业务数据。"
)
