
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

    def test_create_and_get_reviewer_record(self):
        """保存并读取 AI Reviewer 报告。"""

        created = repository.create_reviewer_record(
            self.candidate_id,
            self.version_id,
            self.reviewer_report,
            model_name="test-model",
        )

        self.assertEqual(
            created["overall_status"],
            "passed",
        )
        self.assertEqual(
            created["summary"],
            self.reviewer_report.summary,
        )
        self.assertEqual(
            created["model_name"],
            "test-model",
        )
        self.assertEqual(
            created["report"],
            self.reviewer_report.model_dump(mode="json"),
        )

        latest = repository.get_latest_reviewer_record(
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

    def test_invalid_validation_version_is_rejected(self):
        """校验记录不能关联不存在的候选版本。"""

        with self.assertRaises(sqlite3.IntegrityError):
            repository.create_validation_record(
                self.candidate_id,
                "not-exists",
                self.validation_report,
            )

    def test_invalid_reviewer_version_is_rejected(self):
        """审查记录不能关联不存在的候选版本。"""

        with self.assertRaises(sqlite3.IntegrityError):
            repository.create_reviewer_record(
                self.candidate_id,
                "not-exists",
                self.reviewer_report,
            )


if __name__ == "__main__":
    unittest.main()
