
import streamlit as st

from database.repositories.project_repository import (
    list_projects,
    archive_project,
    restore_project,
)
from components.header import render_header


# ============================================================
# 一、页面初始化
# ============================================================

render_header(
    title="项目归档管理",
    description="归档不再进行中的项目，也可以恢复历史项目。",
    breadcrumb=["项目中心", "项目归档"],
)


# ============================================================
# 二、页面样式
# ============================================================

st.html("""
<style>
.archive-page-intro {
    color: #777589;
    font-size: 14px;
    line-height: 1.7;
    margin-top: -6px;
    margin-bottom: 20px;
}

.archive-card-label {
    color: #6254c7;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
}

.archive-card-hint {
    color: #858397;
    font-size: 13px;
    line-height: 1.7;
    margin-top: 10px;
}
</style>
""")


# ============================================================
# 三、加载项目
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
# 四、页面介绍
# ============================================================

st.markdown("### 📦 项目生命周期管理")

st.markdown(
    '<div class="archive-page-intro">'
    '根据项目当前状态执行归档或恢复操作，'
    '方便管理工作空间中的历史项目。'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 五、项目状态概览
# ============================================================

st.markdown("#### 📊 项目状态概览")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "🚀 进行中项目",
        len(active_projects),
    )

with col2:
    st.metric(
        "📦 已归档项目",
        len(archived_projects),
    )


st.divider()


# ============================================================
# 六、归档与恢复
# ============================================================

st.markdown("### 项目操作")
st.caption("选择目标项目后，执行对应的状态变更操作。")

col_archive, col_restore = st.columns(2)


# ============================================================
# 六-1、归档项目
# ============================================================

with col_archive:

    with st.container(border=True):

        st.markdown(
            '<div class="archive-card-label">'
            'ARCHIVE PROJECT'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown("#### 📦 归档项目")

        st.caption(
            "将不再进行中的项目移入归档状态。"
        )

        if not active_projects:

            st.info(
                "当前没有可归档的项目。",
                icon="📭",
            )

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

            st.markdown(
                '<div class="archive-card-hint">'
                '归档不会删除项目数据，历史项目信息仍然保留。'
                '</div>',
                unsafe_allow_html=True,
            )

            if st.button(
                "确认归档项目",
                key="archive_project_button",
                width="stretch",
            ):

                try:
                    result = archive_project(archive_id)

                    if result:

                        st.success("项目归档成功！")
                        st.rerun()

                    else:

                        st.warning(
                            "项目不存在或已经归档。"
                        )

                except Exception as exc:

                    st.error(
                        f"归档项目失败：{exc}"
                    )


# ============================================================
# 六-2、恢复项目
# ============================================================

with col_restore:

    with st.container(border=True):

        st.markdown(
            '<div class="archive-card-label">'
            'RESTORE PROJECT'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown("#### ♻️ 恢复项目")

        st.caption(
            "将已归档项目恢复为进行中状态。"
        )

        if not archived_projects:

            st.info(
                "当前没有已归档项目。",
                icon="📭",
            )

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

            st.markdown(
                '<div class="archive-card-hint">'
                '恢复后可以继续进行需求分析和测试管理。'
                '</div>',
                unsafe_allow_html=True,
            )

            if st.button(
                "恢复项目",
                key="restore_project_button",
                type="primary",
                width="stretch",
            ):

                try:
                    result = restore_project(restore_id)

                    if result:

                        st.success("项目恢复成功！")
                        st.rerun()

                    else:

                        st.warning(
                            "项目不存在或已经恢复。"
                        )

                except Exception as exc:

                    st.error(
                        f"恢复项目失败：{exc}"
                    )


# ============================================================
# 七、返回入口
# ============================================================

st.divider()

st.page_link(
    "pages/01_项目列表.py",
    label="返回项目列表",
    icon="📚",
)
