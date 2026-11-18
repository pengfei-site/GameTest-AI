
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
    <div class="center-title">📋 测试用例中心</div>
    <div class="center-desc">
        构建智能测试用例生成与管理工作区。<br>
        根据测试点生成测试用例，并统一维护、查看和管理测试用例。
    </div>
</div>
""", unsafe_allow_html=True)


# 项目选择区域
st.markdown("### 当前工作项目")

# TODO：后续接入现有项目选择逻辑
st.info("项目选择功能将在测试用例中心功能迁移阶段接入。")


st.divider()


# 二级导航
tab_generate, tab_manage = st.tabs([
    "✨ AI 测试用例生成",
    "📚 测试用例管理",
])


with tab_generate:
    st.markdown("### AI 测试用例生成")
    st.caption("基于测试点自动生成结构化测试用例。")

    with st.container(border=True):
        st.markdown("#### AI 用例生成工作区")
        st.info(
            "此区域用于迁移原「AI 测试用例生成」页面的功能，"
            "包括测试点选择、生成配置和用例生成结果。"
        )


with tab_manage:
    st.markdown("### 测试用例管理")
    st.caption("统一查看、筛选和维护游戏测试用例。")

    with st.container(border=True):
        st.markdown("#### 测试用例工作区")
        st.info(
            "此区域用于迁移原「测试用例管理」页面的功能，"
            "包括用例列表、用例详情、编辑和状态管理。"
        )


st.divider()
st.caption("GameTest AI · 测试用例中心")
