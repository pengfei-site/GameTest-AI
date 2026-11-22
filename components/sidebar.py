 
import streamlit as st


def render_sidebar(pages):
    """渲染 GameTest AI 统一侧边栏。"""

    with st.sidebar:

        # 品牌区域
        st.html("""
        <div class="gt-sidebar-brand">
            <div class="gt-sidebar-brand-title">
                <span class="gt-sidebar-brand-icon">🎮</span>
                <span>GameTest AI</span>
            </div>
            <div class="gt-sidebar-brand-subtitle">
                AI 驱动的智能游戏测试平台
            </div>
        </div>
        """)

        # 导航区域
        for group_name, group_pages in pages.items():

            if group_name == "隐藏页面":
                continue

            if group_name:
                st.html(f"""
                <div class="gt-sidebar-group-title">
                    {group_name}
                </div>
                """)

            for page in group_pages:
                st.page_link(
                    page,
                    label=page.title,
                    icon=page.icon,
                    width="stretch",
                )

        st.divider()

        # 产品介绍
        st.html("""
        <div class="gt-sidebar-product">
            <div class="gt-sidebar-product-title">
                ✨ AI Testing
            </div>
            <div class="gt-sidebar-product-description">
                从项目管理、需求分析到测试点与测试用例，
                构建完整的智能游戏测试工作流。
            </div>
        </div>

        <div class="gt-sidebar-footer">
            GameTest AI · V1.0
        </div>
        """)
