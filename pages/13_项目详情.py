import streamlit as st

from components.header import render_header
from database.connection import get_connection
from database.repositories.project_repository import get_project


def load_project_statistics(project_id: str) -> dict:
    """按项目真实外键关系统计需求分析、测试点和审核通过的测试用例。"""
    with get_connection() as conn:
        requirement_count = conn.execute(
            "SELECT COUNT(*) FROM requirement_analyses WHERE project_id = ?",
            (project_id,),
        ).fetchone()[0]

        test_point_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM test_points tp
            JOIN generation_batches gb ON gb.id = tp.batch_id
            WHERE gb.project_id = ? AND tp.is_deleted = 0
            """,
            (project_id,),
        ).fetchone()[0]

        approved_case_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM test_case_candidates tc
            JOIN test_case_generation_batches cb ON cb.id = tc.batch_id
            WHERE cb.project_id = ? AND tc.manual_review_status = 'approved'
            """,
            (project_id,),
        ).fetchone()[0]

        case_analysis_count = conn.execute(
            """
            SELECT COUNT(DISTINCT cb.requirement_analysis_id)
            FROM test_case_generation_batches cb
            JOIN test_case_candidates tc ON tc.batch_id = cb.id
            WHERE cb.project_id = ?
            """,
            (project_id,),
        ).fetchone()[0]

        linked_test_point_count = conn.execute(
            """
            SELECT COUNT(DISTINCT bp.test_point_id)
            FROM test_case_generation_batch_points bp
            JOIN test_case_generation_batches cb ON cb.id = bp.batch_id
            JOIN test_points tp ON tp.id = bp.test_point_id
            WHERE cb.project_id = ?
              AND tp.is_deleted = 0
            """,
            (project_id,),
        ).fetchone()[0]

    return {
        "requirements": requirement_count,
        "test_points": test_point_count,
        "approved_cases": approved_case_count,
        "case_analyses": case_analysis_count,
        "linked_test_points": linked_test_point_count,
    }


project_id = st.session_state.get("project_detail_target_id")
if not project_id:
    st.warning("没有指定项目，请从项目列表进入项目详情。")
    if st.button("返回项目列表"):
        st.switch_page("pages/01_项目列表.py")
    st.stop()

project = get_project(str(project_id))
if project is None:
    st.error("项目不存在或已被删除。")
    if st.button("返回项目列表"):
        st.switch_page("pages/01_项目列表.py")
    st.stop()

is_active = project.get("status") == "active"
status_label = "进行中" if is_active else "已归档"

render_header(
    title="项目详情",
    description="查看项目基本信息、测试资产规模及其关联情况。",
    breadcrumb=["项目中心", "项目列表", "项目详情"],
)

top_left, top_right = st.columns([5, 1])
with top_left:
    st.caption(f"项目 ID：{project.get('id', '-')}")
with top_right:
    if st.button("返回项目列表", width="stretch"):
        st.switch_page("pages/01_项目列表.py")

st.divider()
st.subheader("项目基本信息")
with st.container(border=True):
    st.markdown(f"### {project.get('name') or '未命名项目'}")
    st.write(f"**项目状态：** {status_label}")
    st.write(f"**项目描述：** {project.get('description') or '暂无项目描述'}")
    info_left, info_right = st.columns(2)
    info_left.caption(f"创建时间：{project.get('created_at') or '-'}")
    info_right.caption(f"最近更新：{project.get('updated_at') or '-'}")
    if project.get("archived_at"):
        st.caption(f"归档时间：{project.get('archived_at')}")

try:
    stats = load_project_statistics(str(project_id))
except Exception as exc:
    st.error(f"项目统计读取失败：{exc}")
    st.stop()

st.divider()
st.subheader("项目测试资产")
metric_cols = st.columns(3)
metric_cols[0].metric("需求分析记录数", f"{stats['requirements']:,}")
metric_cols[1].metric("有效测试点数", f"{stats['test_points']:,}")
metric_cols[2].metric("审核通过的测试用例数", f"{stats['approved_cases']:,}")
st.caption(
    "统计口径：需求按分析记录计数；测试点排除逻辑删除记录；"
    "测试用例按当前审核通过的候选记录计数，不重复计算版本历史。"
)

st.divider()
st.subheader("需求与测试资产关联")
relation_cols = st.columns(2)
with relation_cols[0]:
    st.markdown("**需求分析 → 测试用例生成**")
    if stats["requirements"] == 0:
        st.info("当前项目暂无需求分析记录。")
    elif stats["case_analyses"] == 0:
        st.warning("已有需求分析记录，但尚无关联的测试用例生成记录。")
    else:
        st.success(
            f"{stats['case_analyses']} 条需求分析记录已关联测试用例生成批次。"
        )
with relation_cols[1]:
    st.markdown("**测试点 → 测试用例**")
    if stats["test_points"] == 0:
        st.info("当前项目暂无有效测试点。")
    elif stats["linked_test_points"] == 0:
        st.warning("已有有效测试点，但尚未关联测试用例生成批次。")
    else:
        st.success(
            f"{stats['linked_test_points']} 个有效测试点已关联测试用例生成批次。"
        )

st.divider()
st.subheader("项目功能入口")
if not is_active:
    st.info("该项目已归档，当前详情仅供查看。恢复项目后可继续进行管理操作。")
else:
    st.caption("选择下方入口继续管理当前项目。")
    action_cols = st.columns(3)
    with action_cols[0]:
        if st.button("需求文档", icon=":material/description:", width="stretch"):
            st.session_state["document_project_id"] = str(project_id)
            st.switch_page("pages/05_需求文档.py")
    with action_cols[1]:
        if st.button("结构化需求分析", icon=":material/psychology:", width="stretch"):
            st.session_state["analysis_project_selector"] = str(project_id)
            st.switch_page("pages/06_结构化需求分析.py")
    with action_cols[2]:
        if st.button("测试点管理", icon=":material/target:", width="stretch"):
            st.session_state["test_point_list_project"] = str(project_id)
            st.switch_page("pages/08_测试点列表.py")

    case_col, edit_col = st.columns(2)
    with case_col:
        if st.button("测试用例管理", icon=":material/checklist:", width="stretch"):
            st.switch_page("pages/12_测试用例管理.py")
    with edit_col:
        if st.button("编辑项目信息", icon=":material/edit:", width="stretch"):
            st.session_state["edit_project_target_id"] = str(project_id)
            st.switch_page("pages/03_项目编辑.py")
