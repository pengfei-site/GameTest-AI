
import streamlit as st

from database.repositories.project_repository import create_project
from components.header import render_header


# ============================================================
# 一、页面初始化
# ============================================================

render_header(
    title="创建项目",
    description="创建游戏测试项目，开启智能测试工作流。",
    breadcrumb=["项目中心", "项目创建"],
)


# ============================================================
# 二、页面样式
# ============================================================

st.html("""
<style>
.create-project-intro {
    color: #777589;
    font-size: 14px;
    line-height: 1.7;
    margin-top: -6px;
    margin-bottom: 20px;
}

.create-project-label {
    color: #6254c7;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1.2px;
    margin-bottom: 8px;
}

.create-project-hint {
    color: #858397;
    font-size: 13px;
    line-height: 1.7;
    margin-top: 12px;
}

.create-project-footer {
    color: #858397;
    font-size: 12px;
    margin-top: 8px;
}
</style>
""")


# ============================================================
# 三、页面介绍
# ============================================================

st.markdown("### ✨ 新建游戏项目")

st.markdown(
    '<div class="create-project-intro">'
    '填写项目基本信息，创建后即可进入需求分析和测试流程。'
    '</div>',
    unsafe_allow_html=True,
)


# ============================================================
# 四、项目创建表单
# ============================================================

with st.container(border=True):

    st.markdown(
        '<div class="create-project-label">NEW PROJECT</div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### 项目基本信息")

    st.caption("请填写项目名称和相关描述。")

    with st.form(
        "create_project_form",
        clear_on_submit=True,
    ):

        new_name = st.text_input(
            "项目名称",
            placeholder="例如：三国策略手游",
            help="项目名称为必填项。",
        )

        new_description = st.text_area(
            "项目描述",
            placeholder="介绍游戏类型、项目背景或测试范围……",
            height=140,
            help="可以填写游戏玩法、核心系统、测试重点等信息。",
        )

        st.markdown(
            '<div class="create-project-hint">'
            '提示：项目创建成功后，可以继续录入需求文档、'
            '生成测试点和测试用例。'
            '</div>',
            unsafe_allow_html=True,
        )

        submitted = st.form_submit_button(
            "✨ 创建项目",
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

                    st.error(
                        f"创建项目失败：{exc}"
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

st.markdown(
    '<div class="create-project-footer">'
    'GameTest AI · 项目管理'
    '</div>',
    unsafe_allow_html=True,
)
