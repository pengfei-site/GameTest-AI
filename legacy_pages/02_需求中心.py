
import streamlit as st


st.markdown("""
<style>
.center-hero {
    background: linear-gradient(120deg, #34256f, #6652bd 55%, #8974dc);
    padding: 28px 32px;
    border-radius: 20px;
    margin-bottom: 24px;
}
.center-title {
    color: #fff !important;
    font-size: 30px;
    font-weight: 850;
    margin-bottom: 8px;
}
.center-desc {
    color: #f0ebff !important;
    font-size: 14px;
    line-height: 1.9;
}
.section-title {
    color: #30265f;
    font-size: 20px;
    font-weight: 800;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #eeeafd;
    border-radius: 16px;
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="center-hero">
    <div class="center-title">📄 需求中心</div>
    <div class="center-desc">
        统一管理游戏需求文档，完成需求结构化分析。<br>
        从原始需求到结构化需求，为后续测试点生成提供基础。
    </div>
</div>
""", unsafe_allow_html=True)


# 项目选择区域
st.markdown("### 当前工作项目")

# TODO：后续接入现有项目选择逻辑
st.info("项目选择功能将在需求中心功能迁移阶段接入。")


st.divider()


# 二级导航
tab_documents, tab_analysis, tab_versions = st.tabs([
    "📚 需求文档",
    "🧠 结构化需求分析",
    "🕘 版本管理",
])


with tab_documents:
    st.markdown("### 需求文档管理")
    st.caption("管理游戏需求文档，支持文档导入、查看和维护。")

    with st.container(border=True):
        st.markdown("#### 文档工作区")
        st.info(
            "此区域用于迁移原「需求文档」页面的功能，"
            "包括文档上传、文档列表和文档详情。"
        )


with tab_analysis:
    st.markdown("### 结构化需求分析")
    st.caption("将原始需求整理为结构化、可测试的需求信息。")

    with st.container(border=True):
        st.markdown("#### AI 需求分析工作区")
        st.info(
            "此区域用于迁移原「结构化需求分析」页面的功能，"
            "包括分析任务、分析结果和需求详情。"
        )


with tab_versions:
    st.markdown("### 需求版本管理")
    st.caption("统一查看和管理需求文档的历史版本。")

    with st.container(border=True):
        st.markdown("#### 版本工作区")
        st.info(
            "此区域用于展示需求文档版本及历史记录，"
            "后续接入原有版本管理功能。"
        )


st.divider()
st.caption("GameTest AI · 需求中心")
