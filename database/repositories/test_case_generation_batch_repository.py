
import json
import uuid

from database.connection import get_connection


def create_generation_batch(
    project_id: str,
    requirement_analysis_id: str,
    module: str = "",
    generation_config: dict | None = None,
    total_points: int = 0,
) -> dict:
    """创建测试用例生成批次。"""

    if total_points < 0:
        raise ValueError("total_points 不能小于 0")

    batch_id = str(uuid.uuid4())

    config_json = (
        json.dumps(generation_config, ensure_ascii=False)
        if generation_config is not None
        else None
    )

    with get_connection(write=True) as conn:
        conn.execute(
            """
            INSERT INTO test_case_generation_batches (
                id,
                project_id,
                requirement_analysis_id,
                module,
                status,
                generation_config_json,
                total_points,
                started_at
            )
            VALUES (?, ?, ?, ?, 'running', ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                batch_id,
                project_id,
                requirement_analysis_id,
                module,
                config_json,
                total_points,
            ),
        )

        row = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()

    return _row_to_batch(row)


def update_generation_batch(
    batch_id: str,
    status: str | None = None,
    total_candidates: int | None = None,
    error_message: str | None = None,
) -> dict:
    """更新测试用例生成批次状态和统计信息。"""

    allowed_statuses = {
        "pending",
        "running",
        "completed",
        "failed",
    }

    if status is not None and status not in allowed_statuses:
        raise ValueError("无效的批次状态")

    if total_candidates is not None and total_candidates < 0:
        raise ValueError("total_candidates 不能小于 0")

    updates = []
    params = []

    if status is not None:
        updates.append("status = ?")
        params.append(status)

        if status in {"completed", "failed"}:
            updates.append("completed_at = CURRENT_TIMESTAMP")

    if total_candidates is not None:
        updates.append("total_candidates = ?")
        params.append(total_candidates)

    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if not updates:
        raise ValueError("没有需要更新的字段")

    params.append(batch_id)

    with get_connection(write=True) as conn:
        cursor = conn.execute(
            f"""
            UPDATE test_case_generation_batches
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            params,
        )

        if cursor.rowcount == 0:
            raise ValueError("测试用例生成批次不存在")

        row = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()

    return _row_to_batch(row)


def get_generation_batch(batch_id: str) -> dict | None:
    """根据批次 ID 查询批次。"""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()

    return _row_to_batch(row) if row else None


def _row_to_batch(row) -> dict:
    result = dict(row)

    config_json = result.pop("generation_config_json")

    result["generation_config"] = (
        json.loads(config_json)
        if config_json
        else None
    )

    return result
