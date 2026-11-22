
import hashlib
import streamlit as st

from core.document_parser import parse_document
from database.repositories.project_repository import list_projects
from database.repositories.document_repository import create_document_version
from components.header import render_header


# ============================================================
# 页面初始化
# ============================================================

render_header(
    title="需求文档",
    description="导入和管理游戏策划需求文档，为后续结构化分析提供原始需求依据。",
    breadcrumb=["需求中心", "需求文档"],
)


# ============================================================
# 页面专属样式
# ============================================================

st.html("""
<style>
/* 页面区块 */
.gt-section {
    margin: 1.5rem 0 0.8rem 0;
}

.gt-section-title {
    font-size: 1.05rem;
    font-weight: 650;
    color: #292746;
    margin-bottom: 0.25rem;
}

.gt-section-desc {
    font-size: 0.85rem;
    color: #85839a;
    margin-bottom: 0.8rem;
}

/* 通用卡片 */
.gt-panel {
    background: #ffffff;
    border: 1px solid #eeeafd;
    border-radius: 14px;
    padding: 1.2rem 1.35rem;
    margin-bottom: 1rem;
}

.gt-panel-title {
    font-size: 0.95rem;
    font-weight: 650;
    color: #302d50;
    margin-bottom: 0.45rem;
}

.gt-panel-desc {
    color: #85839a;
    font-size: 0.82rem;
    line-height: 1.6;
}

/* 文件信息 */
.gt-file-info {
    background: #f8f7ff;
    border: 1px solid #eae7fc;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin-top: 0.7rem;
}

.gt-file-name {
    color: #39345f;
    font-weight: 650;
    font-size: 0.92rem;
    overflow-wrap: anywhere;
}

.gt-file-meta {
    color: #85839a;
    font-size: 0.8rem;
    margin-top: 0.3rem;
}

/* 结果统计 */
.gt-stat-card {
    background: #ffffff;
    border: 1px solid #eeeafd;
    border-radius: 12px;
    padding: 0.9rem 1rem;
    min-height: 92px;
}

.gt-stat-label {
    font-size: 0.78rem;
    color: #85839a;
    margin-bottom: 0.4rem;
}

.gt-stat-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #39345f;
    overflow-wrap: anywhere;
}

/* 状态说明 */
.gt-status-panel {
    background: #f6f4ff;
    border: 1px solid #e9e5ff;
    border-radius: 12px;
    padding: 1rem 1.15rem;
    margin: 0.8rem 0;
}

.gt-status-title {
    color: #5143a3;
    font-weight: 650;
    font-size: 0.92rem;
    margin-bottom: 0.25rem;
}

.gt-status-desc {
    color: #77728f;
    font-size: 0.83rem;
    line-height: 1.6;
}

/* 小屏适配 */
@media (max-width: 768px) {
    .gt-panel {
        padding: 1rem;
    }
}
</style>
""")


# ============================================================
# 一、选择项目
# ============================================================

st.markdown("""
<div class="gt-section">
    <div class="gt-section-title">一、选择所属项目</div>
    <div class="gt-section-desc">
        选择需求文档归属的游戏项目。
    </div>
</div>
""", unsafe_allow_html=True)

try:
    projects = list_projects()
except Exception as e:
    st.error(f"项目列表加载失败：{e}")
    st.stop()

if not projects:
    st.warning("当前没有可用的游戏项目，请先创建项目。")
    st.stop()

project_map = {
    project["id"]: project
    for project in projects
}

project_ids = list(project_map.keys())

selected_project_id = st.selectbox(
    "选择所属游戏项目",
    options=project_ids,
    format_func=lambda project_id: project_map[project_id]["name"],
    key="document_project_id",
)


# ============================================================
# 二、填写文档信息
# ============================================================

st.markdown("""
<div class="gt-section">
    <div class="gt-section-title">二、填写文档信息</div>
    <div class="gt-section-desc">
        设置文档名称和唯一业务标识，便于后续版本管理。
    </div>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    col1, col2 = st.columns(2)

    with col1:
        document_name = st.text_input(
            "文档名称",
            placeholder="例如：登录功能需求说明",
            key="document_name",
        )

    with col2:
        document_key = st.text_input(
            "文档标识（document_key）",
            placeholder="例如：LOGIN_REQUIREMENT",
            key="document_key",
        )


# ============================================================
# 三、上传文档
# ============================================================

st.markdown("""
<div class="gt-section">
    <div class="gt-section-title">三、上传需求文档</div>
    <div class="gt-section-desc">
        支持 DOCX、PDF、Markdown 和 TXT 格式。
    </div>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "上传游戏策划需求文档",
    type=["docx", "pdf", "md", "txt"],
    key="requirement_document",
)

if uploaded_file is None:
    st.info("请上传 DOCX、PDF、Markdown 或 TXT 格式的需求文档。")
    st.stop()

