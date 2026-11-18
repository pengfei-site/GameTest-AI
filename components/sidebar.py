
import streamlit as st


def render_sidebar(pages):
    """渲染 GameTest AI 统一侧边栏。"""

    with st.sidebar:

        # 品牌区域
        st.html("""
        <div style="padding:12px 5px 22px;">
            <div style="
                font-size:25px;
                font-weight:850;
                letter-spacing:-1px;
                color:#ffffff;
            ">
                🎮 GameTest AI
            </div>

            <div style="
                font-size:12px;
                color:#d1cafa;
                margin-top:7px;
            ">
                AI 驱动的智能游戏测试平台
            </div>
        </div>
        """)

        # 导航区域
        for group_name, group_pages in pages.items():

            st.markdown(
                f"""
                <div style="
                    font-size:12px;
                    font-weight:700;
                    color:#c7c0f5;
                    padding:10px 5px 8px;
                ">
                    {group_name}
                </div>
                """,
                unsafe_allow_html=True,
            )

            for page in group_pages:
                st.page_link(
                    page,
                    label=page.title,
                    icon=page.icon,
                    use_container_width=True,
                )

        st.divider()

        # 产品介绍
        st.html("""
        <div style="
            background:rgba(255,255,255,.10);
            padding:15px;
            border-radius:13px;
            margin-top:15px;
        ">
            <div style="
                font-weight:800;
                font-size:15px;
                color:white;
            ">
                ✨ AI Testing
            </div>

            <div style="
                font-size:12px;
                color:#d1cafa;
                line-height:1.8;
                margin-top:8px;
            ">
                从项目管理、需求分析到测试点与测试用例，
                构建完整的智能游戏测试工作流。
            </div>
        </div>
        """)

        st.markdown(
            """
            <div style="
                text-align:center;
                color:#c7c0f5;
                font-size:11px;
                margin-top:35px;
            ">
                GameTest AI · V1.0
            </div>
            """,
            unsafe_allow_html=True,
        )
