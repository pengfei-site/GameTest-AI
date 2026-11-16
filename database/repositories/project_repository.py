
import uuid

from database.connection import get_connection


def create_project(name: str, description: str = "") -> dict:
    """
    创建游戏项目。

    返回创建后的项目数据。
    """

    name = name.strip()

    if not name:
        raise ValueError("项目名称不能为空")

    project_id = str(uuid.uuid4())

    with get_connection(write=True) as conn:
        conn.execute(
            """
            INSERT INTO projects (
                id,
                name,
                description
            )
            VALUES (?, ?, ?)
            """,
            (project_id, name, description.strip())
        )

        row = conn.execute(
            """
            SELECT *
            FROM projects
            WHERE id = ?
            """,
            (project_id,)
        ).fetchone()

    return dict(row)


def get_project(project_id: str) -> dict | None:
    """
    根据项目 ID 查询项目。
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM projects
            WHERE id = ?
            """,
            (project_id,)
        ).fetchone()

    return dict(row) if row else None


def list_projects(include_archived: bool = False) -> list[dict]:
    """
    查询项目列表。

    默认只返回未归档项目。
    include_archived=True 时返回全部项目。
    """

    with get_connection() as conn:

        if include_archived:
            rows = conn.execute(
                """
                SELECT *
                FROM projects
                ORDER BY updated_at DESC
                """
            ).fetchall()

        else:
            rows = conn.execute(
                """
                SELECT *
                FROM projects
                WHERE status = 'active'
                ORDER BY updated_at DESC
                """
            ).fetchall()

    return [dict(row) for row in rows]


def update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None
) -> bool:
    """
    修改项目名称或描述。

    返回是否成功修改。
    """

    if name is None and description is None:
        raise ValueError("至少需要提供一个待修改字段")

    updates = []
    values = []

    if name is not None:

        name = name.strip()

        if not name:
            raise ValueError("项目名称不能为空")

        updates.append("name = ?")
        values.append(name)

    if description is not None:
        updates.append("description = ?")
        values.append(description.strip())

    updates.append("updated_at = CURRENT_TIMESTAMP")

    values.append(project_id)

    sql = f"""
        UPDATE projects
        SET {", ".join(updates)}
        WHERE id = ?
    """

    with get_connection(write=True) as conn:
        cursor = conn.execute(sql, values)

    return cursor.rowcount > 0


def archive_project(project_id: str) -> bool:
    """
    归档项目。

    归档后保留项目及关联历史数据。
    """

    with get_connection(write=True) as conn:
        cursor = conn.execute(
            """
            UPDATE projects
            SET
                status = 'archived',
                archived_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'active'
            """,
            (project_id,)
        )

    return cursor.rowcount > 0


def restore_project(project_id: str) -> bool:
    """
    恢复已归档项目。
    """

    with get_connection(write=True) as conn:
        cursor = conn.execute(
            """
            UPDATE projects
            SET
                status = 'active',
                archived_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'archived'
            """,
            (project_id,)
        )

    return cursor.rowcount > 0
