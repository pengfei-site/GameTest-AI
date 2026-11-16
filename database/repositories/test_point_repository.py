import json
import uuid

from pydantic import BaseModel

from core.schemas import TestPointEditableContent
from database.connection import get_connection


def _to_dict(data):
    """兼容普通字典和 Pydantic 模型。"""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")

    if isinstance(data, dict):
        return data

    raise TypeError("测试点内容必须是 dict 或 Pydantic 模型")


def _serialize(data):
    return json.dumps(data, ensure_ascii=False)


def _parse_test_point(row):
    if row is None:
        return None

    result = dict(row)
    result["original_content"] = json.loads(
        result["original_content"]
    )
    result["current_content"] = json.loads(
        result["current_content"]
    )
    return result


def _parse_history(row):
    if row is None:
        return None

    result = dict(row)

    result["before_data"] = (
        json.loads(result["before_data"])
        if result["before_data"]
        else None
    )

    result["after_data"] = (
        json.loads(result["after_data"])
        if result["after_data"]
        else None
    )

    return result


def _get_ai_review_status(point_id, approved_ids, review_ids):
    """根据 AI Reviewer 的单条测试点分类映射状态。"""
    if point_id in approved_ids:
        return "approved"

    if point_id in review_ids:
        return "needs_review"

    return "not_reviewed"


def create_test_points(
    batch_id: str,
    points: list,
    review_report=None,
) -> list[dict]:
    """
    批量创建测试点。

    original_content 和 current_content 初始内容一致。
    人工审核状态默认为 pending。
    每条测试点创建时同步写入 created 历史。
    """

    if not points:
        raise ValueError("测试点列表不能为空")

    normalized_points = [
        _to_dict(point)
        for point in points
    ]

    point_ids = []

    for point in normalized_points:
        point_id = str(point.get("point_id", "")).strip()

        if not point_id:
            raise ValueError("测试点编号 point_id 不能为空")

        point_ids.append(point_id)

    if len(point_ids) != len(set(point_ids)):
        raise ValueError("同一批次内不能存在重复的测试点编号")

    approved_ids = []
    review_ids = []

    if review_report is not None:
        review_data = _to_dict(review_report)

        approved_ids = review_data.get(
            "approved_point_ids", []
        ) or []

        review_ids = review_data.get(
            "review_point_ids", []
        ) or []

    created_points = []

    with get_connection(write=True) as conn:

        batch = conn.execute(
            """
            SELECT id
            FROM generation_batches
            WHERE id = ?
            """,
            (batch_id,)
        ).fetchone()

        if batch is None:
            raise ValueError("生成批次不存在")

        for point in normalized_points:

            point_id = str(point["point_id"]).strip()
            point_uuid = str(uuid.uuid4())

            content_json = _serialize(point)

            ai_status = _get_ai_review_status(
                point_id,
                approved_ids,
                review_ids,
            )

            conn.execute(
                """
                INSERT INTO test_points (
                    id,
                    batch_id,
                    point_id,
                    original_content,
                    current_content,
                    ai_review_status,
                    manual_review_status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                """,
                (
                    point_uuid,
                    batch_id,
                    point_id,
                    content_json,
                    content_json,
                    ai_status,
                )
            )

            history_id = str(uuid.uuid4())

            conn.execute(
                """
                INSERT INTO test_point_history (
                    id,
                    test_point_id,
                    batch_id,
                    action_type,
                    before_data,
                    after_data,
                    comment
                )
                VALUES (?, ?, ?, 'created', NULL, ?, '')
                """,
                (
                    history_id,
                    point_uuid,
                    batch_id,
                    content_json,
                )
            )

            row = conn.execute(
                """
                SELECT *
                FROM test_points
                WHERE id = ?
                """,
                (point_uuid,)
            ).fetchone()

            created_points.append(
                _parse_test_point(row)
            )

    return created_points


