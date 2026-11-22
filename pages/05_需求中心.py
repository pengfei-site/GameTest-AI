import streamlit as st
from components.header import render_header
from components.requirement_center import (
    render_document_tab,
    render_analysis_tab,
    render_version_tab,
)

render_header(
    title="需求中心",
    description="统一管理需求文档、结构化需求分析与需求版本。",
    breadcrumb=["需求中心"],
)

document_tab, analysis_tab, version_tab = st.tabs([
    "需求文档",
    "结构化需求分析",
    "版本管理",
])

with document_tab:
    render_document_tab()

with analysis_tab:
    render_analysis_tab()

with version_tab:
    render_version_tab()
