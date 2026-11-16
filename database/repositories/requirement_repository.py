
import json
import uuid

from database.connection import get_connection


def create_requirement_analysis(
    project_id: str,
    document_id: str,
    module: str,
    summary: str,
    analysis_data: dict,
) -> dict:
    """
    创建一条独立的结构化需求分析记录。

    规则：
    1. 项目必须存在且处于 active 状态。
    2. 文档必须属于该项目且未被逻辑删除。
    3. 每次分析创建新的记录，不覆盖旧记录。
    4. analysis_data 使用 JSON 保存。
    """

    module = module.strip()
    summary = summary.strip()

    if not isinstance(analysis_data, dict):
        raise TypeError("analysis_data 必须是 dict 类型")

    analysis_json = json.dumps(
        analysis_data,
        ensure_ascii=False
    )

    analysis_id = str(uuid.uuid4())

    with get_connection(write=True) as conn:

        # 检查项目是否存在且未归档
        project = conn.execute(
            """
            SELECT id, status
            FROM projects
            WHERE id = ?
            """,
            (project_id,)
        ).fetchone()

        if project is None:
            raise ValueError("所属游戏项目不存在")

        if project["status"] != "active":
            raise ValueError("已归档项目不能创建新的需求分析")

        # 检查文档是否属于当前项目且未删除
        document = conn.execute(
            """
            SELECT id, project_id, is_deleted
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()

        if document is None:
            raise ValueError("策划文档不存在")

        if document["project_id"] != project_id:
            raise ValueError("策划文档不属于当前游戏项目")

        if document["is_deleted"]:
            raise ValueError("已删除的策划文档不能创建新的需求分析")

        conn.execute(
            """
            INSERT INTO requirement_analyses (
                id,
                project_id,
                document_id,
                module,
                summary,
                analysis_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                project_id,
                document_id,
                module,
                summary,
                analysis_json,
            )
        )

        row = conn.execute(
            """
            SELECT *
            FROM requirement_analyses
            WHERE id = ?
            """,
            (analysis_id,)
        ).fetchone()

    result = dict(row)
    result["analysis_data"] = json.loads(result["analysis_json"])

    return result


def get_requirement_analysis(
    analysis_id: str
) -> dict | None:
    """
    根据 ID 查询需求分析记录。
    返回解析后的 JSON 数据。
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM requirement_analyses
            WHERE id = ?
            """,
            (analysis_id,)
        ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["analysis_data"] = json.loads(result["analysis_json"])

    return result


def list_requirement_analyses(
    project_id: str,
    document_id: str | None = None,
) -> list[dict]:
    """
    查询项目下的需求分析历史。

    可选按策划文档 ID 筛选。
    默认按创建时间倒序排列。
    """

    sql = """
        SELECT *
        FROM requirement_analyses
        WHERE project_id = ?
    """

    params = [project_id]

    if document_id is not None:
        sql += " AND document_id = ?"
        params.append(document_id)

    sql += " ORDER BY created_at DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    results = []

    for row in rows:
        item = dict(row)
        item["analysis_data"] = json.loads(item["analysis_json"])
        results.append(item)

    return results
