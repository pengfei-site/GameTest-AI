
import html

import streamlit as st


def render_header(title, description="", breadcrumb=None):
    """渲染 GameTest AI 统一业务页面标题。"""

    safe_title = html.escape(str(title))
    safe_description = html.escape(str(description))

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

    # 页面标题
    description_html = ""

    if description:
        description_html = f"""
        <div class="gt-page-description">
            {safe_description}
        </div>
        """

    st.html(f"""
    <div class="gt-page-header">
        <div class="gt-page-title">
            {safe_title}
        </div>
        {description_html}
    </div>
    """)
