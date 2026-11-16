
import streamlit as st

from database.repositories.dashboard_repository import (
    get_dashboard_statistics,
)

st.set_page_config(
    page_title="GameTest AI",
    page_icon="🎮",
    layout="wide",
)

st.title("🎮 GameTest AI")
st.caption("智能游戏测试用例生成平台")

st.divider()

st.header("平台总览")

st.markdown("""
欢迎使用 GameTest AI。

本平台用于辅助游戏测试工作，逐步实现从需求文档导入、
需求分析到测试点生成与管理的完整流程。
""")

# 获取数据库统计数据
try:
    stats = get_dashboard_statistics()

    st.subheader("业务数据统计")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "活跃项目",
            stats["active_project_count"],
            help="当前未归档的项目数量",
        )

    with col2:
        st.metric(
            "需求文档",
            stats["document_count"],
            help=f'有效文档版本：{stats["document_version_count"]}',
        )

    with col3:
        st.metric(
            "需求分析记录",
            stats["requirement_analysis_count"],
        )

    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric(
            "生成批次",
            stats["generation_batch_count"],
        )

    with col5:
        st.metric(
            "测试点",
            stats["test_point_count"],
        )

    with col6:
        st.metric(
            "已归档项目",
            stats["archived_project_count"],
        )

except Exception as e:
    st.error(f"首页统计数据读取失败：{e}")

st.divider()

st.subheader("功能模块")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 01 · 项目管理")
    st.write("管理游戏测试项目及项目信息。")
    st.caption("规划中")

with col2:
    st.markdown("### 02 · 需求文档")
    st.write("导入需求文档，解析并保存文档版本。")
    st.caption("已实现")

col3, col4 = st.columns(2)

with col3:
    st.markdown("### 03 · AI 需求分析")
    st.write("通过 AI 辅助理解和分析需求内容。")
    st.caption("已有体验页面")

with col4:
    st.markdown("### 04 · 结构化需求分析")
    st.write("管理结构化需求分析结果。")
    st.caption("已有页面")

st.divider()

st.info("请通过左侧导航栏进入对应的功能页面。")
