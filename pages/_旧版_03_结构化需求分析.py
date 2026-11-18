
import streamlit as st
import pandas as pd
import json

from core.time_utils import format_local_datetime

from database.repositories.project_repository import list_projects
from database.repositories.document_repository import (
    list_documents,
    get_document,
)
from core.requirement_analyzer import analyze_requirement
from database.repositories.requirement_repository import (
    create_requirement_analysis,
)


st.set_page_config(
    page_title="结构化需求分析",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 结构化需求分析")
st.caption("GameTest AI V0.1 · 项目文档库 + DeepSeek + Pydantic")

st.markdown("""
选择项目及其最新有效策划文档版本，
系统将自动提取业务规则、数值约束和待确认问题，
并将结果转换为可供后续测试点生成使用的结构化数据。
""")


# ==================================================
# 一、Session State 初始化
# ==================================================

if "structured_analysis" not in st.session_state:
    st.session_state.structured_analysis = None

if "analysis_file_name" not in st.session_state:
    st.session_state.analysis_file_name = None

if "selected_analysis_project_id" not in st.session_state:
    st.session_state.selected_analysis_project_id = None

if "selected_analysis_document_id" not in st.session_state:
    st.session_state.selected_analysis_document_id = None

if "analysis_project_id" not in st.session_state:
    st.session_state.analysis_project_id = None

if "analysis_document_id" not in st.session_state:
    st.session_state.analysis_document_id = None

# 数据库保存状态
if "saved_analysis_id" not in st.session_state:
    st.session_state.saved_analysis_id = None

if "saved_analysis_created_at" not in st.session_state:
    st.session_state.saved_analysis_created_at = None


# ==================================================
# 二、辅助函数
# ==================================================

def get_project_name(project):
    return (
        project.get("name")
        or project.get("project_name")
        or project.get("title")
        or project.get("id", "未命名项目")
    )


def get_document_name(document):
    return (
        document.get("file_name")
        or document.get("original_filename")
        or document.get("document_name")
        or document.get("filename")
        or document.get("document_key")
        or document.get("id", "未命名文档")
    )


def get_document_type(document):
    return (
        document.get("file_type")
        or document.get("document_type")
        or "未知"
    )


def get_document_content(document):
    return document.get("parsed_content") or ""


def get_document_label(document):
    name = get_document_name(document)
    version = document.get("version", "?")
    document_key = document.get("document_key", "")

    return f"{name} | {document_key} | V{version}"


# ==================================================
# 三、选择项目
# ==================================================

st.header("一、选择项目")

try:
    projects = list_projects()

except Exception as e:
    st.error("读取项目列表失败")
    st.exception(e)
    st.stop()


if not projects:
    st.info("当前没有可用项目，请先在项目管理页面创建项目。")
    st.stop()


project_map = {
    project["id"]: project
    for project in projects
}

project_ids = list(project_map.keys())

selected_project_id = st.selectbox(
    "选择项目",
    options=project_ids,
    format_func=lambda project_id: get_project_name(
        project_map[project_id]
    ),
    key="analysis_project_selector"
)


# ==================================================
# 四、选择最新有效文档版本
# ==================================================

st.header("二、选择需求文档")

try:
    all_documents = list_documents(
        project_id=selected_project_id
    )

    # 同一 document_key 只保留最新有效版本
    latest_documents = {}

    for document in all_documents:
        document_key = document["document_key"]

        if document_key not in latest_documents:
            latest_documents[document_key] = document

    documents = list(latest_documents.values())

except Exception as e:
    st.error("读取项目文档列表失败")
    st.exception(e)
    st.stop()


if not documents:
    st.info(
        "当前项目还没有可用的需求文档，请先前往「需求文档导入与解析」页面导入文档。"
    )
    st.stop()


document_map = {
    document["id"]: document
    for document in documents
}

document_ids = list(document_map.keys())

selected_document_id = st.selectbox(
    "选择需求文档",
    options=document_ids,
    format_func=lambda document_id: get_document_label(
        document_map[document_id]
    ),
    key="analysis_document_selector"
)


# ==================================================
# 五、切换项目或文档时清除旧分析结果
# ==================================================

if (
    st.session_state.selected_analysis_project_id
    != selected_project_id
    or
    st.session_state.selected_analysis_document_id
    != selected_document_id
):

    st.session_state.structured_analysis = None
    st.session_state.analysis_file_name = None

    st.session_state.analysis_project_id = None
    st.session_state.analysis_document_id = None

    # 清除上一份分析结果的数据库保存状态
    st.session_state.saved_analysis_id = None
    st.session_state.saved_analysis_created_at = None

    st.session_state.selected_analysis_project_id = (
        selected_project_id
    )

    st.session_state.selected_analysis_document_id = (
        selected_document_id
    )


# ==================================================
# 六、读取选中文档完整内容
# ==================================================

st.header("三、文档信息")

try:
    selected_document = get_document(
        selected_document_id
    )

except Exception as e:
    st.error("读取文档详情失败")
    st.exception(e)
    st.stop()


if selected_document is None:
    st.error("找不到选中的文档记录。")
    st.stop()


# 检查文档删除状态
if selected_document.get("is_deleted", 0):
    st.warning("该文档已被删除，不能用于新的需求分析。")
    st.stop()


# 检查文档所属项目
if selected_document.get("project_id") != selected_project_id:
    st.error("文档所属项目与当前选择的项目不一致。")
    st.stop()


content = get_document_content(selected_document)

if not content.strip():
    st.warning("该文档没有可用于分析的解析文本。")
    st.stop()


# ==================================================
# 七、展示文档元信息
# ==================================================

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "文档版本",
    f"V{selected_document.get('version', '-')}"
)

