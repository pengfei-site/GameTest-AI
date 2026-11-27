 
import streamlit as st


def get_pages():
    pages = {
        "" : [
            st.Page(
                "pages/00_首页.py",
                title="首页",
                icon="🏠",
                default=True,
                url_path="home",
            ),
            st.Page(
                "pages/01_项目列表.py",
                title="项目中心",
                icon="📚",
                url_path="project-center",
            ),
            st.Page(
                "pages/05_需求文档.py",
                title="需求中心",
                icon="📄",
                url_path="requirement-center",
            ),
        ],

        "AI 测试中心": [
            st.Page(
                "pages/08_测试点中心.py",
                title="测试点中心",
                icon="🎯",
                url_path="test-point-list",
            ),
            st.Page(
                "pages/09_AI测试点生成.py",
                title="AI 测试点生成",
                icon="✨",
                url_path="ai-test-point-generation",
            ),
            st.Page(
                "pages/10_测试点批次管理.py",
                title="测试点批次管理",
                icon="📦",
                url_path="test-point-batch-management",
            ),
            st.Page(
                "pages/11_AI测试用例生成.py",
                title="AI测试用例生成",
                icon="🤖",
                url_path="ai-test-case-generation",
            ),
            st.Page(
                "pages/12_测试用例管理.py",
                title="测试用例管理",
                icon="📋",
                url_path="test-case-management",
            ),
        ],

        "隐藏页面": [
            st.Page(
                "pages/14_需求详情.py",
                title="需求详情",
                icon="📄",
                url_path="requirement-detail",
            ),
            st.Page(
                "pages/13_项目详情.py",
                title="项目详情",
                icon="📊",
                url_path="project-detail",
            ),
        ],
    }

    return pages