file_bytes = uploaded_file.getvalue()
file_hash = hashlib.sha256(file_bytes).hexdigest()

with st.container(border=True):
    st.markdown("**已选择文件**")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write(uploaded_file.name)

    with col2:
        st.caption(f"{len(file_bytes):,} bytes")


# ============================================================
# 四、解析文档
# ============================================================

st.markdown("""
<div class="gt-section">
    <div class="gt-section-title">四、解析文档</div>
    <div class="gt-section-desc">
        提取上传文件中的文本内容，供后续结构化需求分析使用。
    </div>
</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("**文档解析**")
    st.caption("确认项目、文档信息和上传文件无误后，开始解析。")

    if st.button(
        "开始解析文档",
        type="primary",
        width="stretch",
    ):

        st.session_state.pop("parsed_document", None)

        if not document_name.strip():
            st.error("请输入文档名称。")

        elif not document_key.strip():
            st.error("请输入文档标识。")

        else:
            try:
                with st.spinner("正在解析文档..."):
                    result = parse_document(
                        uploaded_file.name,
                        file_bytes,
                    )

                st.session_state["parsed_document"] = {
                    "project_id": selected_project_id,
                    "document_name": document_name.strip(),
                    "document_key": document_key.strip(),
                    "file_name": uploaded_file.name,
                    "file_hash": file_hash,
                    "result": result,
                    "saved_document": None,
                }

                st.success("文档解析成功！")

            except Exception as e:
                st.error(f"文档解析失败：{e}")


# ============================================================
# 五、展示解析结果
# ============================================================

parsed_document = st.session_state.get("parsed_document")

is_current_parse = False

if parsed_document is not None:

    is_current_parse = (
        parsed_document["project_id"] == selected_project_id
        and parsed_document["document_name"] == document_name.strip()
        and parsed_document["document_key"] == document_key.strip()
        and parsed_document["file_hash"] == file_hash
    )

    if not is_current_parse:
        st.warning(
            "项目、文档信息或上传文件已发生变化，请重新解析后再保存。"
        )


if is_current_parse:

    result = parsed_document["result"]

    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">五、解析结果预览</div>
        <div class="gt-section-desc">
            查看文件解析信息和提取出的文档文本。
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("文件类型", result["file_type"])

    with col2:
        st.metric("文本字符数", f'{result["char_count"]:,}')

    with col3:
        st.metric(
            "PDF 页数",
            result["page_count"]
            if result["page_count"] is not None
            else "不适用",
        )

    with st.container(border=True):
        st.markdown("**文档解析内容**")
        st.caption("以下内容为从上传文件中提取的文本。")

        st.text_area(
            "文档解析内容",
            value=result["content"],
            height=400,
            disabled=True,
            label_visibility="collapsed",
        )

    # ========================================================
    # 六、保存文档
    # ========================================================

    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">六、保存需求文档</div>
        <div class="gt-section-desc">
            将解析结果保存到当前项目的文档库。
        </div>
    </div>
    """, unsafe_allow_html=True)

    saved_document = parsed_document.get("saved_document")

    if saved_document is None:

        with st.container(border=True):
            st.markdown("**保存到项目文档库**")
            st.caption(
                "保存后可在需求版本管理页面查看该文档及其历史版本。"
            )

            if st.button(
                "保存到项目文档库",
                type="primary",
                width="stretch",
            ):
                try:
                    with st.spinner("正在保存文档..."):

                        created_document = create_document_version(
                            project_id=parsed_document["project_id"],
                            document_key=parsed_document["document_key"],
                            document_name=parsed_document["document_name"],
                            file_type=result["file_type"],
                            file_path=None,
                            parsed_content=result["content"],
                            file_hash=parsed_document["file_hash"],
                            page_count=result["page_count"],
                            char_count=result["char_count"],
                        )

                    parsed_document["saved_document"] = created_document
                    st.session_state["parsed_document"] = parsed_document

                    st.success("需求文档保存成功！")
                    st.rerun()

                except Exception as e:
                    st.error(f"文档保存失败：{e}")

    else:

        st.success("需求文档已成功保存到项目文档库！")

        col1, col2, col3 = st.columns(3)

        col1.metric("文档版本", f"V{saved_document['version']}")
        col2.metric("文档类型", saved_document["file_type"].upper())
        col3.metric("字符数量", f'{saved_document["char_count"]:,}')

        with st.container(border=True):
            st.markdown("**文档保存信息**")

            st.code(
                f"文档 ID：{saved_document['id']}\n"
                f"项目 ID：{saved_document['project_id']}\n"
                f"文档标识：{saved_document['document_key']}\n"
                f"文档名称：{saved_document['document_name']}\n"
                f"版本号：V{saved_document['version']}"
            )

            st.info("历史版本可前往「需求版本管理」页面查看。")


st.divider()
st.caption("GameTest AI · 需求文档管理")
