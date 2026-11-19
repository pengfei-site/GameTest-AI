
import html
import streamlit as st

from database.repositories.dashboard_repository import (
    get_dashboard_statistics,
)
from database.repositories.project_repository import (
    list_projects,
)
from components.header import render_header


# ============================================================
# 一、首页专属样式
# ============================================================

st.html("""
<style>
/* ------------------------------------------------------------
   欢迎区域
   ------------------------------------------------------------ */

.home-hero {
    position: relative;
    overflow: hidden;
    padding: 34px 38px;
    border-radius: 18px;
    background: linear-gradient(
        120deg,
        #f0edff 0%,
        #f8f7ff 65%,
        #ffffff 100%
    );
    border: 1px solid #e8e3ff;
    margin-bottom: 30px;
}

.hero-tag {
    display: inline-block;
    padding: 5px 11px;
    border-radius: 20px;
    background: #e7e2ff;
    color: #6254c7;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.6px;
    margin-bottom: 15px;
}

.hero-title {
    color: #292746;
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.7px;
    line-height: 1.5;
    margin-bottom: 10px;
}

.hero-desc {
    color: #74728a;
    font-size: 14px;
    line-height: 1.9;
    max-width: 760px;
}

.hero-highlight {
    color: #6254c7;
    font-weight: 700;
}


/* ------------------------------------------------------------
   区域标题
   ------------------------------------------------------------ */

.section-title {
    color: #29263e;
    font-size: 18px;
    font-weight: 750;
    margin-top: 8px;
    margin-bottom: 5px;
}

.section-desc {
    color: #9292a5;
    font-size: 12px;
    line-height: 1.7;
    margin-bottom: 17px;
}


/* ------------------------------------------------------------
   统计卡片
   ------------------------------------------------------------ */

.metric-card {
    background: #ffffff;
    border: 1px solid #e9eaf2;
    border-radius: 14px;
    padding: 19px 20px;
    min-height: 112px;
    box-shadow: 0 2px 8px rgba(32, 35, 75, 0.035);
    transition: all 0.18s ease;
}

.metric-card:hover {
    border-color: #dcd7f7;
    box-shadow: 0 5px 16px rgba(32, 35, 75, 0.06);
}

.metric-label {
    color: #85869b;
    font-size: 12px;
    font-weight: 550;
    margin-bottom: 13px;
}

.metric-value {
    color: #302b54;
    font-size: 29px;
    font-weight: 800;
    line-height: 1.2;
}


/* ------------------------------------------------------------
   项目卡片
   ------------------------------------------------------------ */

.project-name {
    color: #302b54;
    font-size: 16px;
    font-weight: 750;
    margin-bottom: 9px;
}

.project-description {
    color: #77798d;
    font-size: 13px;
    line-height: 1.8;
    overflow-wrap: anywhere;
}

.project-meta {
    color: #999bad;
    font-size: 11px;
    line-height: 1.8;
    margin-top: 12px;
}


/* ------------------------------------------------------------
   工作流卡片
   ------------------------------------------------------------ */

.workflow-card {
    background: #ffffff;
    border: 1px solid #e9eaf2;
    border-radius: 14px;
    padding: 18px 16px;
    min-height: 135px;
    box-shadow: 0 2px 8px rgba(32, 35, 75, 0.035);
    transition: all 0.18s ease;
}

.workflow-card:hover {
    border-color: #dcd7f7;
    transform: translateY(-2px);
}

.workflow-number {
    color: #8c80ce;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.7px;
    margin-bottom: 13px;
}

.workflow-name {
    color: #302b54;
    font-size: 14px;
    font-weight: 750;
    margin-bottom: 8px;
}

.workflow-desc {
    color: #85869b;
    font-size: 12px;
    line-height: 1.8;
}


/* ------------------------------------------------------------
   快捷入口
   ------------------------------------------------------------ */

.feature-icon {
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f0edff;
    border-radius: 11px;
    font-size: 22px;
    margin-bottom: 14px;
}

.feature-name {
    color: #302b54;
    font-size: 15px;
    font-weight: 750;
    margin-bottom: 7px;
}

.feature-desc {
    color: #85869b;
    font-size: 12px;
    line-height: 1.8;
    min-height: 44px;
    margin-bottom: 12px;
}


/* ------------------------------------------------------------
   首页分隔线与页脚
   ------------------------------------------------------------ */

.home-footer {
    text-align: center;
    color: #a0a1b1;
    font-size: 11px;
    padding: 12px 0;
}


/* ------------------------------------------------------------
   小屏适配
   ------------------------------------------------------------ */

@media (max-width: 700px) {
    .home-hero {
        padding: 25px 22px;
    }

    .hero-title {
        font-size: 23px;
    }

    .metric-card {
        padding: 15px;
    }

    .metric-value {
        font-size: 25px;
    }

    .workflow-card {
        padding: 15px;
    }
}
</style>
""")


