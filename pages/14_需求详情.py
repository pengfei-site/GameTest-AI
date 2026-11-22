import base64
import html
from io import BytesIO
from pathlib import Path
import streamlit as st

from core.document_storage import read_original_document

from components.header import render_header
from database.repositories.project_repository import list_projects
from database.repositories.document_repository import list_documents
from database.repositories.requirement_repository import list_requirement_analyses


# 优先读取列表页通过 session_state 传递的定位信息；同时兼容直接使用 URL 参数打开。
project_id = st.session_state.get("requirement_detail_project_id") or st.query_params.get("project_id", "")
document_key = st.session_state.get("requirement_detail_document_key") or st.query_params.get("document_key", "")


def render_back_action():
    if st.button("← 返回需求列表", use_container_width=True):
        st.switch_page("pages/05_需求文档.py")


render_header(
    title="需求详情",
    description="查看需求文档信息、正文内容与历史版本。",
    breadcrumb=["需求中心", "需求文档", "需求详情"],
    actions=render_back_action,
)

if not project_id or not document_key:
    st.warning("缺少需求文档定位信息，请从需求文档列表重新进入。")
    if st.button("返回需求列表"):
        st.switch_page("pages/05_需求文档.py")
    st.stop()

try:
    projects = list_projects()
    project_map = {str(item["id"]): item for item in projects}
    project = project_map.get(str(project_id))
    if project is None:
        st.error("所属项目不存在或已不可用。")
        st.stop()
    versions = list_documents(project_id=str(project_id), document_key=str(document_key), include_deleted=True)
except Exception as exc:
    st.error(f"需求详情加载失败：{exc}")
    st.stop()

if not versions:
    st.warning("未找到对应的需求文档版本。")
    st.stop()

active_versions = [item for item in versions if not item.get("is_deleted")]
current = active_versions[0] if active_versions else versions[0]
name = str(current.get("document_name") or "未命名文档")
project_name = str(project.get("name") or "未命名项目")
status = "有效" if active_versions else "已删除"
status_color = "#15803D" if active_versions else "#B45309"
status_bg = "#DCFCE7" if active_versions else "#FEF3C7"

st.html(f"""
<style>
.gt-detail-hero {{ background:#fff; border:1px solid #E7EAF1; border-radius:14px; padding:20px 22px; margin:8px 0 18px; }}
.gt-detail-title {{ font-size:22px; font-weight:750; color:#24213F; overflow-wrap:anywhere; }}
.gt-detail-sub {{ color:#778196; font-size:13px; margin-top:7px; }}
.gt-detail-badge {{ display:inline-block; border-radius:20px; padding:4px 10px; color:{status_color}; background:{status_bg}; font-size:12px; font-weight:650; }}
.gt-detail-section {{ color:#292746; font-size:16px; font-weight:700; margin:22px 0 10px; }}
.gt-detail-version {{ border:1px solid #E7EAF1; border-radius:10px; padding:12px 14px; margin:7px 0; background:#fff; }}
.gt-analysis-module {{ font-size:15px; font-weight:700; color:#403B78; background:#F4F2FF; border-left:3px solid #8175D5; border-radius:7px; padding:10px 12px; margin:4px 0 14px; }}
.gt-analysis-summary {{ background:#F8F9FC; border:1px solid #E9ECF3; border-radius:9px; padding:13px 15px; line-height:1.75; color:#34384A; }}
.gt-analysis-item {{ background:#fff; border:1px solid #E8EAF1; border-radius:9px; padding:12px 14px; margin:8px 0; }}
.gt-analysis-item-head {{ display:flex; align-items:center; gap:9px; flex-wrap:wrap; color:#34324F; }}
.gt-rule-id {{ color:#6558B5; background:#F1EFFF; border-radius:5px; padding:3px 7px; font-size:12px; font-weight:700; }}
.gt-analysis-tag {{ color:#26734D; background:#EAF7EF; border-radius:20px; padding:3px 8px; font-size:11px; }}
.gt-analysis-tag-warning {{ color:#A65B0B; background:#FFF3DF; }}
.gt-analysis-item-body {{ color:#41465A; line-height:1.7; margin-top:8px; white-space:pre-wrap; }}
.gt-analysis-source {{ color:#8790A2; font-size:12px; line-height:1.6; margin-top:7px; border-top:1px dashed #E7EAF1; padding-top:7px; }}
.gt-analysis-question {{ display:flex; align-items:flex-start; gap:10px; background:#FFFAF1; border:1px solid #F5E5C8; border-radius:9px; padding:12px 14px; margin:8px 0; line-height:1.65; color:#65491F; }}
</style>
<div class="gt-detail-hero">
  <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
    <div class="gt-detail-title">▤ {html.escape(name)}</div>
    <span class="gt-detail-badge">{status}</span>
  </div>
  <div class="gt-detail-sub">所属项目：{html.escape(project_name)}　·　创建时间：{html.escape(str(current.get("created_at") or "暂无"))}　·　当前版本：V{current.get("version", 1)}　·　历史版本：{len(versions)} 个</div>
</div>
""")


