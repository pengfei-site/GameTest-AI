
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


def get_homepage_chart_data() -> dict:
    """
    获取首页顶部统计、审核进度及四张图表所需的真实数据。

    统计规则：
    1. 项目总数：active 和 archived 项目。
    2. 需求文档：排除逻辑删除记录，按 project_id + document_key 去重。
    3. 有效测试点：排除逻辑删除记录。
    4. 测试用例：统计候选本体，不统计历史版本。
    5. 审核进度：按项目和实际 manual_review_status 分组。
    6. 工作流：分别统计需求分析记录、测试点生成批次、用例生成批次。
    """

    statistics_sql = """
        SELECT
            (SELECT COUNT(*)
             FROM projects) AS project_count,

            (SELECT COUNT(*)
             FROM (
                 SELECT project_id, document_key
                 FROM documents
                 WHERE is_deleted = 0
                 GROUP BY project_id, document_key
             )) AS document_count,

            (SELECT COUNT(*)
             FROM test_points
             WHERE is_deleted = 0) AS test_point_count,

            (SELECT COUNT(*)
             FROM test_case_candidates) AS test_case_count
    """

    project_status_sql = """
        SELECT
            status,
            COUNT(*) AS count
        FROM projects
        GROUP BY status
        ORDER BY status
    """

    asset_statistics_sql = """
        SELECT '需求文档' AS asset_type,
               COUNT(*) AS count
        FROM (
            SELECT project_id, document_key
            FROM documents
            WHERE is_deleted = 0
            GROUP BY project_id, document_key
        )

        UNION ALL

        SELECT '需求分析',
               COUNT(*)
        FROM requirement_analyses

        UNION ALL

        SELECT '测试点',
               COUNT(*)
        FROM test_points
        WHERE is_deleted = 0

        UNION ALL

        SELECT '测试用例',
               COUNT(*)
        FROM test_case_candidates
    """

    test_point_review_sql = """
        SELECT
            p.id AS project_id,
            p.name AS project_name,
            COALESCE(tp.manual_review_status, 'unknown') AS review_status,
            COUNT(*) AS count
        FROM test_points tp
        JOIN generation_batches gb
            ON tp.batch_id = gb.id
        JOIN projects p
            ON gb.project_id = p.id
        WHERE tp.is_deleted = 0
        GROUP BY
            p.id,
            p.name,
            COALESCE(tp.manual_review_status, 'unknown')
        ORDER BY p.name, review_status
    """

    test_case_review_sql = """
        SELECT
            p.id AS project_id,
            p.name AS project_name,
            COALESCE(tc.manual_review_status, 'unknown') AS review_status,
            COUNT(*) AS count
        FROM test_case_candidates tc
        JOIN test_case_generation_batches cb
            ON tc.batch_id = cb.id
        JOIN projects p
            ON cb.project_id = p.id
        GROUP BY
            p.id,
            p.name,
            COALESCE(tc.manual_review_status, 'unknown')
        ORDER BY p.name, review_status
    """

    workflow_distribution_sql = """
        SELECT
            '需求分析记录' AS workflow_type,
            COUNT(*) AS count
        FROM requirement_analyses

        UNION ALL

        SELECT
            '测试点生成批次',
            COUNT(*)
        FROM generation_batches

        UNION ALL

        SELECT
            '测试用例生成批次',
            COUNT(*)
        FROM test_case_generation_batches
    """

    with get_connection() as conn:
        statistics = dict(
            conn.execute(statistics_sql).fetchone()
        )

        project_status = [
            dict(row)
            for row in conn.execute(project_status_sql).fetchall()
        ]

        asset_statistics = [
            dict(row)
            for row in conn.execute(asset_statistics_sql).fetchall()
        ]

        test_point_review = [
            dict(row)
            for row in conn.execute(test_point_review_sql).fetchall()
        ]

        test_case_review = [
            dict(row)
            for row in conn.execute(test_case_review_sql).fetchall()
        ]

        workflow_distribution = [
            dict(row)
            for row in conn.execute(workflow_distribution_sql).fetchall()
        ]

    return {
        "statistics": statistics,
        "project_status": project_status,
        "asset_statistics": asset_statistics,
        "review_progress": {
            "test_points": test_point_review,
            "test_cases": test_case_review,
        },
        "workflow_distribution": workflow_distribution,
    }

