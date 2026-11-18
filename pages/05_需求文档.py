
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

st.markdown("""
<style>
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-color: #eeeafd;
    border-radius: 16px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 一、选择项目
# ============================================================

st.subheader("一、选择所属项目")

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

st.divider()
st.subheader("二、填写文档信息")

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

st.subheader("三、上传需求文档")

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

st.caption(f"文件名称：{uploaded_file.name}")
st.caption(f"文件大小：{len(file_bytes):,} bytes")


# ============================================================
# 四、解析文档
# ============================================================

st.divider()
st.subheader("四、解析文档")

if st.button("开始解析文档", type="primary", use_container_width=True):

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
        st.warning("项目、文档信息或上传文件已发生变化，请重新解析后再保存。")


if is_current_parse:

    result = parsed_document["result"]

    st.divider()
    st.subheader("五、解析结果预览")

    col1, col2, col3 = st.columns(3)

    col1.metric("文件类型", result["file_type"])
    col2.metric("文本字符数", result["char_count"])
    col3.metric(
        "PDF 页数",
        result["page_count"] if result["page_count"] is not None else "不适用",
    )

    st.text_area(
        "文档解析内容",
        value=result["content"],
        height=400,
        disabled=True,
    )

    # ========================================================
    # 六、保存文档
    # ========================================================

    st.divider()
    st.subheader("六、保存需求文档")

    saved_document = parsed_document.get("saved_document")

    if saved_document is None:

        if st.button(
            "保存到项目文档库",
            type="primary",
            use_container_width=True,
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
        col3.metric("字符数量", saved_document["char_count"])

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
