import html
import streamlit as st

from components.header import render_header
from database.connection import get_connection
from database.repositories.project_repository import get_project


st.html("""
<style>
.detail-section-title{color:#1E293B;font-size:18px;font-weight:750;margin:8px 0 5px}
.detail-section-desc{color:#64748B;font-size:12px;line-height:1.7;margin-bottom:16px}
.detail-card{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px 20px;box-shadow:0 2px 8px rgba(30,41,59,.035);height:100%}
.detail-card-label{color:#64748B;font-size:13px;font-weight:650;margin-bottom:10px}
.detail-card-value{color:#1E293B;font-size:27px;font-weight:800;line-height:1.25}
.detail-card-note{color:#94A3B8;font-size:11px;line-height:1.6;margin-top:8px}
.project-name{color:#1E293B;font-size:22px;font-weight:800;margin-bottom:10px;overflow-wrap:anywhere}
.project-description{color:#64748B;font-size:13px;line-height:1.8;margin-top:12px}
.project-meta{color:#64748B;font-size:12px;line-height:1.9}
.status-pill{display:inline-block;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:700}
.status-active{color:#15803D;background:#DCFCE7}
.status-archived{color:#475569;background:#F1F5F9}
.relation-card{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:18px;min-height:145px;box-shadow:0 2px 8px rgba(30,41,59,.035)}
.relation-title{color:#1E293B;font-size:14px;font-weight:750;margin-bottom:12px}
.relation-value{color:#1E293B;font-size:24px;font-weight:800;margin-bottom:5px}
.relation-note{color:#64748B;font-size:12px;line-height:1.7}
</style>
""")


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
            WHERE cb.project_id = ? AND tp.is_deleted = 0
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
project_name = html.escape(str(project.get("name") or "未命名项目"))
project_description = html.escape(str(project.get("description") or "暂无项目描述"))

render_header(
    title="项目详情",
    description="查看项目基本信息、测试资产规模及其关联情况。",
    breadcrumb=["项目中心", "项目列表", "项目详情"],
)

_, top_right = st.columns([5, 1])
with top_right:
    if st.button("返回项目列表", width="stretch"):
        st.switch_page("pages/01_项目列表.py")

st.markdown(
    '<div class="detail-section-title">📁 项目基本信息</div>'
    '<div class="detail-section-desc">项目身份信息、基础描述与当前状态</div>',
    unsafe_allow_html=True,
)
status_class = "status-active" if is_active else "status-archived"
created_at = html.escape(str(project.get("created_at") or "-"))
updated_at = html.escape(str(project.get("updated_at") or "-"))
archived_at = project.get("archived_at")
archived_html = f'<span>归档时间：{html.escape(str(archived_at))}</span>' if archived_at else ""
st.html(f"""
<div class="detail-card">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
    <div class="project-name">{project_name}</div>
    <span class="status-pill {status_class}">{status_label}</span>
  </div>
  <div class="project-description">{project_description}</div>
  <div style="height:1px;background:#E2E8F0;margin:16px 0 12px"></div>
  <div class="project-meta" style="display:flex;gap:24px;flex-wrap:wrap">
    <span>项目 ID：{html.escape(str(project.get("id", "-")))}</span>
    <span>创建时间：{created_at}</span><span>最近更新：{updated_at}</span>{archived_html}
  </div>
</div>
""")

try:
    stats = load_project_statistics(str(project_id))
except Exception as exc:
    st.error(f"项目统计读取失败：{exc}")
    st.stop()

st.markdown(
    '<div class="detail-section-title">📊 项目测试资产</div>'
    '<div class="detail-section-desc">当前项目已沉淀的需求分析、测试点与审核通过的测试用例</div>',
    unsafe_allow_html=True,
)
metric_items = [
    ("需求分析记录数", stats["requirements"], "按需求分析记录统计"),
    ("有效测试点数", stats["test_points"], "已排除逻辑删除记录"),
    ("审核通过的测试用例数", stats["approved_cases"], "不重复计算版本历史"),
]
metric_cols = st.columns(3)
for col, (label, value, note) in zip(metric_cols, metric_items):
    with col:
        st.html(f"""
        <div class="detail-card">
          <div class="detail-card-label">{label}</div>
          <div class="detail-card-value">{value:,}</div>
          <div class="detail-card-note">{note}</div>
        </div>
        """)
