
import json
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel

from database.connection import get_connection


VALID_FINAL_STATUSES = {
    "ready_for_manual_review",
    "needs_manual_review",
    "review_failed",
    "validation_failed",
}


def _serialize_report(report):
    """将字典或 Pydantic 模型转换为 JSON 字符串。"""
    if report is None:
        return None

    if isinstance(report, BaseModel):
        report = report.model_dump(mode="json")

    if not isinstance(report, dict):
        raise TypeError("报告必须是 dict、Pydantic 模型或 None")

    return json.dumps(report, ensure_ascii=False)


def _parse_batch(row):
    """将数据库记录转换为 Python 字典，并解析 JSON 报告。"""
    if row is None:
        return None

    result = dict(row)

    result["validation_report"] = (
        json.loads(result["validation_report_json"])
        if result["validation_report_json"]
        else None
    )

    result["review_report"] = (
        json.loads(result["review_report_json"])
        if result["review_report_json"]
        else None
    )

    return result


def create_generation_batch(
    project_id: str,
    requirement_analysis_id: str,
    validation_report=None,
    review_report=None,
    final_status: str = "needs_manual_review",
) -> dict:
    """创建一次独立的测试点生成批次。"""

    if final_status not in VALID_FINAL_STATUSES:
        raise ValueError(
            f"不支持的生成状态：{final_status}"
        )

    validation_json = _serialize_report(validation_report)
    review_json = _serialize_report(review_report)

    batch_id = str(uuid.uuid4())

    with get_connection(write=True) as conn:

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
            raise ValueError("已归档项目不能创建新的生成批次")

        analysis = conn.execute(
            """
            SELECT id, project_id
            FROM requirement_analyses
            WHERE id = ?
            """,
            (requirement_analysis_id,)
        ).fetchone()

        if analysis is None:
            raise ValueError("关联的需求分析记录不存在")

        if analysis["project_id"] != project_id:
            raise ValueError("需求分析记录不属于当前游戏项目")

        conn.execute(
            """
            INSERT INTO generation_batches (
                id,
                project_id,
                requirement_analysis_id,
                validation_report_json,
                review_report_json,
                final_status
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                project_id,
                requirement_analysis_id,
                validation_json,
                review_json,
                final_status,
            )
        )

        row = conn.execute(
            """
            SELECT *
            FROM generation_batches
            WHERE id = ?
            """,
            (batch_id,)
        ).fetchone()

    return _parse_batch(row)



def set_generation_batch_effective(batch_id: str) -> dict:
    """将批次设为所属需求版本的唯一有效批次，原有效批次自动废弃。"""

    with get_connection(write=True) as conn:
        # 先获取 SQLite 写锁，避免并发设置时出现多个有效批次。
        conn.execute("BEGIN IMMEDIATE")

        batch = conn.execute(
            """
            SELECT
                gb.id,
                gb.requirement_analysis_id,
                ra.document_id
            FROM generation_batches AS gb
            JOIN requirement_analyses AS ra
                ON ra.id = gb.requirement_analysis_id
            WHERE gb.id = ?
            """,
            (batch_id,),
        ).fetchone()

        if batch is None:
            raise ValueError("生成批次不存在，或关联的需求版本不存在")

        # 同一策划文档版本（document_id）下，先将所有批次设为废弃。
        conn.execute(
            """
            UPDATE generation_batches
            SET batch_status = 'obsolete'
            WHERE requirement_analysis_id IN (
                SELECT id
                FROM requirement_analyses
                WHERE document_id = ?
            )
            """,
            (batch["document_id"],),
        )

        conn.execute(
            """
            UPDATE generation_batches
            SET batch_status = 'effective'
            WHERE id = ?
            """,
            (batch_id,),
        )

        row = conn.execute(
            """
            SELECT *
            FROM generation_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()

    return _parse_batch(row)



def get_generation_batch(batch_id: str) -> dict | None:
    """根据批次 ID 查询单条生成批次。"""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM generation_batches
            WHERE id = ?
            """,
            (batch_id,)
        ).fetchone()

    return _parse_batch(row)


def list_generation_batches(
    project_id: str,
    requirement_analysis_id: str | None = None,
) -> list[dict]:
    """查询项目的生成批次，可按需求分析记录筛选。"""

    sql = """
        SELECT *
        FROM generation_batches
        WHERE project_id = ?
    """

    params = [project_id]

    if requirement_analysis_id is not None:
        sql += " AND requirement_analysis_id = ?"
        params.append(requirement_analysis_id)

    sql += " ORDER BY generated_at DESC, id DESC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        _parse_batch(row)
        for row in rows
    ]