def render_original_preview(document: dict, key_suffix: str) -> None:
    """优先预览原始文件；旧版本没有原文件时回退到解析文本。"""
    file_path = document.get("file_path")
    try:
        original_bytes = read_original_document(file_path)
    except Exception as exc:
        st.error(f"读取原始文档失败：{exc}")
        original_bytes = None

    if original_bytes:
        file_name = Path(file_path).name
        st.download_button(
            "下载原始文档",
            data=original_bytes,
            file_name=file_name,
            mime={
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "md": "text/markdown",
                "txt": "text/plain",
            }.get(Path(file_path).suffix.lower().lstrip("."), "application/octet-stream"),
            key=f"download_original_{key_suffix}",
        )

        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            encoded = base64.b64encode(original_bytes).decode("ascii")
            st.components.v1.html(
                f'<iframe src="data:application/pdf;base64,{encoded}" '
                'width="100%" height="850" style="border:1px solid #E5E7EB;border-radius:8px;"></iframe>',
                height=870,
                scrolling=True,
            )
        elif suffix == ".docx":
            try:
                import mammoth

                def image_to_data_uri(image):
                    with image.open() as image_file:
                        encoded = base64.b64encode(image_file.read()).decode("ascii")
                    return {"src": f"data:{image.content_type};base64,{encoded}"}

                result = mammoth.convert_to_html(
                    BytesIO(original_bytes),
                    convert_image=mammoth.images.img_element(image_to_data_uri),
                )
                preview_html = result.value
                st.components.v1.html(
                    f"""
                    <div style="font-family:Arial,'Microsoft YaHei',sans-serif;color:#242424;
                                line-height:1.75;padding:24px;background:#fff;">
                    <style>
                      h1,h2,h3,h4 {{ color:#222; margin:1.2em 0 .55em; }}
                      p {{ margin:.55em 0; }}
                      table {{ border-collapse:collapse;width:100%;margin:1em 0; }}
                      td,th {{ border:1px solid #D1D5DB;padding:7px 10px;vertical-align:top; }}
                      img {{ max-width:100%;height:auto; }}
                      blockquote {{ border-left:3px solid #CBD5E1;padding-left:14px;color:#64748B; }}
                    </style>
                    {preview_html}
                    </div>
                    """,
                    height=850,
                    scrolling=True,
                )
                if result.messages:
                    st.caption("部分 Word 特殊样式可能无法完全还原；可下载原始文件查看完整排版。")
            except ImportError:
                st.warning("Word 在线预览组件尚未安装，请下载原始 DOCX 查看完整排版。")
            except Exception as exc:
                st.warning(f"Word 在线预览失败：{exc}，可下载原始文件查看。")
        elif suffix == ".md":
            from core.document_parser import _decode_text
            st.markdown(_decode_text(original_bytes))
        elif suffix == ".txt":
            from core.document_parser import _decode_text
            st.code(_decode_text(original_bytes), language="text")
        return

    st.info("该历史版本尚未保存原始文件，以下显示当时提取的文本内容。")
    content = document.get("parsed_content") or ""
    if content:
        st.text_area(
            "解析文本内容",
            value=content,
            height=520,
            disabled=True,
            label_visibility="collapsed",
            key=f"parsed_fallback_{key_suffix}",
        )
    else:
        st.info("当前版本没有可展示的解析正文。")



