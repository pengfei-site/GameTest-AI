 
import streamlit as st
import html

from database.repositories.project_repository import list_projects, create_project
from components.header import render_header


# ============================================================
# 一、页面初始化
# ============================================================


@st.dialog("创建项目")
def create_project_dialog():
    st.caption("填写项目基本信息，创建后即可进入需求分析和测试流程。")

    with st.form("project_list_create_form", clear_on_submit=True):
        new_name = st.text_input(
            "项目名称",
            placeholder="例如：三国策略手游",
            help="项目名称为必填项。",
        )
        new_description = st.text_area(
            "项目描述",
            placeholder="介绍游戏类型、项目背景或测试范围……",
            height=140,
            help="可以填写游戏玩法、核心系统、测试重点等信息。",
        )

        st.caption(
            "提示：项目创建成功后，可以继续录入需求文档、生成测试点和测试用例。"
        )

        submitted = st.form_submit_button(
            "+ 创建项目",
            type="primary",
            width="stretch",
        )

    if submitted:
        if not new_name.strip():
            st.error("项目名称不能为空。")
        else:
            try:
                project = create_project(
                    name=new_name.strip(),
                    description=new_description,
                )
                st.success(f'项目「{project["name"]}」创建成功！')
                st.rerun()
            except Exception as exc:
                st.error(f"创建项目失败：{exc}")

def render_create_project_action():
    # 在标题栏操作区域内增加弹性留白，使按钮靠右并保持适中宽度。
    _, button_col = st.columns(
        [3, 1],
        vertical_alignment="center",
        gap="small",
    )

    with button_col:
        if st.button(
            "+ 创建项目",
            type="primary",
            width="stretch",
            key="open_create_project_dialog",
        ):
            create_project_dialog()


def render_project_actions():

    search_col, filter_col = st.columns(
        [5, 0.65],
        vertical_alignment="center",
        gap="small",
    )

    with search_col:
        st.text_input(
            "搜索项目",
            placeholder="搜索项目名称、描述或 ID...",
            key="project_search_keyword",
            label_visibility="collapsed",
        )

    with filter_col:
        with st.popover(
            "",
            icon=":material/filter_list:",
            help="筛选项目",
            use_container_width=False,
        ):

            st.markdown("**项目状态**")

            st.radio(
                "项目状态筛选",
                options=["全部项目", "进行中", "已归档"],
                key="project_status_filter",
                label_visibility="collapsed",
            )

render_header(
    title="项目列表",
    description="查看和筛选工作空间中的游戏测试项目。",
    breadcrumb=["项目中心", "项目列表"],
    actions=render_create_project_action,
)

render_project_actions()


# ============================================================
# 二、页面样式
# ============================================================

st.html("""
<style>
.project-overview {
    margin-bottom: 8px;
}

.project-card-title {
    font-size: 19px;
    font-weight: 700;
    color: #172033;
    margin-bottom: 10px;
    line-height: 1.5;
}

.project-card-description {
    font-size: 14px;
    color: #64748B;
    line-height: 1.7;
    margin-bottom: 14px;
}

.project-card-meta {
    display: inline-block;
    font-size: 12px;
    color: #64748B;
    background: #F3F5F9;
    padding: 5px 10px;
    border-radius: 6px;
    margin-bottom: 8px;
}

.project-status-active {
    display: inline-block;
    color: #15803D;
    background: #DCFCE7;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 650;
    white-space: nowrap;
}

.project-status-archived {
    display: inline-block;
    color: #64748B;
    background: #E2E8F0;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 650;
    white-space: nowrap;
}

.project-section-caption {
    color: #858397;
    font-size: 13px;
    margin-top: -8px;
    margin-bottom: 16px;
}
</style>
""")


# ============================================================
# 三、加载项目数据
# ============================================================

try:
    projects = list_projects(include_archived=True)

except Exception as exc:
    st.error(f"项目列表读取失败：{exc}")
    st.stop()


active_projects = [
    p for p in projects
    if p["status"] == "active"
]

archived_projects = [
    p for p in projects
    if p["status"] == "archived"
]


# ============================================================
# 四、项目概览
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="📁 项目总数", value=len(projects))

with col2:
    st.metric(label="🚀 进行中项目", value=len(active_projects))

with col3:
    st.metric(label="📦 已归档项目", value=len(archived_projects))


st.divider()


# ============================================================
# 五、项目筛选
# ============================================================

status_filter = st.session_state.get(
    "project_status_filter",
    "全部项目",
)

search_keyword = st.session_state.get(
    "project_search_keyword",
    "",
)

if status_filter == "进行中":
    displayed_projects = active_projects
elif status_filter == "已归档":
    displayed_projects = archived_projects
else:
    displayed_projects = projects

if search_keyword.strip():
    keyword = search_keyword.strip().lower()
    displayed_projects = [
        project
        for project in displayed_projects
        if keyword in str(project.get("name", "")).lower()
        or keyword in str(project.get("description", "")).lower()
        or keyword in str(project.get("id", "")).lower()
    ]

st.caption(f"当前显示 {len(displayed_projects)} 个项目")


# ============================================================
# 六、项目列表
# ============================================================

if not displayed_projects:

    st.info("当前筛选条件下没有项目。", icon="📭")

    if not projects:
        st.caption("可以通过下方的创建项目入口，建立第一个游戏测试项目。")

else:

    for start in range(0, len(displayed_projects), 2):

        card_cols = st.columns(2, gap="medium")
        row_projects = displayed_projects[start:start + 2]

        for card_col, project in zip(card_cols, row_projects):

            is_active = project["status"] == "active"

            project_name = html.escape(
                str(project.get("name") or "未命名项目")
            )
            project_description = html.escape(
                str(project.get("description") or "暂无项目描述")
            )
            project_id = html.escape(str(project.get("id", "未知")))
            created_at = html.escape(str(project.get("created_at", "未知")))
            updated_at = html.escape(str(project.get("updated_at", "未知")))

            if is_active:
                status_html = """
                    <span class="gt-status gt-status-success">● 进行中</span>
                """
            else:
                status_html = """
                    <span class="gt-status gt-status-neutral">● 已归档</span>
                """

            with card_col:
                card_key = f"project_card_{project['id']}"

                with st.container(key=card_key):
                    st.html(
                        f"""
                        <div style="
                            display: flex;
                            align-items: center;
                            justify-content: space-between;
                            gap: 12px;
                            margin-bottom: 10px;
                        ">
                            <div class="gt-card-title" style="margin-bottom: 0;">
                                🎮 {project_name}
                            </div>
                            {status_html}
                        </div>
                        <div class="gt-card-description">
                            {project_description}
                        </div>
                        """
                    )

                    date_col, action_col = st.columns(
                        [4, 1.5],
                        vertical_alignment="bottom",
                        gap="small",
                    )

                    with date_col:
                        st.html(
                            f"""
                            <div class="gt-info-card-footer">
                                <div>项目 ID：{project_id}</div>
                                <div>创建时间：{created_at}</div>
                                <div>最近更新：{updated_at}</div>
                            </div>
                            """
                        )

                    with action_col:
                        if st.button(
                            "了解详情 >",
                            key=f"open_project_{project['id']}",
                            type="secondary",
                            width="stretch",
                        ):
                            st.session_state["project_detail_target_id"] = str(
                                project["id"]
                            )
                            st.switch_page("pages/13_项目详情.py")


