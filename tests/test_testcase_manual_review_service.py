
import sqlite3
import tempfile
import unittest

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from core.case_schemas import TestCaseCandidate, TestCaseStep
from core import testcase_manual_review_service as service


class TestCaseManualReviewService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        self._init_database()

        self.connection_patcher = patch.object(
            service,
            "get_connection",
            side_effect=self._get_connection,
        )
        self.connection_patcher.start()

        self.candidate_id = self._create_candidate()

    def tearDown(self):
        self.connection_patcher.stop()
        self.temp_dir.cleanup()

    # ---------------------------------------------------------
    # 隔离数据库
    # ---------------------------------------------------------

    def _get_connection(self, write=False):

        @contextmanager
        def connection_context():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")

            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

        return connection_context()

    def _init_database(self):

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")

        conn.executescript(
            """
            CREATE TABLE test_case_generation_batch_points (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                UNIQUE (batch_id, id)
            );

            CREATE TABLE test_case_candidates (
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
                        batch_id, id
                    ),

                UNIQUE (batch_id, batch_point_id, candidate_no),
                UNIQUE (id, batch_id)
            );

            CREATE TABLE test_case_candidate_versions (
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
                    REFERENCES test_case_candidates(id),

                UNIQUE (candidate_id, version_no),
                UNIQUE (candidate_id, id)
            );

            CREATE TABLE test_case_manual_reviews (
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
                        candidate_id, id
                    ),

                CHECK (
                    action_type != 'rejected'
                    OR length(trim(comment)) > 0
                )
            );

            CREATE TABLE test_case_validation_records (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                candidate_version_id TEXT NOT NULL,
                passed INTEGER NOT NULL CHECK (passed IN (0, 1)),
                error_count INTEGER NOT NULL DEFAULT 0,
                warning_count INTEGER NOT NULL DEFAULT 0,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (candidate_id, candidate_version_id)
                    REFERENCES test_case_candidate_versions(
                        candidate_id, id
                    )
            );

            CREATE TABLE test_case_reviewer_records (
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
                        candidate_id, id
                    )
            );
            """
        )

        conn.commit()
        conn.close()

    # ---------------------------------------------------------
    # 测试数据
    # ---------------------------------------------------------

    def _candidate_content(self, title="测试登录功能"):

        return TestCaseCandidate(
            title=title,
            objective="验证用户能够正常登录游戏",
            priority="P0",
            preconditions=["存在有效账号"],
            steps=[
                TestCaseStep(
                    step_no=1,
                    action="使用有效账号和密码发起登录",
                    expected_result="登录成功",
                )
            ],
            postconditions=["用户处于已登录状态"],
        )

    def _create_candidate(self):

        candidate = self._candidate_content()

        import json
        import uuid

        candidate_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        batch_id = "batch-1"
        point_id = "point-1"

        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            INSERT INTO test_case_generation_batch_points (
                id, batch_id
            )
            VALUES (?, ?)
            """,
            (point_id, batch_id),
        )

        conn.execute(
            """
            INSERT INTO test_case_candidates (
                id,
                batch_id,
                batch_point_id,
                candidate_no,
                current_content_json,
                current_version,
                manual_review_status
            )
            VALUES (?, ?, ?, 1, ?, 1, 'pending')
            """,
            (
                candidate_id,
                batch_id,
                point_id,
                json.dumps(
                    candidate.model_dump(mode="json"),
                    ensure_ascii=False,
                ),
            ),
        )

        conn.execute(
            """
            INSERT INTO test_case_candidate_versions (
                id,
                candidate_id,
                version_no,
                content_json,
                change_type
            )
            VALUES (?, ?, 1, ?, 'ai_generated')
            """,
            (
                version_id,
                candidate_id,
                json.dumps(
                    candidate.model_dump(mode="json"),
                    ensure_ascii=False,
                ),
            ),
        )

        conn.commit()
        conn.close()

        self.version_1_id = version_id

        return candidate_id

    def _add_quality_records(
        self,
        passed=True,
        reviewer_status="passed",
        version_id=None,
    ):

        version_id = version_id or self.version_1_id

        conn = sqlite3.connect(self.db_path)

        conn.execute(
            """
            INSERT INTO test_case_validation_records (
                id,
                candidate_id,
                candidate_version_id,
                passed,
                error_count,
                warning_count,
                report_json
            )
            VALUES (?, ?, ?, ?, 0, 0, '{}')
            """,
            (
                "validation-" + version_id,
                self.candidate_id,
                version_id,
                int(passed),
            ),
        )

        conn.execute(
            """
            INSERT INTO test_case_reviewer_records (
                id,
                candidate_id,
                candidate_version_id,
                overall_status,
                summary,
                report_json
            )
            VALUES (?, ?, ?, ?, '', '{}')
            """,
            (
                "reviewer-" + version_id,
                self.candidate_id,
                version_id,
                reviewer_status,
            ),
        )

        conn.commit()
        conn.close()

    def _get_candidate(self):

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            """
            SELECT *
            FROM test_case_candidates
            WHERE id = ?
            """,
            (self.candidate_id,),
        ).fetchone()

        conn.close()

        return dict(row)

    def _count(self, table):

        conn = sqlite3.connect(self.db_path)

        result = conn.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        conn.close()

        return result

    # ---------------------------------------------------------
    # 1. 审核通过
    # ---------------------------------------------------------

    def test_approve_candidate_success(self):
        """质量检查通过后，人工审核成功。"""

        self._add_quality_records()

        result = service.approve_candidate(
            self.candidate_id,
            "审核通过",
        )

        self.assertEqual(
            result["manual_review_status"],
            "approved",
        )

        self.assertEqual(
            self._get_candidate()["manual_review_status"],
            "approved",
        )

        self.assertEqual(self._count("test_case_manual_reviews"), 1)

    def test_approve_without_validation_is_rejected(self):
        """没有 Python 校验记录时不能通过。"""

        with self.assertRaises(ValueError):
            service.approve_candidate(self.candidate_id)

        self.assertEqual(
            self._get_candidate()["manual_review_status"],
            "pending",
        )

        self.assertEqual(self._count("test_case_manual_reviews"), 0)

    def test_approve_when_validation_failed_is_rejected(self):
        """Python 校验未通过时不能审核通过。"""

        self._add_quality_records(passed=False)

        with self.assertRaises(ValueError):
            service.approve_candidate(self.candidate_id)

        self.assertEqual(self._count("test_case_manual_reviews"), 0)

    def test_approve_when_reviewer_not_passed_is_rejected(self):
        """AI Reviewer 未通过时不能审核通过。"""

        self._add_quality_records(
            passed=True,
            reviewer_status="needs_review",
        )

        with self.assertRaises(ValueError):
            service.approve_candidate(self.candidate_id)

        self.assertEqual(self._count("test_case_manual_reviews"), 0)

    # ---------------------------------------------------------
    # 2. 审核驳回
    # ---------------------------------------------------------

    def test_reject_candidate_success(self):
        """驳回成功并保存原因。"""

        result = service.reject_candidate(
            self.candidate_id,
            "预期结果描述不够明确",
        )

        self.assertEqual(
            result["manual_review_status"],
            "rejected",
        )

        self.assertEqual(
            self._get_candidate()["manual_review_status"],
            "rejected",
        )

        self.assertEqual(self._count("test_case_manual_reviews"), 1)

        conn = sqlite3.connect(self.db_path)

        row = conn.execute(
            """
            SELECT action_type, comment
            FROM test_case_manual_reviews
            """
        ).fetchone()

        conn.close()

        self.assertEqual(row[0], "rejected")
        self.assertEqual(row[1], "预期结果描述不够明确")

    def test_reject_without_reason_is_rejected(self):
        """空白驳回原因被拦截。"""

        with self.assertRaises(ValueError):
            service.reject_candidate(self.candidate_id, "  ")

        self.assertEqual(
            self._get_candidate()["manual_review_status"],
            "pending",
        )

        self.assertEqual(self._count("test_case_manual_reviews"), 0)

    # ---------------------------------------------------------
    # 3. 人工修改
    # ---------------------------------------------------------

    def test_modify_candidate_creates_new_version(self):
        """人工修改创建 V2，V1 保留。"""

        updated = self._candidate_content(
            title="人工修改后的登录测试用例"
        )

        result = service.modify_candidate(
            self.candidate_id,
            updated,
            "补充测试用例标题",
        )

        self.assertEqual(result["new_version_no"], 2)

        self.assertEqual(
            result["old_version_id"],
            self.version_1_id,
        )

        self.assertEqual(
            self._get_candidate()["current_version"],
            2,
        )

        self.assertEqual(
            self._get_candidate()["manual_review_status"],
            "pending",
        )

        self.assertEqual(self._count("test_case_candidate_versions"), 2)

    def test_modify_review_references_old_version(self):
        """modified 审核记录关联旧版本 V1。"""

        updated = self._candidate_content(
            title="修改后的标题"
        )

        service.modify_candidate(
            self.candidate_id,
            updated,
            "人工修改",
        )

        conn = sqlite3.connect(self.db_path)

        row = conn.execute(
            """
            SELECT candidate_version_id, action_type
            FROM test_case_manual_reviews
            """
        ).fetchone()

        conn.close()

        self.assertEqual(row[0], self.version_1_id)
        self.assertEqual(row[1], "modified")

    def test_modify_preserves_old_quality_records(self):
        """修改后旧版本质量记录仍然保留。"""

        self._add_quality_records()

        updated = self._candidate_content(
            title="修改后的标题"
        )

        service.modify_candidate(
            self.candidate_id,
            updated,
        )

        self.assertEqual(
            self._count("test_case_validation_records"),
            1,
        )

        self.assertEqual(
            self._count("test_case_reviewer_records"),
            1,
        )

    def test_modify_rejects_invalid_candidate_type(self):
        """修改内容必须是 TestCaseCandidate。"""

        with self.assertRaises(TypeError):
            service.modify_candidate(
                self.candidate_id,
                {"title": "非法数据"},
            )

        self.assertEqual(self._count("test_case_candidate_versions"), 1)

    # ---------------------------------------------------------
    # 4. 审核状态限制
    # ---------------------------------------------------------

    def test_approved_candidate_cannot_be_approved_again(self):
        """已通过候选不能重复审核通过。"""

        self._add_quality_records()

        service.approve_candidate(self.candidate_id)

        with self.assertRaises(ValueError):
            service.approve_candidate(self.candidate_id)

        self.assertEqual(self._count("test_case_manual_reviews"), 1)

    def test_rejected_candidate_cannot_be_rejected_again(self):
        """已驳回候选不能重复驳回。"""

        service.reject_candidate(
            self.candidate_id,
            "第一次驳回",
        )

        with self.assertRaises(ValueError):
            service.reject_candidate(
                self.candidate_id,
                "第二次驳回",
            )

        self.assertEqual(self._count("test_case_manual_reviews"), 1)

    # ---------------------------------------------------------
    # 5. 事务回滚
    # ---------------------------------------------------------

    def test_modify_transaction_rolls_back_on_failure(self):
        """修改中途失败时，新版本和审核记录全部回滚。"""

        updated = self._candidate_content(
            title="不应保存的修改"
        )

        with patch.object(
            service,
            "_insert_manual_review",
            side_effect=RuntimeError("模拟审核记录写入失败"),
        ):
            with self.assertRaises(RuntimeError):
                service.modify_candidate(
                    self.candidate_id,
                    updated,
                    "模拟失败",
                )

        candidate = self._get_candidate()

        self.assertEqual(candidate["current_version"], 1)
        self.assertEqual(candidate["manual_review_status"], "pending")

        self.assertEqual(self._count("test_case_candidate_versions"), 1)
        self.assertEqual(self._count("test_case_manual_reviews"), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
