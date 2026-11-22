import uuid

from database.connection import get_connection



def create_document_version(
    project_id: str,
    document_key: str,
    document_name: str,
    file_type: str,
    file_path: str | None = None,
    parsed_content: str = "",
    file_hash: str | None = None,
    page_count: int | None = None,
    char_count: int | None = None,
    document_id: str | None = None,
) -> dict:
    """
    创建策划文档的新版本。

    同一项目下，相同 document_key 的文档版本号自动递增。
    不覆盖已有版本。
    """

    document_key = document_key.strip()
    document_name = document_name.strip()
    file_type = file_type.strip().lower()

    if not document_key:
        raise ValueError("文档标识 document_key 不能为空")

    if not document_name:
        raise ValueError("文档名称不能为空")

    if not file_type:
        raise ValueError("文件类型不能为空")

    if char_count is None:
        char_count = len(parsed_content)

    document_id = document_id or str(uuid.uuid4())

    with get_connection(write=True) as conn:
        # 确认所属项目存在且处于 active 状态
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
            raise ValueError("已归档项目不能创建新的策划文档版本")

        # 查询同一文档的最大版本号
        row = conn.execute(
            """
            SELECT MAX(version) AS max_version
            FROM documents
            WHERE project_id = ?
              AND document_key = ?
            """,
            (project_id, document_key)
        ).fetchone()

        version = (row["max_version"] or 0) + 1

        # 创建新版本，不修改旧版本
        conn.execute(
            """
            INSERT INTO documents (
                id,
                project_id,
                document_key,
                document_name,
                file_type,
                version,
                file_path,
                parsed_content,
                file_hash,
                page_count,
                char_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                project_id,
                document_key,
                document_name,
                file_type,
                version,
                file_path,
                parsed_content,
                file_hash,
                page_count,
                char_count,
            )
        )

        created = conn.execute(
            """
            SELECT *
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()

    return dict(created)


def get_document(document_id: str) -> dict | None:
    """
    根据文档 ID 查询文档。
    包含已逻辑删除的文档，便于恢复和历史追溯。
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM documents
            WHERE id = ?
            """,
            (document_id,)
        ).fetchone()

    return dict(row) if row else None


def set_active_document_version(document_id: str) -> bool:
    """手动设定文档组的唯一有效版本；原有效版本自动废弃。"""
    with get_connection(write=True) as conn:
        row = conn.execute("SELECT project_id, document_key, is_deleted FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            raise ValueError("需求文档版本不存在")
        if row["is_deleted"]:
            raise ValueError("已删除的版本不能设为有效版本")
        conn.execute("UPDATE documents SET is_active = 0 WHERE project_id = ? AND document_key = ?", (row["project_id"], row["document_key"]))
        conn.execute("UPDATE documents SET is_active = 1 WHERE id = ?", (document_id,))
    return True


def list_documents(
    project_id: str,
    document_key: str | None = None,
    include_deleted: bool = False,
) -> list[dict]:
    """
    查询项目下的策划文档。

    默认隐藏已逻辑删除的文档。
    可以通过 document_key 查询某份文档的所有版本。
    """

    sql = """
        SELECT *
        FROM documents
        WHERE project_id = ?
    """

    params = [project_id]

    if document_key is not None:
        sql += " AND document_key = ?"
        params.append(document_key)

    if not include_deleted:
        sql += " AND is_deleted = 0"

    sql += " ORDER BY document_key, version DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def soft_delete_document(document_id: str) -> bool:
    """
    逻辑删除文档，不物理删除数据库记录。
    """

    with get_connection(write=True) as conn:
        cursor = conn.execute(
            """
            UPDATE documents
            SET
                is_deleted = 1,
                is_active = 0,
                deleted_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND is_deleted = 0
            """,
            (document_id,)
        )

    return cursor.rowcount > 0


def restore_document(document_id: str) -> bool:
    """
    恢复已逻辑删除的文档。
    保留原有版本号和文档内容。
    """

    with get_connection(write=True) as conn:
        cursor = conn.execute(
            """
            UPDATE documents
            SET
                is_deleted = 0,
                deleted_at = NULL
            WHERE id = ?
              AND is_deleted = 1
            """,
            (document_id,)
        )

    return cursor.rowcount > 0
