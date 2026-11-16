
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from core.case_schemas import TestCaseValidationReport
from core.review_schemas import TestCaseReviewResult
from database.repositories import test_case_quality_repository as repository


class TestCaseQualityRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        self._create_test_database()

        self.connection_patcher = patch.object(
            repository,
            "get_connection",
            self._get_test_connection,
        )
        self.connection_patcher.start()

        self.candidate_id = "candidate-1"
        self.version_id = "version-1"

        self.validation_report = TestCaseValidationReport(
            passed=True,
            total=1,
            error_count=0,
            warning_count=0,
            errors=[],
            warnings=[],
        )

        self.reviewer_report = TestCaseReviewResult(
            overall_status="passed",
            summary="候选用例符合需求和来源测试点。",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[],
        )

    def tearDown(self):
        self.connection_patcher.stop()
        self.temp_dir.cleanup()

    def _create_test_database(self):
        """创建隔离测试数据库及质量记录相关表。"""

        conn = sqlite3.connect(self.db_path)

        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE test_case_candidates (
                id TEXT PRIMARY KEY
            );

            CREATE TABLE test_case_candidate_versions (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                version_no INTEGER NOT NULL,
                UNIQUE(candidate_id, id),
                UNIQUE(candidate_id, version_no),
                FOREIGN KEY(candidate_id)
                    REFERENCES test_case_candidates(id)
            );

            CREATE TABLE test_case_validation_records (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                candidate_version_id TEXT NOT NULL,
                passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
                error_count INTEGER NOT NULL CHECK(error_count >= 0),
                warning_count INTEGER NOT NULL CHECK(warning_count >= 0),
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(candidate_id, candidate_version_id)
                    REFERENCES test_case_candidate_versions(candidate_id, id)
            );

            CREATE TABLE test_case_reviewer_records (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                candidate_version_id TEXT NOT NULL,
                overall_status TEXT NOT NULL,
                summary TEXT NOT NULL,
                report_json TEXT NOT NULL,
                model_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(candidate_id, candidate_version_id)
                    REFERENCES test_case_candidate_versions(candidate_id, id)
            );

            CREATE UNIQUE INDEX idx_tc_reviewer_candidate_version_id
            ON test_case_reviewer_records(
                candidate_id,
                candidate_version_id,
                id
            );

            CREATE TABLE test_case_reviewer_confirmations (
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
                    REFERENCES test_case_candidate_versions(candidate_id, id)
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
            );

            INSERT INTO test_case_candidates (id)
            VALUES ('candidate-1');

            INSERT INTO test_case_candidate_versions (
                id, candidate_id, version_no
            )
            VALUES ('version-1', 'candidate-1', 1);

            INSERT INTO test_case_candidate_versions (
                id, candidate_id, version_no
            )
            VALUES ('version-2', 'candidate-1', 2);
            """
        )

        conn.commit()
        conn.close()

    @contextmanager
    def _get_test_connection(self, *, write=False):
        """提供临时数据库连接。"""

        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
        )
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

    def _create_reviewer_record(
        self,
        candidate_id=None,
        version_id=None,
        report=None,
    ):
        """创建测试用 Reviewer 报告。"""

        return repository.create_reviewer_record(
            candidate_id or self.candidate_id,
            version_id or self.version_id,
            report or self.reviewer_report,
        )

    def _create_confirmation(
        self,
        reviewer_record,
        status="confirmed_passed",
        comment="人工确认通过",
        confirmed_by="tester",
    ):
        """创建测试用人工确认记录。"""

        return repository.create_reviewer_confirmation(
            reviewer_record_id=reviewer_record["id"],
            candidate_id=reviewer_record["candidate_id"],
            candidate_version_id=reviewer_record["candidate_version_id"],
            confirmation_status=status,
            confirmed_by=confirmed_by,
            confirmation_comment=comment,
        )

    # --------------------------------------------------
    # 原有 Python Validation 测试
    # --------------------------------------------------

    def test_create_and_get_validation_record(self):
        """保存并读取 Python 校验报告。"""

        created = repository.create_validation_record(
            self.candidate_id,
            self.version_id,
            self.validation_report,
        )

        self.assertEqual(created["passed"], 1)
        self.assertEqual(created["error_count"], 0)
        self.assertEqual(created["warning_count"], 0)

        self.assertEqual(
            created["report"],
            self.validation_report.model_dump(mode="json"),
        )

        latest = repository.get_latest_validation_record(
            self.candidate_id,
            self.version_id,
        )

        self.assertEqual(latest["id"], created["id"])

    def test_latest_validation_record(self):
        """同一版本存在多条校验记录时返回最新一条。"""

        first = repository.create_validation_record(
            self.candidate_id,
            self.version_id,
            self.validation_report,
        )

        second_report = TestCaseValidationReport(
            passed=False,
            total=1,
            error_count=1,
            warning_count=0,
            errors=["测试标题不能为空"],
            warnings=[],
        )

        second = repository.create_validation_record(
            self.candidate_id,
            self.version_id,
            second_report,
        )

        latest = repository.get_latest_validation_record(
            self.candidate_id,
            self.version_id,
        )

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(latest["id"], second["id"])
        self.assertEqual(latest["passed"], 0)

    def test_version_records_are_independent(self):
        """V1 和 V2 的校验记录相互独立。"""

        repository.create_validation_record(
            self.candidate_id,
            "version-1",
            self.validation_report,
        )

        version_2_report = TestCaseValidationReport(
            passed=False,
            total=1,
            error_count=1,
            warning_count=0,
            errors=["V2 校验错误"],
            warnings=[],
        )

        repository.create_validation_record(
            self.candidate_id,
            "version-2",
            version_2_report,
        )

        v1_record = repository.get_latest_validation_record(
            self.candidate_id,
            "version-1",
        )

        v2_record = repository.get_latest_validation_record(
            self.candidate_id,
            "version-2",
        )

        self.assertEqual(v1_record["passed"], 1)
        self.assertEqual(v2_record["passed"], 0)

    # --------------------------------------------------
    # 原有 AI Reviewer 测试
    # --------------------------------------------------

    def test_create_and_get_reviewer_record(self):
        """保存并读取 AI Reviewer 报告。"""

        created = repository.create_reviewer_record(
            self.candidate_id,
            self.version_id,
            self.reviewer_report,
            model_name="test-model",
        )

        self.assertEqual(created["overall_status"], "passed")
        self.assertEqual(
            created["summary"],
            self.reviewer_report.summary,
        )
        self.assertEqual(created["model_name"], "test-model")

        self.assertEqual(
            created["report"],
            self.reviewer_report.model_dump(mode="json"),
        )

        latest = repository.get_latest_reviewer_record(
            self.candidate_id,
            self.version_id,
        )

        self.assertEqual(latest["id"], created["id"])

    def test_invalid_reviewer_version_is_rejected(self):
        """审查记录不能关联不存在的候选版本。"""

        with self.assertRaises(sqlite3.IntegrityError):
            repository.create_reviewer_record(
                self.candidate_id,
                "not-exists",
                self.reviewer_report,
            )

    def test_list_reviewer_records(self):
        """查询指定版本的全部 Reviewer 历史记录。"""

        first = self._create_reviewer_record()

        second_report = TestCaseReviewResult(
            overall_status="needs_review",
            summary="存在待人工复核问题",
            issues=[],
            approved_candidate_indices=[],
            review_candidate_indices=[1],
        )

        second = self._create_reviewer_record(
            report=second_report,
        )

        records = repository.list_reviewer_records(
            self.candidate_id,
            self.version_id,
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["id"], second["id"])
        self.assertEqual(records[1]["id"], first["id"])

        self.assertEqual(records[0]["overall_status"], "needs_review")
        self.assertEqual(records[1]["overall_status"], "passed")

    def test_list_reviewer_records_are_version_independent(self):
        """V1 和 V2 的 Reviewer 历史记录相互独立。"""

        v1_record = self._create_reviewer_record(
            version_id="version-1",
        )

        v2_report = TestCaseReviewResult(
            overall_status="failed",
            summary="V2 存在严重问题",
            issues=[],
            approved_candidate_indices=[],
            review_candidate_indices=[1],
        )

        v2_record = self._create_reviewer_record(
            version_id="version-2",
            report=v2_report,
        )

        v1_records = repository.list_reviewer_records(
            self.candidate_id,
            "version-1",
        )

        v2_records = repository.list_reviewer_records(
            self.candidate_id,
            "version-2",
        )

        self.assertEqual(len(v1_records), 1)
        self.assertEqual(len(v2_records), 1)

        self.assertEqual(v1_records[0]["id"], v1_record["id"])
        self.assertEqual(v2_records[0]["id"], v2_record["id"])

    def test_nonexistent_records_return_none(self):
        """不存在的质量记录应返回 None。"""

        validation = repository.get_latest_validation_record(
            self.candidate_id,
            "not-exists",
        )

        reviewer = repository.get_latest_reviewer_record(
            self.candidate_id,
            "not-exists",
        )

        self.assertIsNone(validation)
        self.assertIsNone(reviewer)

    def test_list_reviewer_records_when_empty(self):
        """不存在 Reviewer 历史记录时返回空列表。"""

        records = repository.list_reviewer_records(
            self.candidate_id,
            "not-exists",
        )

        self.assertEqual(records, [])

    # --------------------------------------------------
    # 新增：AI Reviewer 人工确认测试
    # --------------------------------------------------

    def test_create_reviewer_confirmation_all_statuses(self):
        """三种人工确认状态均能正常保存。"""

        reviewer_record = self._create_reviewer_record()

        statuses = [
            "confirmed_passed",
            "confirmed_issues",
            "recheck_required",
        ]

        for status in statuses:
            with self.subTest(status=status):
                created = self._create_confirmation(
                    reviewer_record,
                    status=status,
                )

                self.assertEqual(
                    created["confirmation_status"],
                    status,
                )

                self.assertEqual(
                    created["reviewer_record_id"],
                    reviewer_record["id"],
                )

                self.assertEqual(
                    created["candidate_id"],
                    self.candidate_id,
                )

                self.assertEqual(
                    created["candidate_version_id"],
                    self.version_id,
                )

                self.assertEqual(
                    created["confirmed_by"],
                    "tester",
                )

    def test_reviewer_confirmations_are_append_only(self):
        """同一 Reviewer 报告多次确认应追加历史，不覆盖。"""

        reviewer_record = self._create_reviewer_record()

        first = self._create_confirmation(
            reviewer_record,
            status="confirmed_passed",
            comment="第一次确认通过",
        )

        second = self._create_confirmation(
            reviewer_record,
            status="confirmed_issues",
            comment="第二次确认发现问题",
        )

        third = self._create_confirmation(
            reviewer_record,
            status="recheck_required",
            comment="第三次要求重新复核",
        )

        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(second["id"], third["id"])

        records = repository.list_reviewer_confirmations(
            reviewer_record["id"],
        )

        self.assertEqual(len(records), 3)

        self.assertEqual(
            [item["id"] for item in records],
            [third["id"], second["id"], first["id"]],
        )

    def test_get_latest_reviewer_confirmation(self):
        """最新人工确认查询返回最后一次确认。"""

        reviewer_record = self._create_reviewer_record()

        first = self._create_confirmation(
            reviewer_record,
            status="confirmed_passed",
        )

        second = self._create_confirmation(
            reviewer_record,
            status="confirmed_issues",
        )

        latest = repository.get_latest_reviewer_confirmation(
            reviewer_record["id"],
        )

        self.assertEqual(latest["id"], second["id"])
        self.assertNotEqual(latest["id"], first["id"])
        self.assertEqual(
            latest["confirmation_status"],
            "confirmed_issues",
        )

    def test_latest_reviewer_confirmation_when_empty(self):
        """尚未人工确认的 Reviewer 报告返回 None。"""

        reviewer_record = self._create_reviewer_record()

        latest = repository.get_latest_reviewer_confirmation(
            reviewer_record["id"],
        )

        self.assertIsNone(latest)

    def test_list_reviewer_confirmations_when_empty(self):
        """不存在人工确认历史时返回空列表。"""

        records = repository.list_reviewer_confirmations(
            "not-exists",
        )

        self.assertEqual(records, [])

    def test_reviewer_confirmation_version_independence(self):
        """V1 和 V2 的人工确认记录相互独立。"""

        v1_reviewer = self._create_reviewer_record(
            version_id="version-1",
        )

        v2_reviewer = self._create_reviewer_record(
            version_id="version-2",
        )

        v1_confirmation = self._create_confirmation(
            v1_reviewer,
            status="confirmed_passed",
        )

        v2_confirmation = self._create_confirmation(
            v2_reviewer,
            status="confirmed_issues",
        )

        v1_records = repository.list_version_reviewer_confirmations(
            self.candidate_id,
            "version-1",
        )

        v2_records = repository.list_version_reviewer_confirmations(
            self.candidate_id,
            "version-2",
        )

        self.assertEqual(len(v1_records), 1)
        self.assertEqual(len(v2_records), 1)

        self.assertEqual(
            v1_records[0]["id"],
            v1_confirmation["id"],
        )

        self.assertEqual(
            v2_records[0]["id"],
            v2_confirmation["id"],
        )

    def test_reviewer_confirmation_rejects_nonexistent_reviewer(self):
        """不存在的 Reviewer 报告不能创建人工确认。"""

        with self.assertRaises(ValueError):
            repository.create_reviewer_confirmation(
                reviewer_record_id="not-exists",
                candidate_id=self.candidate_id,
                candidate_version_id=self.version_id,
                confirmation_status="confirmed_passed",
                confirmed_by="tester",
            )

    def test_reviewer_confirmation_rejects_version_mismatch(self):
        """Reviewer 报告与候选版本不匹配时拒绝创建。"""

        reviewer_record = self._create_reviewer_record(
            version_id="version-1",
        )

        with self.assertRaises(ValueError):
            repository.create_reviewer_confirmation(
                reviewer_record_id=reviewer_record["id"],
                candidate_id=self.candidate_id,
                candidate_version_id="version-2",
                confirmation_status="confirmed_passed",
                confirmed_by="tester",
            )

    def test_reviewer_confirmation_rejects_invalid_status(self):
        """非法人工确认状态必须被拒绝。"""

        reviewer_record = self._create_reviewer_record()

        with self.assertRaises(ValueError):
            self._create_confirmation(
                reviewer_record,
                status="pending",
            )

    def test_reviewer_confirmation_rejects_empty_required_fields(self):
        """人工确认的必填字段不能为空。"""

        reviewer_record = self._create_reviewer_record()

        with self.assertRaises(ValueError):
            repository.create_reviewer_confirmation(
                reviewer_record_id=reviewer_record["id"],
                candidate_id=self.candidate_id,
                candidate_version_id=self.version_id,
                confirmation_status="confirmed_passed",
                confirmed_by=" ",
            )

    def test_reviewer_confirmation_rejects_non_string_comment(self):
        """人工确认备注必须为字符串。"""

        reviewer_record = self._create_reviewer_record()

        with self.assertRaises(ValueError):
            repository.create_reviewer_confirmation(
                reviewer_record_id=reviewer_record["id"],
                candidate_id=self.candidate_id,
                candidate_version_id=self.version_id,
                confirmation_status="confirmed_passed",
                confirmed_by="tester",
                confirmation_comment=None,
            )

    def test_reviewer_confirmation_foreign_keys(self):
        """人工确认表的外键必须有效。"""

        reviewer_record = self._create_reviewer_record()

        with self.assertRaises(sqlite3.IntegrityError):
            with self._get_test_connection(write=True) as conn:
                conn.execute(
                    """
                    INSERT INTO test_case_reviewer_confirmations (
                        id,
                        reviewer_record_id,
                        candidate_id,
                        candidate_version_id,
                        confirmation_status,
                        confirmed_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "invalid-confirmation",
                        "not-exists",
                        self.candidate_id,
                        self.version_id,
                        "confirmed_passed",
                        "tester",
                    ),
                )

    def test_manual_confirmation_does_not_modify_reviewer_report(self):
        """人工确认不应修改 AI Reviewer 原始报告。"""

        reviewer_record = self._create_reviewer_record()

        original_report = reviewer_record["report"].copy()
        original_status = reviewer_record["overall_status"]

        self._create_confirmation(
            reviewer_record,
            status="confirmed_issues",
            comment="人工认为报告存在问题",
        )

        latest_reviewer = repository.get_latest_reviewer_record(
            self.candidate_id,
            self.version_id,
        )

        self.assertEqual(
            latest_reviewer["overall_status"],
            original_status,
        )

        self.assertEqual(
            latest_reviewer["report"],
            original_report,
        )


if __name__ == "__main__":
    unittest.main()
