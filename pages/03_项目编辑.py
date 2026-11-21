
import streamlit as st

from database.repositories.project_repository import (
    list_projects,
    update_project,
)
from components.header import render_header


# ============================================================
# 一、页面初始化
# ============================================================

render_header(
    title="编辑项目",
    description="维护进行中游戏项目的名称和描述信息。",
    breadcrumb=["项目中心", "项目编辑"],
)


# ============================================================
# 二、页面样式
# ============================================================

st.html("""
<style>
.edit-project-intro {
    color: #777589;
    font-size: 14px;
    line-height: 1.7;
    margin-top: -6px;
    margin-bottom: 20px;
}

.edit-project-label {
    color: #6254c7;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
}

.edit-project-hint {
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


# ============================================================
# 四、项目编辑
# ============================================================

st.markdown("### ✏️ 项目信息维护")

st.markdown(
    '<div class="edit-project-intro">'
    '选择一个进行中的项目，查看并修改项目基本资料。'
    '</div>',
    unsafe_allow_html=True,
)


if not active_projects:

    st.info(
        "当前没有可编辑的进行中项目。",
        icon="📭",
    )

else:

    edit_map = {
        p["id"]: p
        for p in active_projects
    }

    # 接收项目列表页传递的目标项目 ID
    target_project_id = st.session_state.pop(
        "edit_project_target_id",
        None,
    )

    if target_project_id is not None:

        # 使用字符串比较，兼容数据库 ID 类型
        for project_id in edit_map:

            if str(project_id) == str(target_project_id):
                st.session_state["edit_project_selector"] = project_id
                break


    st.markdown("#### 1. 选择项目")

    selected_edit_id = st.selectbox(
        "选择需要编辑的项目",
        options=list(edit_map.keys()),
        format_func=lambda pid: edit_map[pid]["name"],
        key="edit_project_selector",
    )

    selected_project = edit_map[selected_edit_id]

    st.markdown("#### 2. 修改项目信息")

    with st.container(border=True):

        st.markdown(
            '<div class="edit-project-label">'
            'EDIT PROJECT'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown("##### 项目基本信息")

        st.caption(
            "修改后保存即可更新项目资料。"
        )

        with st.form("edit_project_form"):

            edit_name = st.text_input(
                "项目名称",
                value=selected_project["name"],
                help="项目名称不能为空。",
            )

            edit_description = st.text_area(
                "项目描述",
                value=selected_project.get("description") or "",
                height=140,
                help="可以填写游戏背景、玩法和测试范围。",
            )

            st.markdown(
                '<div class="edit-project-hint">'
                '提示：修改项目资料不会改变已有需求、测试点和测试用例。'
                '</div>',
                unsafe_allow_html=True,
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

                        st.error(
                            f"修改项目失败：{exc}"
                        )


# ============================================================
# 五、返回入口
# ============================================================

st.divider()

st.page_link(
    "pages/01_项目列表.py",
    label="返回项目列表",
    icon="📚",
)
