
from database.connection import get_connection


def init_db():
    """
    初始化 GameTest AI SQLite 数据库。

    创建：
    1. 六张核心数据表
    2. 八张 MVP-1 测试用例生成及管理数据表
    3. 全部必要查询索引

    重复执行不会覆盖已有业务数据。
    """

    tables = [

        # ============================================================
        # 一、原有六张核心数据表
        # ============================================================

        # 1. 游戏项目管理
        """
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'archived')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            archived_at TEXT
        )
        """,

        # 2. 策划文档及版本管理
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            document_key TEXT NOT NULL,
            document_name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            file_path TEXT,
            parsed_content TEXT DEFAULT '',
            file_hash TEXT,
            page_count INTEGER,
            char_count INTEGER DEFAULT 0,
            is_deleted INTEGER NOT NULL DEFAULT 0
                CHECK (is_deleted IN (0, 1)),
            is_effective INTEGER NOT NULL DEFAULT 0
                CHECK (is_effective IN (0, 1)),
            deleted_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE RESTRICT,

            UNIQUE (project_id, document_key, version)
        )
        """,

        # 3. 结构化需求分析记录
        """
        CREATE TABLE IF NOT EXISTS requirement_analyses (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT '',
            summary TEXT DEFAULT '',
            analysis_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
                ON DELETE RESTRICT
        )
        """,

        # 4. AI 测试点生成批次
        """
        CREATE TABLE IF NOT EXISTS generation_batches (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            requirement_analysis_id TEXT NOT NULL,
            validation_report_json TEXT,
            review_report_json TEXT,
            final_status TEXT NOT NULL
                CHECK (
                    final_status IN (
                        'ready_for_manual_review',
                        'needs_manual_review',
                        'review_failed',
                        'validation_failed'
                    )
                ),
            generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (requirement_analysis_id)
                REFERENCES requirement_analyses(id)
                ON DELETE RESTRICT
        )
        """,

        # 5. 测试点
        """
        CREATE TABLE IF NOT EXISTS test_points (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            point_id TEXT NOT NULL,
            original_content TEXT NOT NULL,
            current_content TEXT NOT NULL,

            ai_review_status TEXT NOT NULL DEFAULT 'not_reviewed'
                CHECK (
                    ai_review_status IN (
                        'not_reviewed',
                        'approved',
                        'needs_review'
                    )
                ),

            manual_review_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (
                    manual_review_status IN (
                        'pending',
                        'approved',
                        'rejected'
                    )
                ),

            manual_comment TEXT DEFAULT '',
            reviewed_at TEXT,

            is_deleted INTEGER NOT NULL DEFAULT 0
                CHECK (is_deleted IN (0, 1)),

            deleted_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (batch_id)
                REFERENCES generation_batches(id)
                ON DELETE RESTRICT,

            UNIQUE (batch_id, point_id)
        )
        """,

        # 6. 测试点操作历史
        """
        CREATE TABLE IF NOT EXISTS test_point_history (
            id TEXT PRIMARY KEY,
            test_point_id TEXT NOT NULL,
            batch_id TEXT NOT NULL,

            action_type TEXT NOT NULL
                CHECK (
                    action_type IN (
                        'created',
                        'edited',
                        'approved',
                        'rejected',
                        'deleted',
                        'restored',
                        'batch_approved',
                        'batch_rejected'
                    )
                ),

            before_data TEXT,
            after_data TEXT,
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (test_point_id)
                REFERENCES test_points(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (batch_id)
                REFERENCES generation_batches(id)
                ON DELETE RESTRICT
        )
        """,

        # ============================================================
        # 二、MVP-1 测试用例生成及管理数据表
        # ============================================================

        # 7. 测试用例生成批次
        """
        CREATE TABLE IF NOT EXISTS test_case_generation_batches (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            requirement_analysis_id TEXT NOT NULL,
            module TEXT NOT NULL DEFAULT '',

            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (
                    status IN (
                        'pending',
                        'running',
                        'completed',
                        'failed'
                    )
                ),

            generation_config_json TEXT,

            total_points INTEGER NOT NULL DEFAULT 0
                CHECK (total_points >= 0),

            total_candidates INTEGER NOT NULL DEFAULT 0
                CHECK (total_candidates >= 0),

            error_message TEXT DEFAULT '',
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (project_id)
                REFERENCES projects(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (requirement_analysis_id)
                REFERENCES requirement_analyses(id)
                ON DELETE RESTRICT
        )
        """,

        # 8. 测试用例生成批次选点
        """
        CREATE TABLE IF NOT EXISTS test_case_generation_batch_points (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            test_point_id TEXT NOT NULL,
            point_id TEXT NOT NULL,
            point_content_json TEXT NOT NULL,
            collection_validation_report_json TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (batch_id)
                REFERENCES test_case_generation_batches(id)
                ON DELETE RESTRICT,

            FOREIGN KEY (test_point_id)
                REFERENCES test_points(id)
                ON DELETE RESTRICT,

            UNIQUE (batch_id, test_point_id),
            UNIQUE (batch_id, id)
        )
        """,

        # 9. AI 候选测试用例
        """
        CREATE TABLE IF NOT EXISTS test_case_candidates (
            id TEXT PRIMARY KEY,
            batch_id TEXT NOT NULL,
            batch_point_id TEXT NOT NULL,

            candidate_no INTEGER NOT NULL
                CHECK (candidate_no >= 1),

            current_content_json TEXT NOT NULL,

            current_version INTEGER NOT NULL DEFAULT 1
                CHECK (current_version >= 1),

            manual_review_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (
                    manual_review_status IN (
                        'pending',
                        'approved',
                        'rejected'
                    )
                ),

            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (batch_id, batch_point_id)
                REFERENCES test_case_generation_batch_points(
                    batch_id,
                    id
                )
                ON DELETE RESTRICT,

            UNIQUE (batch_id, batch_point_id, candidate_no),
            UNIQUE (id, batch_id)
        )
        """,

        # 10. 候选测试用例版本
        """
        CREATE TABLE IF NOT EXISTS test_case_candidate_versions (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,

            version_no INTEGER NOT NULL
                CHECK (version_no >= 1),

            content_json TEXT NOT NULL,

            change_type TEXT NOT NULL
                CHECK (
                    change_type IN (
                        'ai_generated',
                        'manual_edit'
                    )
                ),

            change_note TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (candidate_id)
                REFERENCES test_case_candidates(id)
                ON DELETE RESTRICT,

            UNIQUE (candidate_id, version_no),
            UNIQUE (candidate_id, id)
        )
        """,

        # 11. Python 自动校验记录
        """
        CREATE TABLE IF NOT EXISTS test_case_validation_records (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            candidate_version_id TEXT NOT NULL,

            passed INTEGER NOT NULL
                CHECK (passed IN (0, 1)),

            error_count INTEGER NOT NULL DEFAULT 0
                CHECK (error_count >= 0),

            warning_count INTEGER NOT NULL DEFAULT 0
                CHECK (warning_count >= 0),

            report_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (candidate_id, candidate_version_id)
                REFERENCES test_case_candidate_versions(
                    candidate_id,
                    id
                )
                ON DELETE RESTRICT
        )
        """,

        # 12. AI Reviewer 审查记录
        """
        CREATE TABLE IF NOT EXISTS test_case_reviewer_records (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            candidate_version_id TEXT NOT NULL,

            overall_status TEXT NOT NULL
                CHECK (
                    overall_status IN (
                        'passed',
                        'needs_review',
                        'failed'
                    )
                ),

            summary TEXT DEFAULT '',
            report_json TEXT NOT NULL,
            model_name TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (candidate_id, candidate_version_id)
                REFERENCES test_case_candidate_versions(
                    candidate_id,
                    id
                )
                ON DELETE RESTRICT
        )
        """,

        # 13. 人工审核记录
        """
        CREATE TABLE IF NOT EXISTS test_case_manual_reviews (
            id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            candidate_version_id TEXT NOT NULL,

            action_type TEXT NOT NULL
                CHECK (
                    action_type IN (
                        'approved',
                        'rejected',
                        'modified'
                    )
                ),

            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (candidate_id, candidate_version_id)
                REFERENCES test_case_candidate_versions(
                    candidate_id,
                    id
                )
                ON DELETE RESTRICT,

            CHECK (
                action_type != 'rejected'
                OR length(trim(comment)) > 0
            )
        )
        """,

        # 14. AI Reviewer 人工确认记录
        """
        CREATE TABLE IF NOT EXISTS test_case_reviewer_confirmations (
            id TEXT PRIMARY KEY,

            reviewer_record_id TEXT NOT NULL,
            candidate_id TEXT NOT NULL,
            candidate_version_id TEXT NOT NULL,

            confirmation_status TEXT NOT NULL
                CHECK (
                    confirmation_status IN (
                        'confirmed_passed',
                        'confirmed_issues',
                        'recheck_required'
                    )
                ),

            confirmation_comment TEXT NOT NULL DEFAULT '',
            confirmed_by TEXT NOT NULL,

            confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (candidate_id, candidate_version_id)
                REFERENCES test_case_candidate_versions(
                    candidate_id,
                    id
                )
                ON DELETE RESTRICT,

            FOREIGN KEY (
                candidate_id,
                candidate_version_id,
                reviewer_record_id
            )
                REFERENCES test_case_reviewer_records(
                    candidate_id,
                    candidate_version_id,
                    id
                )
                ON DELETE RESTRICT
        )
        """,
    ]

    # ============================================================
    # 三、数据库索引
    # ============================================================

    indexes = [

        # 原有六张表的索引

        """
        CREATE INDEX IF NOT EXISTS idx_documents_project
        ON documents(project_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_requirement_analyses_project
        ON requirement_analyses(project_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_requirement_analyses_document
        ON requirement_analyses(document_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_batches_project
        ON generation_batches(project_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_batches_requirement
        ON generation_batches(requirement_analysis_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_test_points_batch
        ON test_points(batch_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_test_points_review_status
        ON test_points(batch_id, manual_review_status)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_test_point_history_point
        ON test_point_history(test_point_id, created_at)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_test_point_history_batch
        ON test_point_history(batch_id, created_at)
        """,

        # MVP-1 原有索引

        """
        CREATE INDEX IF NOT EXISTS idx_tc_batches_project
        ON test_case_generation_batches(project_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_batches_analysis
        ON test_case_generation_batches(requirement_analysis_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_batches_status
        ON test_case_generation_batches(status)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_batch_points_batch
        ON test_case_generation_batch_points(batch_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_batch_points_test_point
        ON test_case_generation_batch_points(test_point_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_candidates_batch
        ON test_case_candidates(batch_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_candidates_review
        ON test_case_candidates(manual_review_status)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_versions_candidate
        ON test_case_candidate_versions(candidate_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_validation_candidate
        ON test_case_validation_records(candidate_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_reviewer_candidate
        ON test_case_reviewer_records(candidate_id)
        """,

        """
        CREATE INDEX IF NOT EXISTS idx_tc_manual_candidate
        ON test_case_manual_reviews(candidate_id)
        """,

        # Reviewer 复合唯一索引
        # 为人工确认表的三列复合外键提供合法父键

        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_tc_reviewer_candidate_version_id
        ON test_case_reviewer_records(
            candidate_id,
            candidate_version_id,
            id
        )
        """,

        # Reviewer 人工确认记录索引

        """
        CREATE INDEX IF NOT EXISTS
        idx_tc_reviewer_confirmations_record
        ON test_case_reviewer_confirmations(
            reviewer_record_id,
            created_at
        )
        """,

        """
        CREATE INDEX IF NOT EXISTS
        idx_tc_reviewer_confirmations_version
        ON test_case_reviewer_confirmations(
            candidate_id,
            candidate_version_id,
            created_at
        )
        """,
    ]

    # ============================================================
    # 四、执行数据库初始化
    # ============================================================

    with get_connection() as conn:

        # 创建全部十四张数据表
        for sql in tables:
            conn.execute(sql)

        # 兼容已有数据库：检查集合级 Validator 报告字段
        columns = {
            row["name"]
            for row in conn.execute(
                """
                PRAGMA table_info(
                    test_case_generation_batch_points
                )
                """
            ).fetchall()
        }

        if "collection_validation_report_json" not in columns:
            conn.execute(
                """
                ALTER TABLE test_case_generation_batch_points
                ADD COLUMN collection_validation_report_json TEXT
                """
            )

        # 兼容已有数据库：增加需求版本有效状态字段。
        document_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        if "is_effective" not in document_columns:
            conn.execute(
                """
                ALTER TABLE documents
                ADD COLUMN is_effective INTEGER NOT NULL DEFAULT 0
                CHECK (is_effective IN (0, 1))
                """
            )
            # 旧数据沿用原规则：每份需求最新的未删除版本作为初始有效版本。
            conn.execute(
                """
                UPDATE documents
                SET is_effective = 1
                WHERE is_deleted = 0
                  AND version = (
                      SELECT MAX(d2.version)
                      FROM documents d2
                      WHERE d2.project_id = documents.project_id
                        AND d2.document_key = documents.document_key
                        AND d2.is_deleted = 0
                  )
                """
            )

        # 数据库层保证同一需求最多只有一个未删除的有效版本。
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_documents_single_effective_version
            ON documents(project_id, document_key)
            WHERE is_effective = 1 AND is_deleted = 0
            """
        )

        # 创建全部查询索引
        for sql in indexes:
            conn.execute(sql)

        # 删除上一步连接测试创建的临时表
        conn.execute("DROP TABLE IF EXISTS connection_test")

    print("GameTest AI 数据库初始化完成！")
    print("核心数据表：6 张")
    print("MVP-1 新增数据表：8 张")
    print("业务数据表总计：14 张")
    print("数据库索引：初始化完成")


if __name__ == "__main__":
    init_db()
