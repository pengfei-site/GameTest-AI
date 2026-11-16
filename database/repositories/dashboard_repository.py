
from database.connection import get_connection


def get_dashboard_statistics() -> dict:
    """
    获取平台首页统计数据。

    统计规则：
    1. 项目：分别统计 active 和 archived。
    2. 需求文档：按 project_id + document_key 去重。
    3. 文档版本：统计未逻辑删除的版本记录。
    4. 需求分析：统计全部分析记录。
    5. 生成批次：统计全部生成批次。
    6. 测试点：排除已逻辑删除的数据。
    """

    sql = """
        SELECT
            (
                SELECT COUNT(*)
                FROM projects
                WHERE status = 'active'
            ) AS active_project_count,

            (
                SELECT COUNT(*)
                FROM projects
                WHERE status = 'archived'
            ) AS archived_project_count,

            (
                SELECT COUNT(*)
                FROM (
                    SELECT project_id, document_key
                    FROM documents
                    WHERE is_deleted = 0
                    GROUP BY project_id, document_key
                )
            ) AS document_count,

            (
                SELECT COUNT(*)
                FROM documents
                WHERE is_deleted = 0
            ) AS document_version_count,

            (
                SELECT COUNT(*)
                FROM requirement_analyses
            ) AS requirement_analysis_count,

            (
                SELECT COUNT(*)
                FROM generation_batches
            ) AS generation_batch_count,

            (
                SELECT COUNT(*)
                FROM test_points
                WHERE is_deleted = 0
            ) AS test_point_count
    """

    with get_connection() as conn:
        row = conn.execute(sql).fetchone()

    return dict(row)
