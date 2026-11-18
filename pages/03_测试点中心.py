
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
    <div class="center-title">🎯 测试点中心</div>
    <div class="center-desc">
        统一管理游戏测试点，从需求分析结果出发，<br>
        使用 AI 自动生成测试点，并对生成批次和测试点进行管理。
    </div>
</div>
""", unsafe_allow_html=True)


# 项目选择区域
st.markdown("### 当前工作项目")

# TODO：后续接入现有项目选择逻辑
st.info("项目选择功能将在测试点中心功能迁移阶段接入。")


st.divider()


# 二级导航
tab_list, tab_generate, tab_batches = st.tabs([
    "📋 测试点列表",
    "✨ AI 测试点生成",
    "📚 批次管理",
])


with tab_list:
    st.markdown("### 测试点管理")
    st.caption("统一查看、筛选和维护已生成的测试点。")

    with st.container(border=True):
        st.markdown("#### 测试点工作区")
        st.info(
            "此区域用于迁移原「测试点管理」页面的功能，"
            "包括测试点列表、筛选、详情和状态维护。"
        )


with tab_generate:
    st.markdown("### AI 测试点生成")
    st.caption("基于结构化需求分析结果生成游戏测试点。")

    with st.container(border=True):
        st.markdown("#### AI 生成工作区")
        st.info(
            "此区域用于迁移原「测试点生成」页面的功能，"
            "包括需求选择、生成配置和生成结果。"
        )


with tab_batches:
    st.markdown("### 测试点批次管理")
    st.caption("集中查看不同需求和不同批次产生的测试点。")

    with st.container(border=True):
        st.markdown("#### 批次工作区")
        st.info(
            "此区域用于迁移原「测试点批次管理」页面的功能，"
            "包括批次列表、批次详情和批次状态。"
        )


st.divider()
st.caption("GameTest AI · 测试点中心")
