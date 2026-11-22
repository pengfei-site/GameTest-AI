import base64
import html
import json
from io import BytesIO
from pathlib import Path
import pandas as pd
import streamlit as st

from core.document_storage import read_original_document

from components.header import render_header
from database.repositories.project_repository import list_projects
from database.repositories.document_repository import list_documents
from database.repositories.requirement_repository import (
    list_requirement_analyses,
    create_requirement_analysis,
)
from core.requirement_analyzer import analyze_requirement
from core.time_utils import format_local_datetime


# 优先读取列表页通过 session_state 传递的定位信息；同时兼容直接使用 URL 参数打开。
project_id = st.session_state.get("requirement_detail_project_id") or st.query_params.get("project_id", "")
document_key = st.session_state.get("requirement_detail_document_key") or st.query_params.get("document_key", "")


def render_back_action():
    if st.button("原始文档", width="stretch"):
        st.session_state["show_original_document_dialog"] = True


render_header(
    title="需求详情",
    description="查看需求文档信息与当前版本的结构化分析。",
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
default_version = active_versions[0] if active_versions else versions[0]
version_map = {f"V{item.get('version', 1)}": item for item in versions}
default_version_label = next(
    label for label, item in version_map.items()
    if str(item.get("id")) == str(default_version.get("id"))
)
project_name = str(project.get("name") or "未命名项目")

st.html(f"""
<style>
.gt-detail-hero {{ background:#FFFFFF; border:1px solid #E7EAF1; border-radius:12px; padding:20px 22px; margin:8px 0 20px; box-shadow:0 2px 8px rgba(31,41,55,.04); }}
.gt-detail-title {{ color:#302D50; font-size:20px; line-height:1.45; font-weight:750; }}
.gt-detail-current-version {{ flex-shrink:0; color:#5D50A8; background:#F1EFFF; border:1px solid #E6E1FF; border-radius:999px; padding:6px 12px; font-size:12px; font-weight:700; white-space:nowrap; }}
.gt-detail-sub {{ color:#8490A3; font-size:12px; line-height:1.7; margin-top:10px; }}
.gt-detail-version {{ border:1px solid #E7EAF1; border-radius:10px; padding:12px 14px; margin:7px 0; background:#fff; }}
.gt-analysis-module {{ display:flex; align-items:center; gap:10px; font-size:15px; font-weight:750; color:#37316F; background:linear-gradient(110deg,#F2F0FF,#FAF9FF); border:1px solid #E7E2FF; border-left:4px solid #7968D8; border-radius:10px; padding:13px 16px; margin:2px 0 16px; }}
.gt-analysis-banner {{ background:linear-gradient(120deg,#F4F1FF 0%,#FAF9FF 100%); border:1px solid #E9E4FF; border-radius:14px; padding:20px 22px; margin:12px 0 16px; }}
.gt-analysis-banner-title {{ color:#433B83; font-size:16px; font-weight:750; margin-bottom:7px; }}
.gt-analysis-banner-desc {{ color:#77728F; font-size:13px; line-height:1.8; }}
.gt-analysis-summary {{ background:#F8FAFF; border:1px solid #E5EAF5; border-radius:10px; padding:16px 18px; line-height:1.9; color:#30384B; font-size:14px; }}
.gt-analysis-item {{ background:#fff; border:1px solid #E8ECF3; border-radius:10px; padding:14px 16px; margin:9px 0; box-shadow:0 1px 3px rgba(31,41,55,.025); }}
.gt-analysis-item-head {{ display:flex; align-items:center; gap:9px; flex-wrap:wrap; color:#30364A; font-size:13px; }}
.gt-rule-id {{ color:#5D50A8; background:#F1EFFF; border:1px solid #E6E1FF; border-radius:6px; padding:4px 8px; font-size:11px; font-weight:750; letter-spacing:.2px; }}
.gt-analysis-tag {{ color:#24734B; background:#EAF7EF; border:1px solid #D8F0E1; border-radius:20px; padding:3px 9px; font-size:11px; font-weight:650; white-space:nowrap; }}
.gt-analysis-tag-warning {{ color:#9A5A0B; background:#FFF4E2; border-color:#F7E4C2; }}
.gt-analysis-item-body {{ color:#394256; line-height:1.85; margin-top:10px; white-space:pre-wrap; font-size:13px; overflow-wrap:anywhere; }}
.gt-analysis-source {{ color:#7B8496; font-size:12px; line-height:1.75; margin-top:10px; background:#F8F9FC; border-radius:7px; padding:8px 10px; overflow-wrap:anywhere; }}
.gt-analysis-question {{ display:flex; align-items:flex-start; gap:10px; background:#FFFAF1; border:1px solid #F3E4C8; border-radius:10px; padding:13px 15px; margin:9px 0; line-height:1.8; color:#65491F; font-size:13px; }}
.gt-analysis-group-title {{ display:flex; align-items:center; gap:8px; color:#343653; font-size:13px; font-weight:750; margin:20px 0 9px; padding-bottom:8px; border-bottom:1px solid #EEF0F5; }}
.gt-analysis-group-title:before {{ content:""; width:4px; height:15px; border-radius:4px; background:#8175D5; display:inline-block; }}
.gt-analysis-metrics {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; margin:0 0 14px; }}
.gt-analysis-metric {{ background:#FAFAFE; border:1px solid #ECEBF5; border-radius:9px; padding:10px 12px; }}
.gt-analysis-metric strong {{ display:block; color:#39356B; font-size:19px; line-height:1.3; }}
.gt-analysis-metric span {{ color:#85899A; font-size:11px; }}
/* 需求详情顶部信息卡片：固定白色背景与卡片边界 */
.st-key-requirement-detail-card {{
  background: #FFFFFF !important;
  border: 1px solid #E7EAF1 !important;
  border-radius: 12px !important;
  padding: 20px 22px !important;
  box-shadow: 0 2px 8px rgba(31,41,55,.04) !important;
}}
.st-key-requirement-detail-card [data-testid="stVerticalBlock"] {{
  background: transparent !important;
}}
/* 分类导航改用 Streamlit segmented_control，不再渲染 Radio 圆点 */
div[data-testid="stSegmentedControl"] [role="group"] {{
  display:flex !important;
  flex-wrap:nowrap !important;
  width:100% !important;
  gap:4px !important;
}}
div[data-testid="stSegmentedControl"] button {{
  flex:1 1 auto !important;
  min-width:0 !important;
  white-space:nowrap !important;
  padding-left:8px !important;
  padding-right:8px !important;
}}
@media(max-width:700px) {{ .gt-analysis-metrics {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} }}
</style>
""")

with st.container(border=True, key="requirement-detail-card"):
    title_col, version_col = st.columns([6, 0.85], vertical_alignment="center")
    with title_col:
        st.markdown(
            f'<div class="gt-detail-title">▤ {html.escape(str(default_version.get("document_name") or "未命名文档"))}</div>',
            unsafe_allow_html=True,
        )
    with version_col:
        selected_version_label = st.selectbox(
            "当前版本",
            options=list(version_map.keys()),
            index=list(version_map.keys()).index(default_version_label),
            key=f"requirement_detail_version_{project_id}_{document_key}",
            label_visibility="collapsed",
        )
    current = version_map[selected_version_label]
    name = str(current.get("document_name") or "未命名文档")
    st.caption(
        f"所属项目：{project_name}　·　创建时间：{current.get('created_at') or '暂无'}　·　历史版本：{len(versions)} 个"
    )

st.caption(f"文档标识：{document_key}")




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


def _analysis_text(item, *keys) -> str:
    if not isinstance(item, dict):
        return str(item or "")
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def _render_analysis_card(title: str, body: str, status: str = "", source: str = "", prefix: str = "") -> None:
    status_html = (
        f'<span class="gt-analysis-tag">{html.escape(status)}</span>'
        if status else ""
    )
    st.markdown(
        f"""
        <div class="gt-analysis-item">
          <div class="gt-analysis-item-head">
            <span class="gt-rule-id">{html.escape(prefix or title)}</span>
            <strong>{html.escape(title if prefix else "")}</strong>
            {status_html}
          </div>
          <div class="gt-analysis-item-body">{html.escape(body or "暂无详细描述")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if source:
        with st.expander("查看需求依据", expanded=False):
            st.caption(source)




def render_unanalyzed_requirement(document: dict) -> None:
    """当前版本没有已保存分析时，提供原结构化需求分析页的分析、展示和保存流程。"""
    document_id = str(document.get("id") or "").strip()
    content = str(document.get("parsed_content") or "")
    if not document_id:
        st.warning("当前文档版本缺少关联 ID，无法执行结构化需求分析。")
        return
    if not content.strip():
        st.warning("当前文档版本没有可用于分析的解析文本。")
        return

    state_key = f"detail_structured_analysis_{document_id}"
    saved_key = f"detail_saved_analysis_{document_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = None
    if saved_key not in st.session_state:
        st.session_state[saved_key] = None

    st.markdown("### 结构化需求")
    st.caption("当前版本暂无已保存的需求分析结果。可以直接在此页面执行分析、查看结果并保存。")

    st.html("""
    <div class="gt-analysis-banner">
      <div class="gt-analysis-banner-title">AI 需求分析</div>
      <div class="gt-analysis-banner-desc">
        AI 将从当前文档版本中提取业务规则、前置条件、业务状态、
        数值约束、异常场景以及待策划确认的问题。
        分析结果经过 Pydantic 数据结构校验后展示。
      </div>
    </div>
    """)

    with st.expander("查看当前版本的文档解析内容", expanded=False):
        st.text_area(
            "文档解析文本",
            value=content,
            height=280,
            disabled=True,
            label_visibility="collapsed",
            key=f"detail_analysis_source_{document_id}",
        )

    if st.button(
        "开始结构化需求分析",
        type="primary",
        width="stretch",
        key=f"detail_run_analysis_{document_id}",
    ):
        st.session_state[state_key] = None
        st.session_state[saved_key] = None
        try:
            with st.spinner("AI 正在分析当前版本的策划需求，请稍候..."):
                result = analyze_requirement(content)
                st.session_state[state_key] = result.model_dump(mode="json")
            st.success("结构化需求分析完成。")
        except Exception as exc:
            st.error("需求分析失败，请检查 AI 服务或返回数据。")
            st.exception(exc)

    result = st.session_state.get(state_key)
    if not isinstance(result, dict):
        st.info("点击上方按钮，开始分析当前文档版本。")
        return

    st.divider()
    st.markdown("### 分析结果")
    st.caption(f"分析文档：{document.get('document_name') or document.get('file_name') or '未命名文档'}")

    with st.container(border=True):
        st.markdown("**一、需求摘要**")
        st.markdown(f"**功能模块：** {result.get('module') or '未命名模块'}")
        st.write(result.get("summary") or "暂无需求摘要")

    with st.container(border=True):
        st.markdown("**二、核心业务规则**")
        rules = result.get("business_rules") or []
        if rules:
            rule_rows = [{
                "规则编号": item.get("rule_id", ""),
                "规则描述": item.get("rule_text", ""),
                "需求依据": item.get("source_text", ""),
                "确认状态": "已明确" if item.get("status") == "confirmed" else "待确认",
            } for item in rules if isinstance(item, dict)]
            st.dataframe(pd.DataFrame(rule_rows), width="stretch", hide_index=True)
        else:
            st.info("暂未提取到业务规则。")

    simple_groups = [
        ("三、前置条件", "preconditions", "暂未提取到前置条件。"),
        ("四、业务状态", "states", "暂未提取到业务状态。"),
    ]
    for heading, key, empty_text in simple_groups:
        with st.container(border=True):
            st.markdown(f"**{heading}**")
            values = result.get(key) or []
            if values:
                for value in values:
                    st.markdown(f"- {value}")
            else:
                st.info(empty_text)

    with st.container(border=True):
        st.markdown("**五、数值约束**")
        constraints = result.get("numeric_constraints") or []
        if constraints:
            rows = [{
                "数值名称": str(item.get("name") or ""),
                "数值": "" if item.get("value") is None else str(item.get("value")),
                "单位": str(item.get("unit") or ""),
                "说明": str(item.get("description") or ""),
            } for item in constraints if isinstance(item, dict)]
            st.dataframe(pd.DataFrame(rows, columns=["数值名称", "数值", "单位", "说明"]), width="stretch", hide_index=True)
        else:
            st.info("暂未提取到数值约束。")

    for heading, key, empty_text in [
        ("六、异常场景", "exception_cases", "暂未提取到异常场景。"),
        ("七、待策划确认的问题", "open_questions", "当前未发现需要确认的问题。"),
    ]:
        with st.container(border=True):
            st.markdown(f"**{heading}**")
            values = result.get(key) or []
            if values:
                for index, value in enumerate(values, 1):
                    if key == "open_questions":
                        st.warning(f"{index}. {value}")
                    else:
                        st.markdown(f"- {value}")
            elif key == "open_questions":
                st.success(empty_text)
            else:
                st.info(empty_text)

    st.markdown("### 结构化数据")
    with st.expander("查看完整 JSON"):
        st.json(result)
    st.download_button(
        "下载需求分析 JSON",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name=f"requirement_analysis_V{document.get('version', 1)}.json",
        mime="application/json",
        key=f"detail_download_analysis_{document_id}",
    )

    st.markdown("### 保存分析结果")
    saved_record = st.session_state.get(saved_key)
    if saved_record:
        st.success("当前分析结果已经保存到数据库。")
        st.caption(
            f"分析记录 ID：{saved_record.get('id')} · 创建时间："
            f"{format_local_datetime(saved_record.get('created_at'))}"
        )
    elif st.button(
        "保存分析结果",
        type="primary",
        width="stretch",
        key=f"detail_save_analysis_{document_id}",
    ):
        try:
            with st.spinner("正在保存分析结果..."):
                saved_record = create_requirement_analysis(
                    project_id=str(project_id),
                    document_id=document_id,
                    module=result.get("module") or "未命名模块",
                    summary=result.get("summary") or "",
                    analysis_data=result,
                )
            st.session_state[saved_key] = saved_record
            st.success("分析结果已成功保存到数据库。")
            st.rerun()
        except Exception as exc:
            st.error("分析结果保存失败，请检查数据库记录和关联关系。")
            st.exception(exc)


def render_requirement_analysis(document: dict, section_title: str = "需求结构化分析") -> None:
    """以可筛选的工作台形式展示当前文档版本已保存的分析结果。"""
    document_id = str(document.get("id") or "").strip()
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
        render_unanalyzed_requirement(document)
        return

    category_labels = {
        "summary": "需求概述",
        "business_rules": "业务规则",
        "preconditions": "前置条件",
        "states": "涉及状态",
        "numeric_constraints": "数值约束",
        "exception_cases": "异常情况",
        "open_questions": "待确认问题",
    }
    for record_index, analysis in enumerate(analyses, start=1):
        data = analysis.get("analysis_data") or {}
        if not isinstance(data, dict):
            st.warning("该条分析记录的数据格式异常，暂时无法展示。")
            continue

        module = str(analysis.get("module") or data.get("module") or "未命名模块")
        summary = str(analysis.get("summary") or data.get("summary") or "")
        groups = {
            "summary": summary,
            "business_rules": data.get("business_rules") or [],
            "preconditions": data.get("preconditions") or [],
            "states": data.get("states") or [],
            "numeric_constraints": data.get("numeric_constraints") or [],
            "exception_cases": data.get("exception_cases") or [],
            "open_questions": data.get("open_questions") or [],
        }
        counts = {
            key: (1 if value else 0) if key == "summary" else len(value) if isinstance(value, list) else 0
            for key, value in groups.items()
        }

        st.markdown(
            f'<div class="gt-analysis-module">{html.escape(module)}'
            f'<span style="margin-left:auto;font-size:11px;color:#85899A;font-weight:500;">分析记录 {record_index}</span></div>',
            unsafe_allow_html=True,
        )
        metric_cols = st.columns(4)
        metric_items = [
            ("open_questions", "待确认问题"),
            ("business_rules", "业务规则"),
            ("preconditions", "前置条件"),
            ("numeric_constraints", "数值约束"),
        ]
        for col, (key, label) in zip(metric_cols, metric_items):
            with col:
                st.metric(label, counts[key])

        available = [key for key in category_labels if counts[key] > 0]
        if not available:
            st.info("该分析记录暂无可展示内容。")
            continue

        nav_labels = [category_labels[key] for key in available]
        selected_label = st.segmented_control(
            "分析内容导航",
            options=nav_labels,
            selection_mode="single",
            default=nav_labels[0],
            key=f"analysis_nav_{document_id}_{record_index}_{section_title}",
            label_visibility="collapsed",
            width="stretch",
        )
        selected_key = available[nav_labels.index(selected_label)]
        st.markdown(
            f'<div class="gt-analysis-group-title">{category_labels[selected_key]}</div>',
            unsafe_allow_html=True,
        )

        if selected_key == "summary":
            st.markdown(
                f'<div class="gt-analysis-summary">{html.escape(summary)}</div>',
                unsafe_allow_html=True,
            )

        elif selected_key == "business_rules":
            rules = groups["business_rules"]
            search_col, status_col = st.columns([2, 1])
            with search_col:
                keyword = st.text_input(
                    "搜索业务规则",
                    placeholder="输入规则编号、内容或需求依据",
                    key=f"analysis_rule_search_{document_id}_{record_index}_{section_title}",
                ).strip().lower()
            statuses = sorted({
                str(rule.get("status") or "").strip()
                for rule in rules if isinstance(rule, dict) and rule.get("status")
            })
            with status_col:
                status_filter = st.selectbox(
                    "状态筛选",
                    ["全部状态", *statuses],
                    key=f"analysis_rule_status_{document_id}_{record_index}_{section_title}",
                )
            filtered_rules = []
            for idx, rule in enumerate(rules, start=1):
                rule_id = _analysis_text(rule, "rule_id") or f"BR-{idx:03d}"
                body = _analysis_text(rule, "rule_text", "description", "text") if isinstance(rule, dict) else str(rule)
                source = _analysis_text(rule, "source_text")
                rule_status = _analysis_text(rule, "status")
                haystack = f"{rule_id} {body} {source}".lower()
                if keyword and keyword not in haystack:
                    continue
                if status_filter != "全部状态" and rule_status != status_filter:
                    continue
                filtered_rules.append((rule_id, body, source, rule_status))
            st.caption(f"显示 {len(filtered_rules)} / {len(rules)} 条业务规则")
            if not filtered_rules:
                st.info("没有找到符合条件的业务规则。")
            for rule_id, body, source, rule_status in filtered_rules:
                _render_analysis_card(rule_id, body, rule_status, source, rule_id)

        elif selected_key == "numeric_constraints":
            rows = []
            for item in groups[selected_key]:
                if isinstance(item, dict):
                    rows.append({
                        "参数": _analysis_text(item, "name") or "未命名约束",
                        "数值": _display_value(item.get("value", "")),
                        "单位": _analysis_text(item, "unit"),
                        "说明": _analysis_text(item, "description"),
                    })
                else:
                    rows.append({"参数": _display_value(item), "数值": "", "单位": "", "说明": ""})
            st.dataframe(rows, hide_index=True, width="stretch")

        else:
            values = groups[selected_key]
            for idx, item in enumerate(values, start=1):
                if selected_key == "open_questions":
                    body = _analysis_text(item, "question", "text", "description") if isinstance(item, dict) else str(item)
                    source = _analysis_text(item, "source_text")
                    st.markdown(
                        f'<div class="gt-analysis-question"><span class="gt-analysis-tag gt-analysis-tag-warning">待确认</span><div>{html.escape(body)}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if source:
                        with st.expander("查看需求依据", expanded=False):
                            st.caption(source)
                    continue

                title = (
                    _analysis_text(item, "rule_id", "name", "title")
                    if isinstance(item, dict) else ""
                ) or f"{selected_key[:3].upper()}-{idx:03d}"
                body = _analysis_text(item, "rule_text", "description", "text", "question") if isinstance(item, dict) else str(item)
                status = _analysis_text(item, "status") if isinstance(item, dict) else ""
                source = _analysis_text(item, "source_text") if isinstance(item, dict) else ""
                _render_analysis_card(title, body, status, source, title)


render_requirement_analysis(current)



@st.dialog("原始需求文档", width="large")
def show_original_document_dialog():
    st.caption("这里展示当前版本上传时保存的原始文件；如需保留完整排版，可下载原文件查看。")
    render_original_preview(
        current,
        f"dialog_{current.get('id') or current.get('version') or 'latest'}",
    )


if st.session_state.pop("show_original_document_dialog", False):
    show_original_document_dialog()

