
import streamlit as st

from database.repositories.project_repository import (
    list_projects,
    update_project,
)
from components.header import render_header


render_header(
    title="编辑项目",
    description="维护进行中游戏项目的名称和描述信息。",
    breadcrumb=["项目中心", "项目编辑"],
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


# ============================================================
# 二、编辑项目
# ============================================================

st.markdown("### ✏️ 项目信息维护")
st.caption("选择一个进行中的项目，修改项目基本资料。")

if not active_projects:

    st.info("当前没有可编辑的进行中项目。")

else:

    edit_map = {
        p["id"]: p
        for p in active_projects
    }

    selected_edit_id = st.selectbox(
        "选择需要编辑的项目",
        options=list(edit_map.keys()),
        format_func=lambda pid: edit_map[pid]["name"],
        key="edit_project_selector",
    )

    selected_project = edit_map[selected_edit_id]

    with st.container(border=True):

        st.markdown("#### 项目基本信息")

        with st.form("edit_project_form"):

            edit_name = st.text_input(
                "项目名称",
                value=selected_project["name"],
            )

            edit_description = st.text_area(
                "项目描述",
                value=selected_project.get("description") or "",
                height=140,
            )

            submitted = st.form_submit_button(
                "保存修改",
                type="primary",
                width="stretch",
            )

            if submitted:

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
                            st.warning(
                                "项目不存在或没有完成修改。"
                            )

                    except Exception as exc:
                        st.error(f"修改项目失败：{exc}")


st.divider()

st.page_link(
    "pages/01_项目列表.py",
    label="返回项目列表",
    icon="📚",
)

