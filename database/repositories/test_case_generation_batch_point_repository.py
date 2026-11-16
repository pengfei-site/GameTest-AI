
import json
import uuid

from database.connection import get_connection


def create_batch_points(
    batch_id: str,
    test_points: list[dict],
) -> list[dict]:
    """
    批量保存测试用例生成批次的测试点快照。

    快照使用测试点当前内容，不使用 original_content。
    所有快照在同一个事务中保存。
    """

    if not test_points:
        return []

    normalized_points = []

    for point in test_points:
        if not isinstance(point, dict):
            raise TypeError("测试点必须是字典")

        test_point_id = str(point.get("id", "")).strip()
        point_id = str(point.get("point_id", "")).strip()
        current_content = point.get("current_content")

        if not test_point_id:
            raise ValueError("测试点内部 ID 不能为空")

        if not point_id:
            raise ValueError("测试点编号不能为空")

        if not isinstance(current_content, dict):
            raise TypeError("测试点 current_content 必须是字典")

        snapshot_json = json.dumps(
            current_content,
            ensure_ascii=False,
        )

        normalized_points.append({
            "id": str(uuid.uuid4()),
            "batch_id": batch_id,
            "test_point_id": test_point_id,
            "point_id": point_id,
            "point_content_json": snapshot_json,
        })

    test_point_ids = [
        point["test_point_id"]
        for point in normalized_points
    ]

    if len(test_point_ids) != len(set(test_point_ids)):
        raise ValueError("同一批次不能重复关联同一个测试点")

    created_points = []

    with get_connection(write=True) as conn:

        batch = conn.execute(
            """
            SELECT id
            FROM test_case_generation_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()

        if batch is None:
            raise ValueError("测试用例生成批次不存在")

        for point in normalized_points:
            conn.execute(
                """
                INSERT INTO test_case_generation_batch_points (
                    id,
                    batch_id,
                    test_point_id,
                    point_id,
                    point_content_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    point["id"],
                    point["batch_id"],
                    point["test_point_id"],
                    point["point_id"],
                    point["point_content_json"],
                ),
            )

            created_points.append({
                "id": point["id"],
                "batch_id": batch_id,
                "test_point_id": point["test_point_id"],
                "point_id": point["point_id"],
                "point_content": json.loads(
                    point["point_content_json"]
                ),
                "collection_validation_report": None,
            })

    return created_points


def update_batch_point_collection_validation(
    batch_point_id: str,
    report,
) -> dict:
    """
    更新测试点快照的集合级 Validator 报告。

    report 支持：
    1. Pydantic 模型
    2. dict

    保存后返回更新后的测试点快照。
    """

    if not batch_point_id:
        raise ValueError("批次测试点记录 ID 不能为空")

    if hasattr(report, "model_dump"):
        report_data = report.model_dump(mode="json")
    elif isinstance(report, dict):
        report_data = report
    else:
        raise TypeError("Validator 报告必须是 Pydantic 模型或字典")

    report_json = json.dumps(
        report_data,
        ensure_ascii=False,
    )

    with get_connection(write=True) as conn:
        cursor = conn.execute(
            """
            UPDATE test_case_generation_batch_points
            SET collection_validation_report_json = ?
            WHERE id = ?
            """,
            (report_json, batch_point_id),
        )

        if cursor.rowcount == 0:
            raise ValueError("测试用例生成批次测试点快照不存在")

    result = get_batch_point_by_id(batch_point_id)

    if result is None:
        raise RuntimeError("集合级 Validator 报告保存后无法读取快照")

    return result


def list_batch_points(batch_id: str) -> list[dict]:
    """查询指定测试用例生成批次的全部测试点快照。"""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batch_points
            WHERE batch_id = ?
            ORDER BY point_id ASC
            """,
            (batch_id,),
        ).fetchall()

    return [
        _row_to_batch_point(row)
        for row in rows
    ]


def get_batch_point_by_id(
    batch_point_id: str,
) -> dict | None:
    """根据批次测试点记录 ID 查询快照。"""

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_case_generation_batch_points
            WHERE id = ?
            """,
            (batch_point_id,),
        ).fetchone()

    return _row_to_batch_point(row) if row else None


def _row_to_batch_point(row) -> dict:
    """将数据库记录转换为业务字典。"""

    result = dict(row)

    result["point_content"] = json.loads(
        result.pop("point_content_json")
    )

    report_json = result.get(
        "collection_validation_report_json"
    )

    result["collection_validation_report"] = (
        json.loads(report_json)
        if report_json
        else None
    )

    return result
