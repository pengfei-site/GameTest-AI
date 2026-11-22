# 需求中心各功能模块：保留原有业务逻辑，统一由需求中心页面的 Tab 调用。

def render_document_tab():
    
    import hashlib
    import streamlit as st
    
    from core.document_parser import parse_document
    from database.repositories.project_repository import list_projects
    from database.repositories.document_repository import create_document_version
    from components.header import render_header
    
    
    # ============================================================
    # 页面初始化
    # ============================================================
    
    
    
    
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
        return
    
    if not projects:
        st.warning("当前没有可用的游戏项目，请先创建项目。")
        return
    
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
        return
    
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
    


def render_analysis_tab():
    
    import streamlit as st
    import pandas as pd
    import json
    
    from components.header import render_header
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
    
    
    # ============================================================
    # 页面初始化
    # ============================================================
    
    
    
    
    # ============================================================
    # 页面专属样式
    # ============================================================
    
    st.html("""
    <style>
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
        font-size: 0.84rem;
        color: #85839a;
        line-height: 1.6;
    }
    
    .gt-info-panel {
        background: #ffffff;
        border: 1px solid #eeeafd;
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        margin-bottom: 1rem;
    }
    
    .gt-info-title {
        color: #39345f;
        font-size: 0.95rem;
        font-weight: 650;
        margin-bottom: 0.45rem;
    }
    
    .gt-info-desc {
        color: #85839a;
        font-size: 0.82rem;
        line-height: 1.6;
    }
    
    .gt-analysis-banner {
        background: linear-gradient(120deg, #f4f1ff 0%, #faf9ff 100%);
        border: 1px solid #e9e4ff;
        border-radius: 14px;
        padding: 1.25rem 1.4rem;
        margin: 0.8rem 0 1rem 0;
    }
    
    .gt-analysis-title {
        color: #433b83;
        font-size: 1rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    
    .gt-analysis-desc {
        color: #77728f;
        font-size: 0.84rem;
        line-height: 1.7;
    }
    
    .gt-result-panel {
        background: #ffffff;
        border: 1px solid #eeeafd;
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        margin: 0.7rem 0;
    }
    
    .gt-result-heading {
        color: #39345f;
        font-size: 0.98rem;
        font-weight: 700;
        margin-bottom: 0.65rem;
    }
    
    .gt-question-panel {
        background: #fffaf1;
        border: 1px solid #f4e5c9;
        border-radius: 12px;
        padding: 1rem 1.15rem;
        margin: 0.6rem 0;
    }
    
    .gt-save-panel {
        background: #f7f6ff;
        border: 1px solid #e9e5fc;
        border-radius: 14px;
        padding: 1.2rem 1.3rem;
        margin-top: 0.8rem;
    }
    
    @media (max-width: 768px) {
        .gt-info-panel,
        .gt-result-panel,
        .gt-save-panel {
            padding: 0.9rem;
        }
    }
    </style>
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
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">一、选择项目</div>
        <div class="gt-section-desc">
            选择需要进行需求分析的游戏项目。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        projects = list_projects()
    except Exception as e:
        st.error("读取项目列表失败")
        st.exception(e)
        return
    
    if not projects:
        st.info("当前没有可用项目，请先创建项目。")
        return
    
    project_map = {
        project["id"]: project
        for project in projects
    }
    
    project_ids = list(project_map.keys())
    
    with st.container(border=True):
        selected_project_id = st.selectbox(
            "选择项目",
            options=project_ids,
            format_func=lambda project_id: get_project_name(
                project_map[project_id]
            ),
            key="analysis_project_selector",
        )
    
    
    # ==================================================
    # 四、选择最新有效文档版本
    # ==================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">二、选择需求文档</div>
        <div class="gt-section-desc">
            系统默认读取每个文档标识对应的最新有效版本。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        all_documents = list_documents(
            project_id=selected_project_id
        )
    
        latest_documents = {}
    
        for document in all_documents:
            document_key = document["document_key"]
    
            if document_key not in latest_documents:
                latest_documents[document_key] = document
    
        documents = list(latest_documents.values())
    
    except Exception as e:
        st.error("读取项目文档列表失败")
        st.exception(e)
        return
    
    if not documents:
        st.info(
            "当前项目还没有可用的需求文档，请先前往「需求文档」页面导入文档。"
        )
        return
    
    document_map = {
        document["id"]: document
        for document in documents
    }
    
    document_ids = list(document_map.keys())
    
    with st.container(border=True):
        selected_document_id = st.selectbox(
            "选择需求文档",
            options=document_ids,
            format_func=lambda document_id: get_document_label(
                document_map[document_id]
            ),
            key="analysis_document_selector",
        )
    
    
    # ==================================================
    # 五、切换项目或文档时清除旧分析结果
    # ==================================================
    
    if (
        st.session_state.selected_analysis_project_id != selected_project_id
        or
        st.session_state.selected_analysis_document_id != selected_document_id
    ):
        st.session_state.structured_analysis = None
        st.session_state.analysis_file_name = None
    
        st.session_state.analysis_project_id = None
        st.session_state.analysis_document_id = None
    
        st.session_state.saved_analysis_id = None
        st.session_state.saved_analysis_created_at = None
    
        st.session_state.selected_analysis_project_id = selected_project_id
        st.session_state.selected_analysis_document_id = selected_document_id
    
    
    # ==================================================
    # 六、读取选中文档完整内容
    # ==================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">三、文档信息</div>
        <div class="gt-section-desc">
            查看当前选中文档的基本信息和导入内容。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        selected_document = get_document(selected_document_id)
    except Exception as e:
        st.error("读取文档详情失败")
        st.exception(e)
        return
    
    if selected_document is None:
        st.error("找不到选中的文档记录。")
        return
    
    if selected_document.get("is_deleted", 0):
        st.warning("该文档已被删除，不能用于新的需求分析。")
        return
    
    if selected_document.get("project_id") != selected_project_id:
        st.error("文档所属项目与当前选择的项目不一致。")
        return
    
    content = get_document_content(selected_document)
    
    if not content.strip():
        st.warning("该文档没有可用于分析的解析文本。")
        return
    
    
    # ==================================================
    # 七、展示文档元信息
    # ==================================================
    
    with st.container(border=True):
    
        st.markdown("**当前分析文档**")
    
        st.write(f"**文档名称：** {get_document_name(selected_document)}")
    
        st.write(
            f"**导入时间：** "
            f"{format_local_datetime(selected_document.get('created_at'))}"
        )
    
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
    
    
    # ==================================================
    # 八、查看文档解析内容
    # ==================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">四、文档解析内容</div>
        <div class="gt-section-desc">
            可展开查看完整原始文本，确认需求上下文。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("查看完整文档文本", expanded=False):
        st.text_area(
            "原始文档文本",
            value=content,
            height=350,
            disabled=True,
        )
    
    
    # ==================================================
    # 九、执行结构化需求分析
    # ==================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">五、结构化需求分析</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.html("""
    <div class="gt-analysis-banner">
        <div class="gt-analysis-title">AI 需求分析</div>
        <div class="gt-analysis-desc">
            AI 将从当前文档中提取业务规则、前置条件、业务状态、
            数值约束、异常场景以及待策划确认的问题。
            分析结果经过 Pydantic 数据结构校验后展示。
        </div>
    </div>
    """)
    
    if st.button(
        "开始结构化需求分析",
        type="primary",
        width="stretch",
    ):
    
        st.session_state.saved_analysis_id = None
        st.session_state.saved_analysis_created_at = None
    
        with st.spinner("AI 正在分析策划需求，请稍候..."):
    
            try:
                result = analyze_requirement(content)
    
                analysis_data = result.model_dump(
                    mode="json"
                )
    
                st.session_state.structured_analysis = analysis_data
    
                st.session_state.analysis_project_id = selected_project_id
                st.session_state.analysis_document_id = selected_document_id
    
                st.session_state.analysis_file_name = get_document_name(
                    selected_document
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
    
    is_current_analysis = (
        result is not None
        and st.session_state.analysis_project_id == selected_project_id
        and st.session_state.analysis_document_id == selected_document_id
    )
    
    if is_current_analysis:
    
        st.divider()
    
        st.markdown("""
        <div class="gt-section">
            <div class="gt-section-title">六、分析结果</div>
            <div class="gt-section-desc">
                以下内容为 AI 从当前需求文档中提取的结构化信息。
            </div>
        </div>
        """, unsafe_allow_html=True)
    
        st.caption(
            f"分析文档：{st.session_state.analysis_file_name}"
        )
    
        # ==================================================
        # 1. 需求摘要
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**一、需求摘要**")
    
            st.markdown(f"**功能模块：** {result['module']}")
    
            st.write(result["summary"])
    
    
        # ==================================================
        # 2. 核心业务规则
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**二、核心业务规则**")
    
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
                        ),
                    })
    
                st.dataframe(
                    pd.DataFrame(rule_rows),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("暂未提取到业务规则。")
    
    
        # ==================================================
        # 3. 前置条件
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**三、前置条件**")
    
            preconditions = result.get("preconditions", [])
    
            if preconditions:
                for item in preconditions:
                    st.markdown(f"- {item}")
            else:
                st.info("暂未提取到前置条件。")
    
    
        # ==================================================
        # 4. 业务状态
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**四、业务状态**")
    
            states = result.get("states", [])
    
            if states:
                for item in states:
                    st.markdown(f"- {item}")
            else:
                st.info("暂未提取到业务状态。")
    
    
        # ==================================================
        # 5. 数值约束
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**五、数值约束**")
    
            numeric_constraints = result.get(
                "numeric_constraints", []
            )
    
            if numeric_constraints:
                numeric_rows = []
    
                for item in numeric_constraints:
                    value = item.get("value")
    
                    numeric_rows.append({
                        "数值名称": str(item.get("name") or ""),
                        # 展示层统一转换为字符串，避免 int / float / str 混合
                        "数值": "" if value is None else str(value),
                        "单位": str(item.get("unit") or ""),
                        "说明": str(item.get("description") or ""),
                    })
    
                numeric_df = pd.DataFrame(
                    numeric_rows,
                    columns=["数值名称", "数值", "单位", "说明"],
                )
    
                st.dataframe(
                    numeric_df,
                    width="stretch",
                    hide_index=True,
                )
    
            else:
                st.info("暂未提取到数值约束。")
    
    
        # ==================================================
        # 6. 异常场景
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**六、异常场景**")
    
            exception_cases = result.get(
                "exception_cases", []
            )
    
            if exception_cases:
                for item in exception_cases:
                    st.markdown(f"- {item}")
            else:
                st.info("暂未提取到异常场景。")
    
    
        # ==================================================
        # 7. 待策划确认的问题
        # ==================================================
    
        with st.container(border=True):
    
            st.markdown("**七、待策划确认的问题**")
    
            questions = result.get("open_questions", [])
    
            if questions:
                for index, question in enumerate(questions, 1):
                    st.warning(f"{index}. {question}")
            else:
                st.success("当前未发现需要确认的问题。")
    
    
        # ==================================================
        # 8. JSON 结构化数据
        # ==================================================
    
        st.markdown("""
        <div class="gt-section">
            <div class="gt-section-title">八、结构化数据</div>
            <div class="gt-section-desc">
                可查看完整 JSON 或下载分析结果。
            </div>
        </div>
        """, unsafe_allow_html=True)
    
        with st.expander("查看完整 JSON"):
            st.json(result)
    
        json_text = json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    
        st.download_button(
            label="下载需求分析 JSON",
            data=json_text,
            file_name="requirement_analysis.json",
            mime="application/json",
        )
    
    
        # ==================================================
        # 十一、数据库持久化
        # ==================================================
    
        st.divider()
    
        st.markdown("""
        <div class="gt-section">
            <div class="gt-section-title">九、保存分析结果</div>
            <div class="gt-section-desc">
                将当前结构化分析结果保存为项目分析记录。
            </div>
        </div>
        """, unsafe_allow_html=True)
    
        if st.session_state.saved_analysis_id:
    
            st.success("当前分析结果已经保存到数据库。")
    
            with st.container(border=True):
    
                st.write(
                    f"**分析记录 ID：** "
                    f"`{st.session_state.saved_analysis_id}`"
                )
    
                st.write(
                    f"**创建时间：** "
                    f"{format_local_datetime(st.session_state.saved_analysis_created_at)}"
                )
    
        else:
    
            with st.container(border=True):
    
                st.info(
                    "当前分析结果尚未保存。确认分析内容无误后，可以保存到数据库。"
                )
    
                if st.button(
                    "保存分析结果",
                    type="primary",
                    width="stretch",
                    key="save_requirement_analysis",
                ):
    
                    try:
                        with st.spinner("正在保存分析结果..."):
    
                            saved_record = create_requirement_analysis(
                                project_id=selected_project_id,
                                document_id=selected_document_id,
                                module=result["module"],
                                summary=result["summary"],
                                analysis_data=result,
                            )
    
                        st.session_state.saved_analysis_id = saved_record["id"]
                        st.session_state.saved_analysis_created_at = saved_record["created_at"]
    
                        st.success("分析结果已成功保存到数据库！")
    
                        st.write(
                            f"**分析记录 ID：** `{saved_record['id']}`"
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
    
    
    st.divider()
    st.caption("GameTest AI · 结构化需求分析")
    


def render_version_tab():
    
    import streamlit as st
    
    from components.header import render_header
    from core.time_utils import format_local_datetime
    
    from database.repositories.project_repository import list_projects
    
    from database.repositories.document_repository import (
        list_documents,
        get_document,
        soft_delete_document,
        restore_document,
    )
    
    
    # ============================================================
    # 页面初始化
    # ============================================================
    
    
    
    
    # ============================================================
    # 页面专属样式
    # ============================================================
    
    st.html("""
    <style>
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
        font-size: 0.84rem;
        color: #85839a;
        line-height: 1.6;
    }
    
    .gt-panel {
        background: #ffffff;
        border: 1px solid #eeeafd;
        border-radius: 14px;
        padding: 1.1rem 1.25rem;
        margin: 0.7rem 0;
    }
    
    .gt-panel-title {
        color: #39345f;
        font-size: 0.98rem;
        font-weight: 700;
        margin-bottom: 0.6rem;
    }
    
    .gt-panel-desc {
        color: #85839a;
        font-size: 0.82rem;
        line-height: 1.6;
    }
    
    .gt-filter-panel {
        background: #f8f7ff;
        border: 1px solid #ebe7fc;
        border-radius: 14px;
        padding: 1rem 1.2rem 0.4rem 1.2rem;
        margin: 0.8rem 0;
    }
    
    .gt-version-header {
        background: linear-gradient(120deg, #f4f1ff 0%, #faf9ff 100%);
        border: 1px solid #e9e4ff;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    
    .gt-version-title {
        color: #433b83;
        font-size: 0.98rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    
    .gt-version-desc {
        color: #77728f;
        font-size: 0.82rem;
        line-height: 1.6;
    }
    
    .gt-action-panel {
        background: #faf9ff;
        border: 1px solid #eeeafd;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: 0.8rem 0;
    }
    
    .gt-content-panel {
        background: #ffffff;
        border: 1px solid #e9e5fc;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin-top: 1rem;
    }
    
    @media (max-width: 768px) {
        .gt-panel,
        .gt-action-panel,
        .gt-content-panel {
            padding: 0.85rem;
        }
    }
    </style>
    """)
    
    
    # ============================================================
    # 一、选择项目
    # ============================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">一、选择项目</div>
        <div class="gt-section-desc">
            选择需要管理需求文档版本的游戏项目。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        projects = list_projects()
    except Exception as e:
        st.error(f"项目列表加载失败：{e}")
        return
    
    if not projects:
        st.info("当前没有可用项目，请先创建项目。")
        return
    
    project_map = {
        project["id"]: project
        for project in projects
    }
    
    project_ids = list(project_map.keys())
    
    with st.container(border=True):
        selected_project_id = st.selectbox(
            "选择所属游戏项目",
            options=project_ids,
            format_func=lambda project_id: project_map[project_id]["name"],
            key="version_project_id",
        )
    
    
    # ============================================================
    # 二、读取文档版本
    # ============================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">二、需求文档版本</div>
        <div class="gt-section-desc">
            查看当前项目下的需求文档及其全部历史版本。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        saved_documents = list_documents(
            project_id=selected_project_id,
            include_deleted=True,
        )
    except Exception as e:
        st.error(f"需求文档版本加载失败：{e}")
        return
    
    
    # ============================================================
    # 三、操作消息
    # ============================================================
    
    action_message = st.session_state.pop(
        "document_version_action_message",
        None,
    )
    
    if action_message:
        st.success(action_message)
    
    
    # ============================================================
    # 四、版本统计
    # ============================================================
    
    if not saved_documents:
        st.info("当前项目还没有导入需求文档。")
        return
    
    
    document_groups = {}
    
    for document in saved_documents:
        key = document["document_key"]
    
        if key not in document_groups:
            document_groups[key] = []
    
        document_groups[key].append(document)
    
    
    total_document_count = len(document_groups)
    total_history_versions = len(saved_documents)
    
    total_active_versions = sum(
        1
        for doc in saved_documents
        if not doc["is_deleted"]
    )
    
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">版本概览</div>
        <div class="gt-section-desc">
            当前项目需求文档及版本记录统计。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
    
        col1, col2, col3 = st.columns(3)
    
        col1.metric("需求文档数量", total_document_count)
        col2.metric("有效版本数量", total_active_versions)
        col3.metric("历史版本总数", total_history_versions)
    
    
    # ============================================================
    # 五、搜索与筛选
    # ============================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">三、搜索与筛选</div>
        <div class="gt-section-desc">
            根据文档名称、文档标识和版本状态快速定位记录。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
    
        col1, col2 = st.columns([2, 1])
    
        with col1:
            search_keyword = st.text_input(
                "搜索文档名称或标识",
                placeholder="输入文档名称或 document_key",
                key="version_search_keyword",
            )
    
        with col2:
            document_status_filter = st.selectbox(
                "版本显示范围",
                options=["有效版本", "全部版本"],
                key="version_status_filter",
            )
    
    
    # ============================================================
    # 六、整理展示数据
    # ============================================================
    
    filtered_groups = []
    
    for key, all_versions in document_groups.items():
    
        active_versions = [
            doc for doc in all_versions
            if not doc["is_deleted"]
        ]
    
        latest = (
            active_versions[0]
            if active_versions
            else None
        )
    
        if document_status_filter == "有效版本":
            visible_versions = active_versions
        else:
            visible_versions = all_versions
    
        if not visible_versions:
            continue
    
        display_document = latest if latest else all_versions[0]
    
        keyword = search_keyword.strip().lower()
    
        document_name = display_document["document_name"].lower()
    
        if (
            not keyword
            or keyword in document_name
            or keyword in key.lower()
        ):
            filtered_groups.append(
                (
                    key,
                    visible_versions,
                    all_versions,
                    latest,
                    display_document,
                )
            )
    
    
    st.caption(
        f"当前项目共 {total_document_count} 份需求文档，"
        f"有效版本 {total_active_versions} 条，"
        f"历史版本总数 {total_history_versions} 条。"
    )
    
    
    # ============================================================
    # 七、展示每份文档的版本历史
    # ============================================================
    
    st.markdown("""
    <div class="gt-section">
        <div class="gt-section-title">四、文档版本历史</div>
        <div class="gt-section-desc">
            展开文档分组，可以查看版本记录、管理版本状态和查看文档内容。
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if not filtered_groups:
        st.warning("没有找到符合条件的需求文档。")
    
    else:
    
        for (
            key,
            versions,
            all_versions,
            latest,
            display_document,
        ) in filtered_groups:
    
            latest_label = (
                f"最新有效版本 V{latest['version']}"
                if latest
                else "暂无有效版本"
            )
    
            with st.expander(
                f"{display_document['document_name']}（{latest_label}）",
                key=f"version_expander_{key}",
            ):
    
                # ====================================================
                # 文档基本信息
                # ====================================================
    
                st.markdown("""
                <div class="gt-version-header">
                    <div class="gt-version-title">文档基本信息</div>
                    <div class="gt-version-desc">
                        当前文档的版本概况和基础属性。
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
                col1, col2, col3, col4 = st.columns(4)
    
                col1.metric(
                    "最新有效版本",
                    f"V{latest['version']}" if latest else "无",
                )
    
                col2.metric(
                    "有效版本数",
                    len([
                        doc for doc in all_versions
                        if not doc["is_deleted"]
                    ]),
                )
    
                col3.metric(
                    "历史版本总数",
                    len(all_versions),
                )
    
                col4.metric(
                    "文件类型",
                    display_document["file_type"].upper(),
                )
    
                with st.container(border=True):
    
                    st.write(f"**文档名称：** {display_document['document_name']}")
                    st.write(f"**文档标识：** `{key}`")
                    st.write(f"**文档 ID：** `{display_document['id']}`")
    
                    st.write(
                        f"**创建时间：** "
                        f"{format_local_datetime(display_document.get('created_at'))}"
                    )
    
    
                # ====================================================
                # 历史版本选择
                # ====================================================
    
                st.markdown("**历史版本列表**")
    
                version_options = {
                    (
                        f"V{doc['version']}（"
                        f"{format_local_datetime(doc.get('created_at'))}）"
                        + (" [已删除]" if doc["is_deleted"] else "")
                    ): doc["id"]
                    for doc in versions
                }
    
                selected_version_label = st.selectbox(
                    "选择要管理的文档版本",
                    options=list(version_options.keys()),
                    key=f"manage_version_{key}",
                )
    
                selected_version_id = version_options[
                    selected_version_label
                ]
    
                selected_version_record = next(
                    doc for doc in versions
                    if doc["id"] == selected_version_id
                )
    
                st.divider()
    
    
                # ====================================================
                # 版本操作
                # ====================================================
    
                st.markdown("**版本状态与操作**")
    
                with st.container(border=True):
    
                    if not selected_version_record["is_deleted"]:
    
                        st.success(
                            f"当前选择：V{selected_version_record['version']} · 有效版本"
                        )
    
                        confirm_delete = st.checkbox(
                            f"确认逻辑删除 V{selected_version_record['version']}？",
                            key=f"confirm_version_delete_{selected_version_id}",
                        )
    
                        if st.button(
                            "删除所选版本",
                            key=f"delete_version_{selected_version_id}",
                            type="secondary",
                            disabled=not confirm_delete,
                        ):
                            try:
                                deleted = soft_delete_document(
                                    selected_version_id
                                )
    
                                if deleted:
                                    st.session_state[
                                        "document_version_action_message"
                                    ] = (
                                        f"V{selected_version_record['version']} "
                                        "已成功逻辑删除。"
                                    )
                                    st.rerun()
                                else:
                                    st.warning(
                                        "删除未生效，该版本可能已经被删除。"
                                    )
    
                            except Exception as e:
                                st.error(f"删除文档版本失败：{e}")
    
                    else:
    
                        st.warning(
                            f"当前选择：V{selected_version_record['version']} · 已逻辑删除"
                        )
    
                        if st.button(
                            f"恢复 V{selected_version_record['version']}",
                            key=f"restore_version_{selected_version_id}",
                            type="primary",
                        ):
                            try:
                                restored = restore_document(
                                    selected_version_id
                                )
    
                                if restored:
                                    st.session_state[
                                        "document_version_action_message"
                                    ] = (
                                        f"V{selected_version_record['version']} "
                                        "已成功恢复。"
                                    )
                                    st.rerun()
                                else:
                                    st.warning(
                                        "恢复未生效，该版本可能已经恢复。"
                                    )
    
                            except Exception as e:
                                st.error(f"恢复文档版本失败：{e}")
    
    
                # ====================================================
                # 查看版本内容
                # ====================================================
    
                st.markdown("**版本内容查看**")
    
                with st.container(border=True):
    
                    st.caption(
                        "选择版本后，可以读取该版本保存的完整需求文档内容。"
                    )
    
                    if st.button(
                        "查看该版本内容",
                        key=f"view_version_{selected_version_id}",
                    ):
                        try:
                            selected_document = get_document(
                                selected_version_id
                            )
    
                            if selected_document is None:
                                st.error("未找到该文档版本。")
                            else:
                                st.session_state[
                                    f"viewed_version_{key}"
                                ] = selected_document
    
                        except Exception as e:
                            st.error(f"读取文档版本失败：{e}")
    
                    viewed_document = st.session_state.get(
                        f"viewed_version_{key}"
                    )
    
                    if (
                        viewed_document is not None
                        and viewed_document["id"] == selected_version_id
                    ):
                        st.divider()
    
                        st.markdown(
                            f"#### 当前查看版本：V{viewed_document['version']}"
                        )
    
                        col1, col2 = st.columns(2)
    
                        col1.metric(
                            "文件类型",
                            viewed_document["file_type"].upper(),
                        )
    
                        col2.metric(
                            "字符数量",
                            viewed_document["char_count"],
                        )
    
                        st.text_area(
                            "需求文档完整内容",
                            value=viewed_document["parsed_content"] or "",
                            height=350,
                            disabled=True,
                            key=f"version_content_{selected_version_id}",
                        )
    
    
    st.divider()
    st.caption("GameTest AI · 需求版本管理")
    