def _display_value(value) -> str:
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def _render_analysis_items(values, label: str, item_prefix: str = "") -> None:
    if not isinstance(values, list) or not values:
        return
    st.markdown(f"**{label}**")
    for index, value in enumerate(values, start=1):
        if isinstance(value, dict):
            title = (
                value.get("rule_id")
                or value.get("name")
                or value.get("title")
                or f"{item_prefix}{index:03d}"
            )
            body = (
                value.get("rule_text")
                or value.get("description")
                or value.get("text")
                or value.get("question")
                or ""
            )
            status_value = value.get("status")
            status_html = (
                f'<span class="gt-analysis-tag">{html.escape(str(status_value))}</span>'
                if status_value else ""
            )
            st.markdown(
                f"""
                <div class="gt-analysis-item">
                  <div class="gt-analysis-item-head">
                    <strong>{html.escape(str(title))}</strong>{status_html}
                  </div>
                  {f'<div class="gt-analysis-item-body">{html.escape(str(body))}</div>' if body else ''}
                  {f'<div class="gt-analysis-source">需求依据：{html.escape(str(value.get("source_text")))}</div>' if value.get("source_text") else ''}
                  {f'<div class="gt-analysis-source">{html.escape(str(value.get("unit") or ""))}</div>' if value.get("unit") else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="gt-analysis-item">{html.escape(_display_value(value))}</div>',
                unsafe_allow_html=True,
            )


def render_requirement_analysis(document: dict, section_title: str = "需求结构化分析") -> None:
    """展示当前文档版本已保存的分析结果，不触发重新分析。"""
    document_id = str(document.get("id") or "").strip()
    st.markdown(
        f'<div class="gt-detail-section">{html.escape(section_title)}</div>',
        unsafe_allow_html=True,
    )
    if not document_id:
        st.info("当前文档版本缺少关联 ID，无法定位已保存的分析结果。")
        return

    try:
        analyses = list_requirement_analyses(
            project_id=str(project_id),
            document_id=document_id,
        )
    except Exception as exc:
        st.error(f"读取已保存的需求分析结果失败：{exc}")
        return

    if not analyses:
        st.info("当前文档版本暂无已保存的需求分析结果。")
        return

    for index, analysis in enumerate(analyses, start=1):
        analysis_data = analysis.get("analysis_data") or {}
        if not isinstance(analysis_data, dict):
            st.warning("该条分析记录的数据格式异常，暂时无法展示。")
            continue

        module = str(analysis.get("module") or analysis_data.get("module") or "未命名模块")
        summary = str(analysis.get("summary") or analysis_data.get("summary") or "")
        business_rules = analysis_data.get("business_rules") or []
        preconditions = analysis_data.get("preconditions") or []
        states = analysis_data.get("states") or []
        constraints = analysis_data.get("numeric_constraints") or []
        exceptions = analysis_data.get("exception_cases") or []
        questions = analysis_data.get("open_questions") or []

        with st.expander(f"{module} · 分析记录 {index}", expanded=(index == 1)):
            st.markdown(
                f'<div class="gt-analysis-module">{html.escape(module)}</div>',
                unsafe_allow_html=True,
            )
            if summary:
                st.markdown("**需求概述**")
                st.markdown(
                    f'<div class="gt-analysis-summary">{html.escape(summary)}</div>',
                    unsafe_allow_html=True,
                )

            if business_rules:
                st.markdown("**业务规则**")
                for rule_index, rule in enumerate(business_rules, start=1):
                    if isinstance(rule, dict):
                        rule_id = str(rule.get("rule_id") or f"BR-{rule_index:03d}")
                        rule_text = str(rule.get("rule_text") or "")
                        rule_status = str(rule.get("status") or "")
                        source_text = str(rule.get("source_text") or "")
                    else:
                        rule_id, rule_text, rule_status, source_text = f"BR-{rule_index:03d}", str(rule), "", ""
                    status_html = (
                        f'<span class="gt-analysis-tag">{html.escape(rule_status)}</span>'
                        if rule_status else ""
                    )
                    st.markdown(
                        f"""
                        <div class="gt-analysis-item">
                          <div class="gt-analysis-item-head">
                            <span class="gt-rule-id">{html.escape(rule_id)}</span>
                            {status_html}
                          </div>
                          <div class="gt-analysis-item-body">{html.escape(rule_text)}</div>
                          {f'<div class="gt-analysis-source">需求依据：{html.escape(source_text)}</div>' if source_text else ''}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            _render_analysis_items(preconditions, "前置条件", "PRE-")
            _render_analysis_items(states, "涉及状态", "STATE-")

            if constraints:
                st.markdown("**数值约束**")
                rows = []
                for item in constraints:
                    if isinstance(item, dict):
                        rows.append({
                            "参数": str(item.get("name") or "未命名约束"),
                            "数值": _display_value(item.get("value", "")),
                            "单位": str(item.get("unit") or ""),
                            "说明": str(item.get("description") or ""),
                        })
                    else:
                        rows.append({"参数": _display_value(item), "数值": "", "单位": "", "说明": ""})
                st.dataframe(rows, hide_index=True, use_container_width=True)

            _render_analysis_items(exceptions, "异常情况", "EX-")
            if questions:
                st.markdown("**待确认问题**")
                for question_index, question in enumerate(questions, start=1):
                    question_text = (
                        question.get("question") or question.get("text") or question.get("description") or str(question)
                        if isinstance(question, dict) else str(question)
                    )
                    st.markdown(
                        f"""
                        <div class="gt-analysis-question">
                          <span class="gt-analysis-tag gt-analysis-tag-warning">待确认</span>
                          <div>{html.escape(question_text)}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


render_requirement_analysis(current)


with st.expander("查看原始需求文档", expanded=False):
    st.caption("这里展示上传时保存的原始文件；如需保留完整排版，可下载原文件查看。")
    render_original_preview(current, f"current_{current.get('id') or current.get('version') or 'latest'}")

st.markdown('<div class="gt-detail-section">版本历史</div>', unsafe_allow_html=True)
for item in versions:
    deleted = bool(item.get("is_deleted"))
    version_status = "已删除" if deleted else "有效"
    st.html(f"""
    <div class="gt-detail-version">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
        <strong style="color:#302D50;">V{item.get("version", 1)}</strong>
        <span style="font-size:12px;color:{"#B45309" if deleted else "#15803D"};">{version_status}</span>
      </div>
      <div style="font-size:12px;color:#8490A3;margin-top:5px;">{html.escape(str(item.get("created_at") or "创建时间未知"))}　·　{str(item.get("file_type") or "未知").upper()}　·　{(item.get("char_count") or 0):,} 字符</div>
    </div>
    """)
    with st.expander(f"查看 V{item.get('version', 1)} 内容"):
        render_requirement_analysis(item, f"V{item.get('version', 1)} 需求结构化分析")
        render_original_preview(item, f"history_{item.get('id') or item.get('version') or 'unknown'}")
