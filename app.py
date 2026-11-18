
import streamlit as st
from pathlib import Path

from components.navigation import get_pages
from components.sidebar import render_sidebar


# ============================================================
# 一、基础页面配置
# ============================================================

st.set_page_config(
    page_title="GameTest AI",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 二、加载全局 CSS
# ============================================================

BASE_DIR = Path(__file__).parent
CSS_PATH = BASE_DIR / "styles" / "main.css"

if CSS_PATH.exists():
    css = CSS_PATH.read_text(encoding="utf-8")

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )


# ============================================================
# 三、注册页面路由
# ============================================================

pages = get_pages()


# ============================================================
# 四、启动 Streamlit 路由
# ============================================================

current_page = st.navigation(
    pages,
    position="hidden",
)


# ============================================================
# 五、渲染统一侧边栏
# ============================================================

render_sidebar(pages)


# ============================================================
# 六、执行当前页面
# ============================================================

current_page.run()
