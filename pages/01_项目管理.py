
import html

import streamlit as st

from database.repositories.project_repository import (
    archive_project,
    create_project,
    list_projects,
    restore_project,
    update_project,
)


# ============================================================
# 一、页面样式
# ============================================================

st.markdown(
    """
    <style>
    .project-hero {
        background: linear-gradient(120deg, #34256f 0%, #6652bd 55%, #8974dc 100%);
        padding: 30px 34px;
        border-radius: 20px;
        margin-bottom: 25px;
        box-shadow: 0 10px 28px rgba(76, 57, 150, 0.16);
    }

    .project-hero-title {
        color: #ffffff !important;
        font-size: 30px;
        font-weight: 850;
        line-height: 1.4;
        margin-bottom: 10px;
        text-shadow: 0 2px 8px rgba(20, 10, 60, 0.2);
    }

    .project-hero-desc {
        color: #f0ebff !important;
        font-size: 14px;
        line-height: 1.9;
        opacity: 1;
    }

    .section-heading {
        font-size: 20px;
        font-weight: 800;
        color: #29234a;
        margin: 8px 0 4px;
    }

    .section-description {
        font-size: 13px;
        color: #85809b;
        margin-bottom: 16px;
    }

    .project-stat-card {
        background: #ffffff;
        border: 1px solid #eeeafd;
        border-radius: 16px;
        padding: 19px 20px;
        box-shadow: 0 4px 16px rgba(76, 57, 150, 0.05);
        min-height: 112px;
    }

    .project-stat-label {
        color: #817b9b;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .project-stat-value {
        color: #30265f;
        font-size: 30px;
        font-weight: 850;
        line-height: 1.2;
    }

    .project-stat-note {
        color: #a09ab5;
        font-size: 11px;
        margin-top: 7px;
    }

    .project-card-title {
        color: #30265f;
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 7px;
        overflow-wrap: anywhere;
    }

    .project-card-description {
        color: #77728c;
        font-size: 13px;
        line-height: 1.8;
        margin-bottom: 12px;
        overflow-wrap: anywhere;
    }

    .project-card-meta {
        color: #9690aa;
        font-size: 11px;
        line-height: 1.9;
    }

    .project-section-tag {
        display: inline-block;
        background: #f0edff;
        color: #6852bd;
        padding: 5px 11px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        margin-bottom: 12px;
    }

    div[data-testid="stForm"] {
        background: #ffffff;
        border: 1px solid #eeeafd;
        border-radius: 16px;
        padding: 20px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #eeeafd;
        border-radius: 16px;
    }

    .stButton button,
    .stFormSubmitButton button {
        border-radius: 10px;
        font-weight: 650;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #eeeafd;
        border-radius: 14px;
        padding: 15px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 二、顶部区域
# ============================================================

st.markdown(
    """
    <div class="project-hero">
        <div class="project-hero-title">
            📁 游戏项目管理中心
        </div>
        <div class="project-hero-desc">
            统一管理你的游戏测试项目。<br>
            创建项目、维护项目信息、查看项目状态，
            并通过归档与恢复功能管理项目生命周期。
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 三、加载项目
# ============================================================

def load_projects():
    """读取全部项目，包括已归档项目。"""
    return list_projects(include_archived=True)


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
# 四、项目统计
# ============================================================

st.markdown(
    '<div class="section-heading">项目概览</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">快速了解当前工作空间中的项目状态</div>',
    unsafe_allow_html=True,
)

stat1, stat2, stat3 = st.columns(3)

statistics = [
    (stat1, "📁 项目总数", len(projects), "当前工作空间全部项目"),
    (stat2, "🚀 进行中项目", len(active_projects), "正在使用的项目"),
    (stat3, "📦 已归档项目", len(archived_projects), "已完成归档的项目"),
]

for column, label, value, note in statistics:
    with column:
        st.markdown(
            f"""
            <div class="project-stat-card">
                <div class="project-stat-label">{label}</div>
                <div class="project-stat-value">{value}</div>
                <div class="project-stat-note">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")
st.divider()


# ============================================================
# 五、创建项目
# ============================================================

st.markdown(
    '<div class="section-heading">✨ 创建新项目</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">创建一个游戏项目，开始你的智能测试工作流</div>',
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown(
        '<div class="project-section-tag">NEW PROJECT</div>',
        unsafe_allow_html=True,
    )

    with st.form("create_project_form", clear_on_submit=True):
        new_name = st.text_input(
            "项目名称",
            placeholder="例如：三国策略手游",
        )

        new_description = st.text_area(
            "项目描述",
            placeholder="介绍游戏类型、项目背景或测试范围……",
            height=100,
        )

        create_submitted = st.form_submit_button(
            "＋ 创建项目",
            type="primary",
            use_container_width=True,
        )

        if create_submitted:
            if not new_name.strip():
                st.error("项目名称不能为空。")
            else:
                try:
                    project = create_project(
                        name=new_name.strip(),
                        description=new_description,
                    )

                    st.success(
                        f'项目「{project["name"]}」创建成功！'
                    )
                    st.rerun()

                except Exception as exc:
                    st.error(f"创建项目失败：{exc}")


st.divider()


# ============================================================
# 六、项目列表
# ============================================================

st.markdown(
    '<div class="section-heading">📚 项目列表</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">查看、筛选当前工作空间中的游戏项目</div>',
    unsafe_allow_html=True,
)

if not projects:
    st.info("当前还没有项目，请先创建一个项目。")

else:
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

    if not displayed_projects:
        st.info("当前筛选条件下没有项目。")

    else:
        for project in displayed_projects:
            is_active = project["status"] == "active"

            status_label = (
                "🟢 进行中"
                if is_active
                else "⚪ 已归档"
            )

            project_name = html.escape(
                str(project.get("name") or "未命名项目")
            )

            project_description = html.escape(
                str(project.get("description") or "暂无项目描述")
            )

            project_id = html.escape(str(project.get("id", "未知")))

            created_at = html.escape(
                str(project.get("created_at", "未知"))
            )

            updated_at = html.escape(
                str(project.get("updated_at", "未知"))
            )

            with st.container(border=True):
                info_col, status_col = st.columns([5, 1])

                with info_col:
                    st.markdown(
                        f"""
                        <div class="project-card-title">
                            {project_name}
                        </div>
                        <div class="project-card-description">
                            {project_description}
                        </div>
                        <div class="project-card-meta">
                            项目 ID：{project_id}<br>
                            创建时间：{created_at}<br>
                            最近更新：{updated_at}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with status_col:
                    st.write("")
                    st.write(status_label)


st.divider()


# ============================================================
# 七、编辑项目
# ============================================================

st.markdown(
    '<div class="section-heading">✏️ 编辑项目信息</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">修改进行中项目的名称和描述</div>',
    unsafe_allow_html=True,
)

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

    with st.container(border=True):
        st.markdown(
            '<div class="project-section-tag">EDIT PROJECT</div>',
            unsafe_allow_html=True,
        )

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
                use_container_width=True,
            )

            if edit_submitted:
                if not edit_name.strip():
                    st.error("项目名称不能为空。")
                else:
                    try:
                        updated = update_project(
                            project_id=selected_edit_id,
                            name=edit_name.strip(),
                            description=edit_description,
                        )

                        if updated:
                            st.success("项目资料修改成功！")
                            st.rerun()
                        else:
                            st.warning("项目不存在或没有完成修改。")

                    except Exception as exc:
                        st.error(f"修改项目失败：{exc}")


st.divider()


# ============================================================
# 八、项目归档与恢复
# ============================================================

st.markdown(
    '<div class="section-heading">📦 项目归档与恢复</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">管理项目生命周期，归档不会删除项目关联的历史业务数据</div>',
    unsafe_allow_html=True,
)

col_archive, col_restore = st.columns(2)

# ----------------------------
# 归档项目
# ----------------------------

with col_archive:
    with st.container(border=True):
        st.markdown("#### 📦 归档项目")
        st.caption("将暂时不再使用的项目移入归档状态。")

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
                use_container_width=True,
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


# ----------------------------
# 恢复项目
# ----------------------------

with col_restore:
    with st.container(border=True):
        st.markdown("#### ♻️ 恢复项目")
        st.caption("将已归档的项目恢复到正常使用状态。")

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

            st.info(
                "恢复后，该项目将重新进入进行中项目列表，"
                "可以继续使用。"
            )

            if st.button(
                "恢复项目",
                key="restore_project_button",
                type="primary",
                use_container_width=True,
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


# ============================================================
# 九、页脚
# ============================================================

st.divider()

st.caption(
    "GameTest AI · 项目管理 · 项目归档不会删除项目关联的历史业务数据。"
)
