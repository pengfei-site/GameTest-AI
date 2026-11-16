
import streamlit as st

from database.repositories.dashboard_repository import (
    get_dashboard_statistics,
)
from database.repositories.project_repository import (
    list_projects,
)


st.set_page_config(
    page_title="GameTest AI",
    page_icon="🎮",
    layout="wide",
)

st.title("🎮 GameTest AI")
st.caption("智能游戏测试用例生成平台 · 项目工作台")

st.divider()

# ============================================================
# 一、欢迎区域
# ============================================================

st.header("工作台")

st.markdown(
    """
    欢迎使用 GameTest AI。

    从游戏项目开始，完成需求文档导入、结构化需求分析、
    AI 测试点生成、AI 测试用例生成、质量检查和测试用例导出。
    """
)

# ============================================================
# 二、业务统计
# ============================================================

st.subheader("业务数据统计")

try:
    stats = get_dashboard_statistics()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "进行中项目",
        stats["active_project_count"],
    )

    col2.metric(
        "需求文档",
        stats["document_count"],
        help=f'有效文档版本：{stats["document_version_count"]}',
    )

    col3.metric(
        "需求分析记录",
        stats["requirement_analysis_count"],
    )

    col4, col5, col6 = st.columns(3)

    col4.metric(
        "测试点生成批次",
        stats["generation_batch_count"],
    )

    col5.metric(
        "测试点数量",
        stats["test_point_count"],
    )

    col6.metric(
        "已归档项目",
        stats["archived_project_count"],
    )

except Exception as exc:
    st.error(f"业务统计数据读取失败：{exc}")

st.divider()

# ============================================================
# 三、项目工作区
# ============================================================

st.subheader("我的游戏项目")

try:
    projects = list_projects()

    if not projects:
        st.info(
            "当前还没有进行中的游戏项目。"
            "请先创建项目，再开始需求分析和测试用例生成。"
        )

        st.page_link(
            "pages/01_项目管理.py",
            label="前往项目管理，创建第一个项目",
            icon="📁",
            use_container_width=True,
        )

    else:
        st.write(f"当前共有 **{len(projects)}** 个进行中的项目。")

        for project in projects:
            with st.container(border=True):
                col_info, col_action = st.columns([4, 1])

                with col_info:
                    st.markdown(f'### {project["name"]}')

                    st.write(
                        project.get("description") or "暂无项目描述"
                    )

                    st.caption(
                        f'创建时间：{project.get("created_at", "未知")} '
                        f'| 最近更新：{project.get("updated_at", "未知")}'
                    )

                with col_action:
                    st.page_link(
                        "pages/02_需求文档.py",
                        label="需求文档",
                        icon="📄",
                        use_container_width=True,
                    )

                    st.page_link(
                        "pages/03_结构化需求分析.py",
                        label="需求分析",
                        icon="🧠",
                        use_container_width=True,
                    )

                    st.page_link(
                        "pages/07_AI测试用例生成.py",
                        label="生成用例",
                        icon="🧪",
                        use_container_width=True,
                    )

except Exception as exc:
    st.error(f"项目列表读取失败：{exc}")

st.divider()

# ============================================================
# 四、业务功能导航
# ============================================================

st.subheader("业务功能入口")

pages = [
    {
        "title": "项目管理",
        "description": "创建、编辑、归档和恢复游戏测试项目。",
        "path": "pages/01_项目管理.py",
        "icon": "📁",
    },
    {
        "title": "需求文档",
        "description": "导入策划文档、解析内容和管理文档版本。",
        "path": "pages/02_需求文档.py",
        "icon": "📄",
    },
    {
        "title": "结构化需求分析",
        "description": "通过 AI 分析需求并保存结构化分析结果。",
        "path": "pages/03_结构化需求分析.py",
        "icon": "🧠",
    },
    {
        "title": "测试点生成",
        "description": "根据结构化需求生成 AI 测试点。",
        "path": "pages/04_测试点生成.py",
        "icon": "🎯",
    },
    {
        "title": "测试点批次管理",
        "description": "查看测试点生成批次、质量报告和历史记录。",
        "path": "pages/05_测试点批次管理.py",
        "icon": "📚",
    },
    {
        "title": "测试点管理",
        "description": "编辑、审核和管理 AI 生成的测试点。",
        "path": "pages/06_测试点管理.py",
        "icon": "✅",
    },
    {
        "title": "AI 测试用例生成",
        "description": "根据测试点生成结构化测试用例。",
        "path": "pages/07_AI测试用例生成.py",
        "icon": "🧪",
    },
    {
        "title": "测试用例管理",
        "description": "管理候选用例、质量复检、人工确认和导出。",
        "path": "pages/08_测试用例管理.py",
        "icon": "📋",
    },
]

for start in range(0, len(pages), 2):
    col1, col2 = st.columns(2)

    for col, page in zip(
        [col1, col2],
        pages[start:start + 2],
    ):
        with col:
            with st.container(border=True):
                st.markdown(f'### {page["icon"]} {page["title"]}')
                st.write(page["description"])

                st.page_link(
                    page["path"],
                    label=f'进入{page["title"]}',
                    use_container_width=True,
                )

st.divider()

st.caption("GameTest AI · V1 项目工作台")