# ============================================================
# 二、统一页面标题
# ============================================================

render_header(
    title="智能游戏测试工作台",
    description="欢迎使用 GameTest AI，从项目管理到 AI 测试用例生成，统一管理游戏测试工作流。",
    breadcrumb=["工作空间", "首页"],
)


# ============================================================
# 三、欢迎区域
# ============================================================

st.html("""
<div class="home-hero">
    <div class="hero-tag">
        ✨ AI POWERED GAME TESTING
    </div>

    <div class="hero-title">
        让游戏测试更智能、更高效
    </div>

    <div class="hero-desc">
        从游戏项目管理开始，逐步完成需求文档导入、
        结构化需求分析、AI 测试点生成、
        AI 测试用例生成与质量管理，
        构建完整的
        <span class="hero-highlight">智能游戏测试工作流</span>。
    </div>
</div>
""")


# ============================================================
# 四、业务数据统计
# ============================================================

st.markdown(
    """
    <div class="section-title">📊 业务数据总览</div>
    <div class="section-desc">
        了解当前平台的项目与测试资产情况
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    stats = get_dashboard_statistics()

    metrics = [
        ("进行中项目", stats["active_project_count"], "📁"),
        ("需求文档", stats["document_count"], "📄"),
        ("需求分析记录", stats["requirement_analysis_count"], "🧠"),
        ("测试点生成批次", stats["generation_batch_count"], "🎯"),
        ("测试点数量", stats["test_point_count"], "📋"),
        ("已归档项目", stats["archived_project_count"], "📦"),
    ]

    metric_cols = st.columns(3)

    for index, (label, value, icon) in enumerate(metrics):
        with metric_cols[index % 3]:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">
                        {icon} {label}
                    </div>
                    <div class="metric-value">
                        {value}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

except Exception as exc:
    st.error(f"业务统计数据读取失败：{exc}")


st.divider()


# ============================================================
# 五、我的游戏项目
# ============================================================

st.markdown(
    """
    <div class="section-title">📁 我的游戏项目</div>
    <div class="section-desc">
        查看当前游戏项目，快速进入对应业务中心
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    projects = list_projects()

    if not projects:
        st.info(
            "目前还没有游戏项目，先创建一个项目，开启智能测试之旅。"
        )

        st.page_link(
            "pages/01_项目列表.py",
            label="前往项目中心",
            icon="📁",
            width="stretch",
        )

    else:
        st.caption(f"当前共有 {len(projects)} 个项目")

        for project in projects:

            project_name = html.escape(
                str(project.get("name") or "未命名项目")
            )

            project_description = html.escape(
                str(project.get("description") or "暂无项目描述")
            )

            created_at = html.escape(
                str(project.get("created_at") or "未知")
            )

            updated_at = html.escape(
                str(project.get("updated_at") or "未知")
            )

            with st.container(border=True):

                col_info, col_action = st.columns([3, 1])

                with col_info:
                    st.markdown(
                        f"""
                        <div class="project-name">
                            🎮 {project_name}
                        </div>

                        <div class="project-description">
                            {project_description}
                        </div>

                        <div class="project-meta">
                            创建时间：{created_at}
                            &nbsp; | &nbsp;
                            最近更新：{updated_at}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with col_action:
                    st.page_link(
                        "pages/05_需求文档.py",
                        label="需求中心",
                        icon="📄",
                        width="stretch",
                    )

                    st.page_link(
                        "pages/08_测试点列表.py",
                        label="测试点中心",
                        icon="🎯",
                        width="stretch",
                    )

                    st.page_link(
                        "pages/11_AI测试用例生成.py",
                        label="测试用例中心",
                        icon="📋",
                        width="stretch",
                    )

except Exception as exc:
    st.error(f"项目列表读取失败：{exc}")


st.divider()


# ============================================================
# 六、核心业务工作流
# ============================================================

st.markdown(
    """
    <div class="section-title">🔄 核心业务工作流</div>
    <div class="section-desc">
        从项目创建到测试用例管理，逐步完成智能游戏测试
    </div>
    """,
    unsafe_allow_html=True,
)

workflow = [
    {
        "number": "STEP 01",
        "name": "项目管理",
        "description": "创建游戏项目，维护项目基础信息。",
        "icon": "📁",
    },
    {
        "number": "STEP 02",
        "name": "需求分析",
        "description": "导入需求文档，完成结构化需求分析。",
        "icon": "📄",
    },
    {
        "number": "STEP 03",
        "name": "测试点生成",
        "description": "根据需求内容生成和管理测试点。",
        "icon": "🎯",
    },
    {
        "number": "STEP 04",
        "name": "测试用例生成",
        "description": "根据测试点生成结构化测试用例。",
        "icon": "🧪",
    },
]

workflow_cols = st.columns(4)

for col, item in zip(workflow_cols, workflow):
    with col:
        st.html(
            f"""
            <div class="workflow-card">
                <div class="workflow-number">
                    {item["number"]}
                </div>

                <div class="workflow-name">
                    {item["icon"]} {item["name"]}
                </div>

                <div class="workflow-desc">
                    {item["description"]}
                </div>
            </div>
            """
        )


st.divider()


# ============================================================
# 七、业务功能入口
# ============================================================

st.markdown(
    """
    <div class="section-title">🚀 快捷功能入口</div>
    <div class="section-desc">
        选择业务中心，继续你的游戏测试工作
    </div>
    """,
    unsafe_allow_html=True,
)

features = [
    {
        "title": "项目中心",
        "description": "创建、编辑、查询和归档游戏测试项目。",
        "path": "pages/01_项目列表.py",
        "icon": "📁",
    },
    {
        "title": "需求中心",
        "description": "管理需求文档、结构化需求分析和版本。",
        "path": "pages/05_需求文档.py",
        "icon": "📄",
    },
    {
        "title": "测试点中心",
        "description": "生成、审核和管理 AI 测试点及批次。",
        "path": "pages/08_测试点列表.py",
        "icon": "🎯",
    },
    {
        "title": "测试用例中心",
        "description": "生成和管理结构化游戏测试用例。",
        "path": "pages/11_AI测试用例生成.py",
        "icon": "📋",
    },
]

for start in range(0, len(features), 2):

    cols = st.columns(2)

    for col, feature in zip(cols, features[start:start + 2]):

        with col:
            with st.container(border=True):

                st.markdown(
                    f"""
                    <div class="feature-icon">
                        {feature["icon"]}
                    </div>

                    <div class="feature-name">
                        {feature["title"]}
                    </div>

                    <div class="feature-desc">
                        {feature["description"]}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.page_link(
                    feature["path"],
                    label=f'进入{feature["title"]}',
                    width="stretch",
                )


# ============================================================
# 八、页脚
# ============================================================

st.divider()

st.markdown(
    """
    <div class="home-footer">
        GameTest AI · AI 驱动的智能游戏测试平台
    </div>
    """,
    unsafe_allow_html=True,
)
