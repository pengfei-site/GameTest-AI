 
import streamlit as st


def get_pages():
    pages = {
        "工作空间": [
            st.Page(
                "pages/00_首页.py",
                title="首页",
                icon="🏠",
                default=True,
                url_path="home",
            ),
        ],

        "项目中心": [
            st.Page(
                "pages/01_项目列表.py",
                title="项目列表",
                icon="📚",
                url_path="project-list",
            ),
            st.Page(
                "pages/02_项目创建.py",
                title="创建项目",
                icon="✨",
                url_path="project-create",
            ),
        ],

        "需求中心": [
            st.Page(
                "pages/05_需求文档.py",
                title="需求文档",
                icon="📄",
                url_path="requirement-documents",
            ),
            st.Page(
                "pages/06_结构化需求分析.py",
                title="结构化需求分析",
                icon="🧠",
                url_path="structured-requirement-analysis",
            ),
            st.Page(
                "pages/07_需求版本管理.py",
                title="需求版本管理",
                icon="🕘",
                url_path="requirement-versions",
            ),
        ],

        "AI 测试中心": [
            st.Page(
                "pages/08_测试点列表.py",
                title="测试点列表",
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
                "pages/13_项目详情.py",
                title="项目详情",
                icon="📊",
                url_path="project-detail",
            ),
        ],
    }

    return pages
