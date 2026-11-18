

import streamlit as st


def render_header(title, description="", breadcrumb=None):
    """渲染 GameTest AI 统一业务页面标题。"""

    if breadcrumb:
        breadcrumb_text = " / ".join(breadcrumb)

        st.html(f"""
        <div style="
            font-size:12px;
            color:#928ba9;
            margin-bottom:10px;
        ">
            {breadcrumb_text}
        </div>
        """)

    st.html(f"""
    <div style="margin-bottom:24px;">
        <div style="
            font-size:28px;
            font-weight:800;
            color:#292541;
            letter-spacing:-0.5px;
        ">
            {title}
        </div>

        <div style="
            font-size:14px;
            color:#85819a;
            margin-top:8px;
            line-height:1.7;
        ">
            {description}
        </div>
    </div>
    """)
