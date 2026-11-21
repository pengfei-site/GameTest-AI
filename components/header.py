import html

import streamlit as st


def render_header(title, description="", breadcrumb=None, actions=None):
    """渲染 GameTest AI 统一业务页面标题。"""

    # 面包屑
    if breadcrumb:
        breadcrumb_items = [
            html.escape(str(item))
            for item in breadcrumb
        ]

        breadcrumb_text = (
            '<span class="gt-breadcrumb-separator">/</span>'
        ).join(breadcrumb_items)

        st.html(f"""
        <div class="gt-breadcrumb">
            {breadcrumb_text}
        </div>
        """)

    safe_title = html.escape(str(title))
    safe_description = html.escape(str(description))

    description_html = ""

    if description:
        description_html = f"""
        <div class="gt-page-description">
            {safe_description}
        </div>
        """

    # 左右两列：左侧标题，右侧操作
    if actions is not None:

        title_col, action_col = st.columns(
            [3, 2],
            vertical_alignment="center",
            gap="large",
        )

        with title_col:
            st.html(f"""
            <div class="gt-page-header">
                <div class="gt-page-title">
                    {safe_title}
                </div>
                {description_html}
            </div>
            """)

        with action_col:
            actions()

    else:
        st.html(f"""
        <div class="gt-page-header">
            <div class="gt-page-title">
                {safe_title}
            </div>
            {description_html}
        </div>
        """)