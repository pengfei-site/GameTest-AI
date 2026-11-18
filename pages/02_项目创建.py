
import streamlit as st

from database.repositories.project_repository import create_project
from components.header import render_header


render_header(
    title="创建项目",
    description="创建游戏测试项目，开启智能测试工作流。",
    breadcrumb=["项目中心", "项目创建"],
)


st.markdown("### ✨ 新建游戏项目")
st.caption("填写项目基本信息，创建后即可进入需求分析和测试流程。")

with st.container(border=True):

    st.markdown("#### NEW PROJECT")

    with st.form(
        "create_project_form",
        clear_on_submit=True,
    ):

        new_name = st.text_input(
            "项目名称",
            placeholder="例如：三国策略手游",
        )

        new_description = st.text_area(
            "项目描述",
            placeholder="介绍游戏类型、项目背景或测试范围……",
            height=140,
        )

        submitted = st.form_submit_button(
            "＋ 创建项目",
            type="primary",
            width="stretch",
        )

        if submitted:

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

                    st.page_link(
                        "pages/01_项目列表.py",
                        label="返回项目列表",
                        icon="📚",
                    )

                except Exception as exc:
                    st.error(f"创建项目失败：{exc}")


st.divider()

st.page_link(
    "pages/01_项目列表.py",
    label="返回项目列表",
    icon="📚",
)

