import html

import plotly.graph_objects as go
import streamlit as st

from database.repositories.dashboard_repository import (
    get_homepage_chart_data,
)

from components.header import render_header


# ============================================================
# 一、首页专属样式
# ============================================================

st.html("""
<style>
.section-title {
    color: #1E293B;
    font-size: 18px;
    font-weight: 750;
    margin-top: 8px;
    margin-bottom: 5px;
}
.section-desc {
    color: #64748B;
    font-size: 12px;
    line-height: 1.7;
    margin-bottom: 17px;
}
.metric-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 19px 20px;
    min-height: 112px;
    box-shadow: 0 2px 8px rgba(30, 41, 59, 0.035);
    transition: all 0.18s ease;
}
.metric-card:hover {
    border-color: #BFDBFE;
    box-shadow: 0 5px 16px rgba(30, 41, 59, 0.07);
}
.metric-label {
    color: #64748B;
    font-size: 14px;
    font-weight: 650;
    margin-bottom: 13px;
}
.metric-value {
    color: #1E293B;
    font-size: 29px;
    font-weight: 800;
    line-height: 1.2;
}
.review-card {
    min-height: 115px;
    padding: 14px 18px;
}

.review-title {
    color: #64748B;
    font-size: 14px;
    font-weight: 650;
    margin-bottom: 13px;
}

.review-summary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-bottom: 12px;
    font-size: 13px;
}

.review-approved {
    color: #16A34A;
    font-weight: 650;
}

.review-count {
    color: #1E293B;
    font-weight: 800;
    font-size: 20px;
}

.review-progress-row {
    display: flex;
    align-items: center;
    gap: 10px;
}

.review-progress-track {
    flex: 1;
    height: 7px;
    overflow: hidden;
    background: #E2E8F0;
    border-radius: 8px;
}

.review-progress-fill {
    height: 100%;
    background: #22C55E;
    border-radius: 8px;
}

.review-percent {
    min-width: 42px;
    color: #16A34A;
    font-size: 12px;
    font-weight: 700;
    text-align: right;
}
.review-status-row strong {
    color: #1E293B;
    font-weight: 700;
}
.workflow-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 18px 16px;
    min-height: 135px;
    box-shadow: 0 2px 8px rgba(30, 41, 59, 0.035);
    transition: all 0.18s ease;
}
.workflow-card:hover {
    border-color: #BFDBFE;
    transform: translateY(-2px);
}
.workflow-number {
    color: #3B82F6;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.7px;
    margin-bottom: 13px;
}
.workflow-name {
    color: #1E293B;
    font-size: 14px;
    font-weight: 750;
    margin-bottom: 8px;
}
.workflow-desc {
    color: #64748B;
    font-size: 12px;
    line-height: 1.8;
}
.feature-icon {
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #EFF6FF;
    border-radius: 11px;
    font-size: 22px;
    margin-bottom: 14px;
}
.feature-name {
    color: #1E293B;
    font-size: 15px;
    font-weight: 750;
    margin-bottom: 7px;
}
.feature-desc {
    color: #64748B;
    font-size: 12px;
    line-height: 1.8;
    min-height: 44px;
    margin-bottom: 12px;
}
.home-footer {
    text-align: center;
    color: #94A3B8;
    font-size: 11px;
    padding: 12px 0;
}
@media (max-width: 700px) {
    .metric-card { padding: 15px; }
    .metric-value { font-size: 25px; }
    .workflow-card { padding: 15px; }
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
# 三、业务数据统计、人工审核进度与图表
# ============================================================

try:
    dashboard_data = get_homepage_chart_data()
    stats = dashboard_data["statistics"]
    review_data = dashboard_data["review_progress"]

    metrics = [
        ("游戏项目总数", stats["project_count"], "🎮"),
        ("需求文档数量", stats["document_count"], "📄"),
        ("有效测试点数量", stats["test_point_count"], "🎯"),
        ("测试用例数量", stats["test_case_count"], "📋"),
    ]

    metric_cols = st.columns(4)
    for col, (label, value, icon) in zip(metric_cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{icon} {label}</div>
                    <div class="metric-value">{value:,}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.write("")

    review_cols = st.columns(2)
    review_configs = [
        (review_cols[0], "测试点人工审核", review_data["test_points"]),
        (review_cols[1], "测试用例人工审核", review_data["test_cases"]),
    ]
    status_labels = {
        "approved": "已通过",
        "pending": "待审核",
        "rejected": "已驳回",
        "unknown": "未知状态",
    }

    for col, title, records in review_configs:
        total = sum(item["count"] for item in records)
        approved = sum(
            item["count"] for item in records
            if item["review_status"] == "approved"
        )
        progress = approved / total if total else 0

        with col:
            st.html(
                f"""
                <div class="metric-card review-card">
                    <div class="review-title">{title}</div>

                    <div class="review-summary">
                        <span class="review-approved">✓ 已通过</span>
                        <span class="review-count">
                            {approved:,} / {total:,}
                        </span>
                    </div>

                    <div class="review-progress-row">
                        <div class="review-progress-track">
                            <div
                                class="review-progress-fill"
                                style="width: {progress * 100:.1f}%;">
                            </div>
                        </div>
                        <span class="review-percent">
                            {progress * 100:.0f}%
                        </span>
                    </div>
                </div>
                """,
            )

    st.divider()

    # -------------------- 图表一：项目状态分布 --------------------
    chart_col1, chart_col2 = st.columns(2)

    project_status = dashboard_data["project_status"]
    status_name_map = {"active": "进行中", "archived": "已归档"}
    status_labels_chart = [
        status_name_map.get(item["status"], str(item["status"]))
        for item in project_status
    ]
    status_values = [item["count"] for item in project_status]

    with chart_col1:
        with st.container(border=True):
            st.markdown("**项目状态分布**")
            if sum(status_values) > 0:
                fig = go.Figure(
                    go.Pie(
                        labels=status_labels_chart,
                        values=status_values,
                        hole=0.62,
                        textinfo="label+percent",
                        hovertemplate="%{label}<br>项目数：%{value}<br>占比：%{percent}<extra></extra>",
                        marker={"colors": ["#3B82F6", "#94A3B8", "#8B5CF6", "#06B6D4"]},
                    )
                )
                fig.update_layout(
                    height=310,
                    margin={"l": 10, "r": 10, "t": 20, "b": 10},
                    showlegend=True,
                    legend={"orientation": "h", "y": -0.08},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("暂无项目数据")

    # -------------------- 图表二：测试资产统计 --------------------
    asset_statistics = dashboard_data["asset_statistics"]
    with chart_col2:
        with st.container(border=True):
            st.markdown("**测试资产统计**")
            if asset_statistics:
                asset_names = [item["asset_type"] for item in asset_statistics]
                asset_values = [item["count"] for item in asset_statistics]
                fig = go.Figure(
                    go.Bar(
                        x=asset_names,
                        y=asset_values,
                        marker_color=["#3B82F6", "#06B6D4", "#8B5CF6", "#22C55E"],
                        text=asset_values,
                        textposition="outside",
                        hovertemplate="%{x}<br>数量：%{y:,}<extra></extra>",
                        width=0.25,
                        marker_line_width=0,
                    )
                )
                fig.update_layout(
                    height=310,
                    margin={"l": 15, "r": 15, "t": 25, "b": 20},
                    yaxis={"title": "数量", "rangemode": "tozero", "gridcolor": "#E2E8F0"},
                    xaxis={"title": ""},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    bargap=0.55,
                    barcornerradius=6,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("暂无测试资产数据")

    # -------------------- 图表三、四：审核进度与工作流分布 --------------------
    chart_col3, chart_col4 = st.columns(2)

    point_records = review_data["test_points"]
    case_records = review_data["test_cases"]

    with chart_col3:
        with st.container(border=True):
            st.markdown("**项目测试资产审核进度**")

            project_names = {}
            for item in point_records + case_records:
                project_names[item["project_id"]] = item["project_name"]

            review_statuses = sorted({
                item["review_status"]
                for item in point_records + case_records
            })
            review_colors = {
                "approved": "#22C55E",
                "pending": "#F59E0B",
                "rejected": "#EF4444",
                "unknown": "#94A3B8",
            }
            review_display = {
                "approved": "已通过",
                "pending": "待审核",
                "rejected": "已驳回",
                "unknown": "未知状态",
            }

            y_labels = []
            for project_id, project_name in project_names.items():
                y_labels.extend([
                    f"{project_name} · 测试点",
                    f"{project_name} · 测试用例",
                ])

            if y_labels:
                fig = go.Figure()
                for status in review_statuses:
                    values = []
                    for project_id in project_names:
                        point_count = sum(
                            item["count"] for item in point_records
                            if item["project_id"] == project_id
                            and item["review_status"] == status
                        )
                        case_count = sum(
                            item["count"] for item in case_records
                            if item["project_id"] == project_id
                            and item["review_status"] == status
                        )
                        values.extend([point_count, case_count])

                    fig.add_trace(
                        go.Bar(
                            name=review_display.get(status, status),
                            y=y_labels,
                            x=values,
                            orientation="h",
                            marker_color=review_colors.get(status, "#64748B"),
                            hovertemplate="%{y}<br>%{fullData.name}：%{x:,}<extra></extra>",
                            width=0.25,
                            marker_line_width=0,
                        )
                    )

                fig.update_layout(
                    barmode="stack",
                    height=max(310, 120 + len(y_labels) * 65),
                    margin={"l": 10, "r": 10, "t": 35, "b": 20},
                    xaxis={"title": "数量", "gridcolor": "#E2E8F0", "rangemode": "tozero"},
                    yaxis={"title": ""},
                    legend={"orientation": "h", "y": 1.15},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    bargap=0.45,
                    barcornerradius=6,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("暂无项目审核数据")

    with chart_col4:
        with st.container(border=True):
            st.markdown("**测试工作流分布**")
            workflow_distribution = dashboard_data["workflow_distribution"]
            if workflow_distribution:
                workflow_names = [item["workflow_type"] for item in workflow_distribution]
                workflow_values = [item["count"] for item in workflow_distribution]
                fig = go.Figure(
                    go.Bar(
                        x=workflow_names,
                        y=workflow_values,
                        marker_color=["#3B82F6", "#06B6D4", "#8B5CF6"],
                        text=workflow_values,
                        textposition="outside",
                        hovertemplate="%{x}<br>数量：%{y:,}<extra></extra>",
                        width=0.25,
                        marker_line_width=0,
                    )
                )
                fig.update_layout(
                    height=310,
                    margin={"l": 15, "r": 15, "t": 25, "b": 25},
                    yaxis={"title": "记录 / 批次数量", "rangemode": "tozero", "gridcolor": "#E2E8F0"},
                    xaxis={"title": ""},
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    bargap=0.55,
                    barcornerradius=6,
                )
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            else:
                st.info("暂无工作流数据")

except Exception as exc:
    st.error(f"首页统计或图表数据读取失败：{exc}")


st.divider()


# ============================================================
# 四、核心业务工作流
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
# 五、业务功能入口
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
        "path": "pages/08_测试点中心.py",
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
# 六、页脚
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