col2.metric(
    "文档类型",
    get_document_type(selected_document)
)

col3.metric(
    "文本字符数",
    f"{len(content):,}"
)

col4.metric(
    "文档标识",
    selected_document.get("document_key", "-")
)

st.write(
    f"**文档名称：** {get_document_name(selected_document)}"
)

st.write(
    f"**导入时间：** "
    f"{format_local_datetime(selected_document.get('created_at'))}"
)


# ==================================================
# 八、查看文档解析内容
# ==================================================

st.header("四、文档解析内容")

with st.expander("查看完整文档文本", expanded=False):
    st.text_area(
        "原始文档文本",
        value=content,
        height=350,
        disabled=True
    )


# ==================================================
# 九、执行结构化需求分析
# ==================================================

st.divider()

st.header("五、结构化需求分析")

st.markdown("""
点击下方按钮，系统将调用 DeepSeek 分析当前选中的需求文档。
分析结果经过 Pydantic 数据结构校验后展示。
""")

if st.button(
    "开始结构化需求分析",
    type="primary",
    use_container_width=True
):

    # 重新分析时清除旧保存状态
    st.session_state.saved_analysis_id = None
    st.session_state.saved_analysis_created_at = None

    with st.spinner("DeepSeek 正在分析策划需求，请稍候..."):

        try:
            result = analyze_requirement(content)

            # Pydantic 对象转换为 JSON 兼容字典
            analysis_data = result.model_dump(
                mode="json"
            )

            # 保存当前分析结果
            st.session_state.structured_analysis = (
                analysis_data
            )

            # 绑定当前项目和文档
            st.session_state.analysis_project_id = (
                selected_project_id
            )

            st.session_state.analysis_document_id = (
                selected_document_id
            )

            st.session_state.analysis_file_name = (
                get_document_name(selected_document)
            )

            st.success("结构化需求分析完成！")

        except Exception as e:
            st.session_state.structured_analysis = None
            st.session_state.analysis_project_id = None
            st.session_state.analysis_document_id = None

            st.error("需求分析失败，请检查 AI 服务或返回数据。")
            st.exception(e)


# ==================================================
# 十、展示分析结果
# ==================================================

result = st.session_state.structured_analysis

# 确认分析结果属于当前项目和文档
is_current_analysis = (
    result is not None
    and
    st.session_state.analysis_project_id == selected_project_id
    and
    st.session_state.analysis_document_id == selected_document_id
)