st.caption(
    "统计口径：需求按分析记录计数；测试点排除逻辑删除记录；"
    "测试用例按当前审核通过的候选记录计数，不重复计算版本历史。"
)

st.markdown(
    '<div class="detail-section-title">🔗 需求与测试资产关联</div>'
    '<div class="detail-section-desc">依据现有生成批次与资产关联关系展示，不以数量推断关联</div>',
    unsafe_allow_html=True,
)
relation_cols = st.columns(2)
if stats["requirements"] == 0:
    req_value, req_note = "暂无数据", "当前项目暂无需求分析记录。"
elif stats["case_analyses"] == 0:
    req_value, req_note = "尚未关联", "已有需求分析记录，但尚无关联的测试用例生成记录。"
else:
    req_value, req_note = f'{stats["case_analyses"]:,} 条', "需求分析记录已关联测试用例生成批次。"
if stats["test_points"] == 0:
    point_value, point_note = "暂无数据", "当前项目暂无有效测试点。"
elif stats["linked_test_points"] == 0:
    point_value, point_note = "尚未关联", "已有有效测试点，但尚未关联测试用例生成批次。"
else:
    point_value, point_note = f'{stats["linked_test_points"]:,} 个', "有效测试点已关联测试用例生成批次。"
with relation_cols[0]:
    st.html(f"""
    <div class="relation-card">
      <div class="relation-title">需求分析 → 测试用例生成</div>
      <div class="relation-value">{req_value}</div>
      <div class="relation-note">{req_note}</div>
    </div>
    """)
with relation_cols[1]:
    st.html(f"""
    <div class="relation-card">
      <div class="relation-title">测试点 → 测试用例</div>
      <div class="relation-value">{point_value}</div>
      <div class="relation-note">{point_note}</div>
    </div>
    """)

st.markdown(
    '<div class="detail-section-title">🚀 项目功能入口</div>'
    '<div class="detail-section-desc">直接进入当前项目对应的业务管理页面</div>',
    unsafe_allow_html=True,
)
if not is_active:
    st.info("该项目已归档，当前详情仅供查看。恢复项目后可继续进行管理操作。")
else:
    action_items = [
        ("📄 需求文档", "查看和维护项目需求文档", "进入需求文档", "detail_documents"),
        ("🧠 结构化需求分析", "查看需求分析结果", "进入需求分析", "detail_analysis"),
        ("🎯 测试点管理", "生成、审核和管理测试点", "进入测试点管理", "detail_test_points"),
        ("📋 测试用例管理", "查看和管理测试用例", "进入测试用例管理", "detail_test_cases"),
        ("✏️ 编辑项目信息", "修改项目名称、描述等基础信息", "编辑项目", "detail_edit_project"),
    ]
    destinations = {
        "detail_documents": ("document_project_id", "pages/05_需求文档.py"),
        "detail_analysis": ("analysis_project_selector", "pages/06_结构化需求分析.py"),
        "detail_test_points": ("test_point_list_project", "pages/08_测试点列表.py"),
        "detail_test_cases": (None, "pages/12_测试用例管理.py"),
        "detail_edit_project": ("edit_project_target_id", "pages/03_项目编辑.py"),
    }
    for start in range(0, len(action_items), 3):
        cols = st.columns(3)
        for col, (title, description, button_label, key) in zip(cols, action_items[start:start + 3]):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.caption(description)
                    if st.button(button_label, key=key, width="stretch"):
                        state_key, page = destinations[key]
                        if state_key:
                            st.session_state[state_key] = str(project_id)
                        st.switch_page(page)