def get_test_point(test_point_id: str) -> dict | None:
    """
    根据内部 UUID 查询测试点。
    包含已逻辑删除的测试点，便于后续恢复。
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

    return _parse_test_point(row)


def list_test_points(
    batch_id: str,
    include_deleted: bool = False,
    manual_review_status: str | None = None,
) -> list[dict]:
    """查询批次测试点，默认隐藏已逻辑删除的数据。"""

    sql = """
        SELECT *
        FROM test_points
        WHERE batch_id = ?
    """

    params = [batch_id]

    if not include_deleted:
        sql += " AND is_deleted = 0"

    if manual_review_status is not None:
        if manual_review_status not in {
            "pending",
            "approved",
            "rejected",
        }:
            raise ValueError("无效的人工审核状态")

        sql += " AND manual_review_status = ?"
        params.append(manual_review_status)

    sql += " ORDER BY point_id ASC"

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [
        _parse_test_point(row)
        for row in rows
    ]


def list_test_point_history(
    test_point_id: str,
) -> list[dict]:
    """查询单条测试点的操作历史，按实际写入顺序返回。"""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_point_history
            WHERE test_point_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (test_point_id,)
        ).fetchall()

    return [
        _parse_history(row)
        for row in rows
    ]


def edit_test_point(
    test_point_id: str,
    current_content,
) -> dict:
    """
    编辑测试点当前内容。

    - 使用 TestPointEditableContent 校验可编辑字段
    - point_id 不允许被人工修改
    - original_content 永远不修改
    - current_content 更新为人工编辑后的内容
    - 人工审核状态恢复为 pending
    - 清空当前审核意见和审核时间
    - 保留 AI 审查状态
    - 保存完整编辑前后快照
    - 同一事务中写入 edited 历史
    """

    raw_content = _to_dict(current_content)

    with get_connection(write=True) as conn:

        row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        if row is None:
            raise ValueError("测试点不存在")

        if row["is_deleted"]:
            raise ValueError("已删除的测试点不能直接编辑，请先恢复")

        # 使用专用模型校验编辑内容。
        # point_id、id 等非编辑字段会被 extra='forbid' 拒绝。
        editable_content = TestPointEditableContent.model_validate(
            raw_content
        )

        new_content = editable_content.model_dump(mode="json")

        # point_id 只能沿用数据库原值，不能由编辑请求修改。
        new_content["point_id"] = row["point_id"]

        content_json = _serialize(new_content)

        # 编辑前完整快照。
        before_data = {
            "point_id": row["point_id"],
            "original_content": json.loads(row["original_content"]),
            "current_content": json.loads(row["current_content"]),
            "ai_review_status": row["ai_review_status"],
            "manual_review_status": row["manual_review_status"],
            "manual_comment": row["manual_comment"],
            "reviewed_at": row["reviewed_at"],
            "is_deleted": row["is_deleted"],
            "deleted_at": row["deleted_at"],
        }

        conn.execute(
            """
            UPDATE test_points
            SET
                current_content = ?,
                manual_review_status = 'pending',
                manual_comment = '',
                reviewed_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                content_json,
                test_point_id,
            )
        )

        updated_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        # 编辑后完整快照。
        after_data = {
            "point_id": updated_row["point_id"],
            "original_content": json.loads(
                updated_row["original_content"]
            ),
            "current_content": json.loads(
                updated_row["current_content"]
            ),
            "ai_review_status": updated_row["ai_review_status"],
            "manual_review_status": updated_row["manual_review_status"],
            "manual_comment": updated_row["manual_comment"],
            "reviewed_at": updated_row["reviewed_at"],
            "is_deleted": updated_row["is_deleted"],
            "deleted_at": updated_row["deleted_at"],
        }

        conn.execute(
            """
            INSERT INTO test_point_history (
                id,
                test_point_id,
                batch_id,
                action_type,
                before_data,
                after_data,
                comment
            )
            VALUES (?, ?, ?, 'edited', ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                test_point_id,
                row["batch_id"],
                _serialize(before_data),
                _serialize(after_data),
                "人工编辑测试点",
            )
        )

        final_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

    return _parse_test_point(final_row)


def _review_test_point(
    test_point_id: str,
    action_type: str,
    comment: str = "",
) -> dict:
    """执行单条测试点审核，并在同一事务中保存操作历史。"""

    if action_type not in {"approved", "rejected"}:
        raise ValueError("不支持的审核操作")

    comment = comment.strip()

    if action_type == "rejected" and not comment:
        raise ValueError("驳回原因不能为空")

    new_status = action_type

    with get_connection(write=True) as conn:
        # 在读取审核状态前获取 SQLite 写锁，避免并发审核同时通过 pending 检查。
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        if row is None:
            raise ValueError("测试点不存在")

        if row["is_deleted"]:
            raise ValueError("已删除的测试点不能审核，请先恢复")

        if row["manual_review_status"] != "pending":
            raise ValueError("只有待审核的测试点才能执行审核操作")

        before_data = {
            "point_id": row["point_id"],
            "current_content": json.loads(row["current_content"]),
            "manual_review_status": row["manual_review_status"],
            "manual_comment": row["manual_comment"],
            "reviewed_at": row["reviewed_at"],
        }

        conn.execute(
            """
            UPDATE test_points
            SET
                manual_review_status = ?,
                manual_comment = ?,
                reviewed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                new_status,
                comment,
                test_point_id,
            )
        )

        updated_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        after_data = {
            "point_id": updated_row["point_id"],
            "current_content": json.loads(
                updated_row["current_content"]
            ),
            "manual_review_status": updated_row["manual_review_status"],
            "manual_comment": updated_row["manual_comment"],
            "reviewed_at": updated_row["reviewed_at"],
        }

        conn.execute(
            """
            INSERT INTO test_point_history (
                id,
                test_point_id,
                batch_id,
                action_type,
                before_data,
                after_data,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                test_point_id,
                row["batch_id"],
                action_type,
                _serialize(before_data),
                _serialize(after_data),
                comment,
            )
        )

        final_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

    return _parse_test_point(final_row)


def approve_test_point(
    test_point_id: str,
    comment: str = "",
) -> dict:
    """审核通过单条测试点。审核意见可以为空。"""

    return _review_test_point(
        test_point_id=test_point_id,
        action_type="approved",
        comment=comment,
    )


def reject_test_point(
    test_point_id: str,
    reason: str,
) -> dict:
    """驳回单条测试点，必须填写驳回原因。"""

    return _review_test_point(
        test_point_id=test_point_id,
        action_type="rejected",
        comment=reason,
    )


def _batch_review_test_points(
    test_point_ids: list[str],
    action_type: str,
    comment: str = "",
) -> list[dict]:
    """批量审核测试点，所有状态更新和历史记录在同一事务中完成。"""

    if action_type not in {"batch_approved", "batch_rejected"}:
        raise ValueError("不支持的批量审核操作")

    if not test_point_ids:
        raise ValueError("请选择至少一条测试点")

    if any(
        not isinstance(point_id, str) or not point_id.strip()
        for point_id in test_point_ids
    ):
        raise ValueError("测试点 ID 不能为空")

    if len(test_point_ids) != len(set(test_point_ids)):
        raise ValueError("测试点 ID 不能重复")

    comment = comment.strip()

    if action_type == "batch_rejected" and not comment:
        raise ValueError("批量驳回原因不能为空")

    new_status = (
        "approved" if action_type == "batch_approved" else "rejected"
    )

    with get_connection(write=True) as conn:
        # 在读取待审核状态前获取 SQLite 写锁，保证整批审核的状态判断一致。
        conn.execute("BEGIN IMMEDIATE")
        placeholders = ",".join("?" for _ in test_point_ids)

        rows = conn.execute(
            f"""
            SELECT *
            FROM test_points
            WHERE id IN ({placeholders})
            """,
            test_point_ids,
        ).fetchall()

        if len(rows) != len(test_point_ids):
            raise ValueError("存在不存在的测试点，批量审核已取消")

        row_map = {row["id"]: row for row in rows}
        ordered_rows = [row_map[point_id] for point_id in test_point_ids]

        batch_ids = {row["batch_id"] for row in ordered_rows}

        if len(batch_ids) != 1:
            raise ValueError("批量审核的测试点必须属于同一个生成批次")

        for row in ordered_rows:
            if row["is_deleted"]:
                raise ValueError(
                    f"测试点 {row['point_id']} 已删除，不能参与批量审核"
                )

            if row["manual_review_status"] != "pending":
                raise ValueError(
                    f"测试点 {row['point_id']} 不是待审核状态，不能参与批量审核"
                )

        results = []

        for row in ordered_rows:
            test_point_id = row["id"]

            before_data = {
                "point_id": row["point_id"],
                "current_content": json.loads(row["current_content"]),
                "manual_review_status": row["manual_review_status"],
                "manual_comment": row["manual_comment"],
                "reviewed_at": row["reviewed_at"],
            }

            conn.execute(
                """
                UPDATE test_points
                SET
                    manual_review_status = ?,
                    manual_comment = ?,
                    reviewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_status, comment, test_point_id),
            )

            updated_row = conn.execute(
                """
                SELECT *
                FROM test_points
                WHERE id = ?
                """,
                (test_point_id,),
            ).fetchone()

            after_data = {
                "point_id": updated_row["point_id"],
                "current_content": json.loads(
                    updated_row["current_content"]
                ),
                "manual_review_status": updated_row["manual_review_status"],
                "manual_comment": updated_row["manual_comment"],
                "reviewed_at": updated_row["reviewed_at"],
            }

            conn.execute(
                """
                INSERT INTO test_point_history (
                    id,
                    test_point_id,
                    batch_id,
                    action_type,
                    before_data,
                    after_data,
                    comment
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    test_point_id,
                    row["batch_id"],
                    action_type,
                    _serialize(before_data),
                    _serialize(after_data),
                    comment,
                ),
            )

            final_row = conn.execute(
                """
                SELECT *
                FROM test_points
                WHERE id = ?
                """,
                (test_point_id,),
            ).fetchone()

            results.append(_parse_test_point(final_row))

    return results


def batch_approve_test_points(
    test_point_ids: list[str],
    comment: str = "",
) -> list[dict]:
    """批量审核通过，仅允许待审核测试点参与。"""

    return _batch_review_test_points(
        test_point_ids=test_point_ids,
        action_type="batch_approved",
        comment=comment,
    )


def batch_reject_test_points(
    test_point_ids: list[str],
    reason: str,
) -> list[dict]:
    """批量驳回测试点，必须填写驳回原因。"""

    return _batch_review_test_points(
        test_point_ids=test_point_ids,
        action_type="batch_rejected",
        comment=reason,
    )


def soft_delete_test_point(test_point_id: str) -> dict:
    """逻辑删除测试点，保留内容和审核状态，并记录操作历史。"""

    with get_connection(write=True) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        if row is None:
            raise ValueError("测试点不存在")

        if row["is_deleted"]:
            raise ValueError("测试点已经删除，无需重复删除")

        before_data = {
            "point_id": row["point_id"],
            "current_content": json.loads(row["current_content"]),
            "manual_review_status": row["manual_review_status"],
            "manual_comment": row["manual_comment"],
            "reviewed_at": row["reviewed_at"],
            "is_deleted": row["is_deleted"],
            "deleted_at": row["deleted_at"],
        }

        conn.execute(
            """
            UPDATE test_points
            SET
                is_deleted = 1,
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (test_point_id,)
        )

        updated_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        after_data = {
            "point_id": updated_row["point_id"],
            "current_content": json.loads(updated_row["current_content"]),
            "manual_review_status": updated_row["manual_review_status"],
            "manual_comment": updated_row["manual_comment"],
            "reviewed_at": updated_row["reviewed_at"],
            "is_deleted": updated_row["is_deleted"],
            "deleted_at": updated_row["deleted_at"],
        }

        conn.execute(
            """
            INSERT INTO test_point_history (
                id,
                test_point_id,
                batch_id,
                action_type,
                before_data,
                after_data,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                test_point_id,
                row["batch_id"],
                "deleted",
                _serialize(before_data),
                _serialize(after_data),
                "逻辑删除测试点",
            )
        )

        final_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

    return _parse_test_point(final_row)


def restore_test_point(test_point_id: str) -> dict:
    """恢复已逻辑删除的测试点，保留原内容和审核状态。"""

    with get_connection(write=True) as conn:
        row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        if row is None:
            raise ValueError("测试点不存在")

        if not row["is_deleted"]:
            raise ValueError("测试点尚未删除，无需恢复")

        before_data = {
            "point_id": row["point_id"],
            "current_content": json.loads(row["current_content"]),
            "manual_review_status": row["manual_review_status"],
            "manual_comment": row["manual_comment"],
            "reviewed_at": row["reviewed_at"],
            "is_deleted": row["is_deleted"],
            "deleted_at": row["deleted_at"],
        }

        conn.execute(
            """
            UPDATE test_points
            SET
                is_deleted = 0,
                deleted_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (test_point_id,)
        )

        updated_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

        after_data = {
            "point_id": updated_row["point_id"],
            "current_content": json.loads(updated_row["current_content"]),
            "manual_review_status": updated_row["manual_review_status"],
            "manual_comment": updated_row["manual_comment"],
            "reviewed_at": updated_row["reviewed_at"],
            "is_deleted": updated_row["is_deleted"],
            "deleted_at": updated_row["deleted_at"],
        }

        conn.execute(
            """
            INSERT INTO test_point_history (
                id,
                test_point_id,
                batch_id,
                action_type,
                before_data,
                after_data,
                comment
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                test_point_id,
                row["batch_id"],
                "restored",
                _serialize(before_data),
                _serialize(after_data),
                "恢复已删除的测试点",
            )
        )

        final_row = conn.execute(
            """
            SELECT *
            FROM test_points
            WHERE id = ?
            """,
            (test_point_id,)
        ).fetchone()

    return _parse_test_point(final_row)


def get_test_point_review_statistics(batch_id: str) -> dict:
    """
    统计批次测试点数量。

    total：未删除测试点总数。
    pending / approved / rejected：人工审核状态数量。
    other：其他人工审核状态数量。
    deleted：已逻辑删除测试点数量。
    """

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(CASE WHEN is_deleted = 0 THEN 1 END) AS total,

                COUNT(
                    CASE
                        WHEN is_deleted = 0
                         AND manual_review_status = 'pending'
                        THEN 1
                    END
                ) AS pending,

                COUNT(
                    CASE
                        WHEN is_deleted = 0
                         AND manual_review_status = 'approved'
                        THEN 1
                    END
                ) AS approved,

                COUNT(
                    CASE
                        WHEN is_deleted = 0
                         AND manual_review_status = 'rejected'
                        THEN 1
                    END
                ) AS rejected,

                COUNT(
                    CASE
                        WHEN is_deleted = 0
                         AND (
                            manual_review_status IS NULL
                            OR manual_review_status NOT IN (
                                'pending',
                                'approved',
                                'rejected'
                            )
                         )
                        THEN 1
                    END
                ) AS other,

                COUNT(CASE WHEN is_deleted = 1 THEN 1 END) AS deleted

            FROM test_points
            WHERE batch_id = ?
            """,
            (batch_id,)
        ).fetchone()

    return {
        "total": row["total"] or 0,
        "pending": row["pending"] or 0,
        "approved": row["approved"] or 0,
        "rejected": row["rejected"] or 0,
        "other": row["other"] or 0,
        "deleted": row["deleted"] or 0,
    }


def list_batch_test_point_history(batch_id: str) -> list[dict]:
    """查询整个生成批次的所有测试点操作历史，按实际写入顺序返回。"""

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM test_point_history
            WHERE batch_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (batch_id,)
        ).fetchall()

    return [
        _parse_history(row)
        for row in rows
    ]