if is_current_analysis:

    st.divider()

    st.header("六、分析结果")

    st.caption(
        f"分析文档：{st.session_state.analysis_file_name}"
    )

    # --------------------------------------------------
    # 1. 需求摘要
    # --------------------------------------------------

    st.subheader("一、需求摘要")

    st.write(f"**功能模块：** {result['module']}")
    st.write(result["summary"])

    # --------------------------------------------------
    # 2. 核心业务规则
    # --------------------------------------------------

    st.subheader("二、核心业务规则")

    rules = result.get("business_rules", [])

    if rules:

        rule_rows = []

        for rule in rules:
            rule_rows.append({
                "规则编号": rule["rule_id"],
                "规则描述": rule["rule_text"],
                "需求依据": rule["source_text"],
                "确认状态": (
                    "已明确"
                    if rule["status"] == "confirmed"
                    else "待确认"
                )
            })

        st.dataframe(
            pd.DataFrame(rule_rows),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("暂未提取到业务规则。")

    # --------------------------------------------------
    # 3. 前置条件
    # --------------------------------------------------

    st.subheader("三、前置条件")

    preconditions = result.get("preconditions", [])

    if preconditions:
        for item in preconditions:
            st.markdown(f"- {item}")
    else:
        st.info("暂未提取到前置条件。")

    # --------------------------------------------------
    # 4. 业务状态
    # --------------------------------------------------

    st.subheader("四、业务状态")

    states = result.get("states", [])

    if states:
        for item in states:
            st.markdown(f"- {item}")
    else:
        st.info("暂未提取到业务状态。")

    # --------------------------------------------------
    # 5. 数值约束
    # --------------------------------------------------

    st.subheader("五、数值约束")

    numeric_constraints = result.get(
        "numeric_constraints", []
    )

    if numeric_constraints:

        numeric_rows = []

        for item in numeric_constraints:
            numeric_rows.append({
                "数值名称": item["name"],
                "数值": item["value"],
                "单位": item.get("unit", ""),
                "说明": item.get("description", "")
            })

        st.dataframe(
            pd.DataFrame(numeric_rows),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("暂未提取到数值约束。")

    # --------------------------------------------------
    # 6. 异常场景
    # --------------------------------------------------

    st.subheader("六、异常场景")

    exception_cases = result.get(
        "exception_cases", []
    )

    if exception_cases:
        for item in exception_cases:
            st.markdown(f"- {item}")
    else:
        st.info("暂未提取到异常场景。")

    # --------------------------------------------------
    # 7. 待策划确认的问题
    # --------------------------------------------------

    st.subheader("七、待策划确认的问题")

    questions = result.get("open_questions", [])

    if questions:

        for index, question in enumerate(questions, 1):
            st.warning(f"{index}. {question}")

    else:
        st.success("当前未发现需要确认的问题。")

    # --------------------------------------------------
    # 8. 完整 JSON
    # --------------------------------------------------

    st.divider()

    st.subheader("八、结构化数据")

    with st.expander("查看完整 JSON"):

        st.json(result)

    json_text = json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    )

    st.download_button(
        label="下载需求分析 JSON",
        data=json_text,
        file_name="requirement_analysis.json",
        mime="application/json"
    )


    # --------------------------------------------------
    # 9. 数据库持久化
    # --------------------------------------------------

    st.divider()

    st.subheader("九、保存分析结果")

    if st.session_state.saved_analysis_id:

        st.success("当前分析结果已经保存到数据库。")

        st.write(
            f"**分析记录 ID：** "
            f"`{st.session_state.saved_analysis_id}`"
        )

        st.write(
            f"**创建时间：** "
            f"{format_local_datetime(st.session_state.saved_analysis_created_at)}"
        )

    else:

        st.info(
            "当前分析结果尚未保存。"
            "确认分析内容无误后，可以保存到数据库。"
        )

        if st.button(
            "保存分析结果",
            type="primary",
            use_container_width=True,
            key="save_requirement_analysis"
        ):

            try:
                with st.spinner("正在保存分析结果..."):

                    saved_record = create_requirement_analysis(
                        project_id=selected_project_id,
                        document_id=selected_document_id,
                        module=result["module"],
                        summary=result["summary"],
                        analysis_data=result
                    )

                # 保存成功后记录数据库返回信息
                # 保留原始 UTC 时间，不在 Session State 中转换
                st.session_state.saved_analysis_id = (
                    saved_record["id"]
                )

                st.session_state.saved_analysis_created_at = (
                    saved_record["created_at"]
                )

                st.success("分析结果已成功保存到数据库！")

                st.write(
                    f"**分析记录 ID：** "
                    f"`{saved_record['id']}`"
                )

                st.write(
                    f"**创建时间：** "
                    f"{format_local_datetime(saved_record.get('created_at'))}"
                )

            except Exception as e:

                st.error("分析结果保存失败，请检查数据库记录和关联关系。")
                st.exception(e)


else:

    st.info(
        "当前文档尚未生成结构化分析结果，请点击上方按钮开始分析。"
    )
