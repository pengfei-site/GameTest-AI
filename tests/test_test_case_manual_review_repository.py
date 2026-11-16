
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from database.repositories import (
    test_case_manual_review_repository as repository,
)


class TestCaseManualReviewRepository(unittest.TestCase):

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

    def tearDown(self):
        self.connection_patcher.stop()
        self.temp_dir.cleanup()

    def _create_test_database(self):
        """创建隔离测试数据库及必要的数据表。"""

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

            CREATE TABLE test_case_manual_reviews (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                candidate_version_id TEXT NOT NULL,

                action_type TEXT NOT NULL CHECK(
                    action_type IN (
                        'approved',
                        'rejected',
                        'modified'
                    )
                ),

                comment TEXT DEFAULT '',

                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(candidate_id, candidate_version_id)
                    REFERENCES test_case_candidate_versions(
                        candidate_id,
                        id
                    ),

                CHECK(
                    action_type != 'rejected'
                    OR length(trim(comment)) > 0
                )
            );

            INSERT INTO test_case_candidates (id)
            VALUES ('candidate-1');

            INSERT INTO test_case_candidate_versions (
                id,
                candidate_id,
                version_no
            )
            VALUES
                ('version-1', 'candidate-1', 1),
                ('version-2', 'candidate-1', 2);
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

    def test_create_approved_review(self):
        """保存审核通过记录。"""

        result = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "approved",
        )

        self.assertEqual(result["candidate_id"], self.candidate_id)
        self.assertEqual(
            result["candidate_version_id"],
            self.version_id,
        )
        self.assertEqual(result["action_type"], "approved")
        self.assertEqual(result["comment"], "")

    def test_create_rejected_review(self):
        """保存驳回记录及驳回原因。"""

        reason = "测试步骤缺少明确的预期结果"

        result = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "rejected",
            reason,
        )

        self.assertEqual(result["action_type"], "rejected")
        self.assertEqual(result["comment"], reason)

    def test_rejected_review_requires_comment(self):
        """驳回时必须填写非空白原因。"""

        with self.assertRaises(ValueError):
            repository.create_manual_review(
                self.candidate_id,
                self.version_id,
                "rejected",
                "   ",
            )

    def test_create_modified_review(self):
        """保存人工修改记录。"""

        result = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "modified",
            "调整了测试步骤和预期结果",
        )

        self.assertEqual(result["action_type"], "modified")
        self.assertEqual(
            result["comment"],
            "调整了测试步骤和预期结果",
        )

    def test_get_latest_manual_review(self):
        """查询指定版本最新审核记录。"""

        first = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "rejected",
            "第一次审核未通过",
        )

        second = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "approved",
            "修改后审核通过",
        )

        latest = repository.get_latest_manual_review(
            self.candidate_id,
            self.version_id,
        )

        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(latest["id"], second["id"])
        self.assertEqual(latest["action_type"], "approved")

    def test_list_manual_reviews(self):
        """查询候选用例的完整审核历史。"""

        first = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "rejected",
            "第一次审核未通过",
        )

        second = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "modified",
            "人工修改",
        )

        third = repository.create_manual_review(
            self.candidate_id,
            self.version_id,
            "approved",
            "审核通过",
        )

        history = repository.list_manual_reviews(
            self.candidate_id
        )

        self.assertEqual(len(history), 3)

        self.assertEqual(
            [item["id"] for item in history],
            [
                first["id"],
                second["id"],
                third["id"],
            ],
        )

    def test_version_reviews_are_independent(self):
        """不同候选版本的审核记录相互独立。"""

        repository.create_manual_review(
            self.candidate_id,
            "version-1",
            "rejected",
            "V1 未通过",
        )

        repository.create_manual_review(
            self.candidate_id,
            "version-2",
            "approved",
            "V2 通过",
        )

        v1 = repository.get_latest_manual_review(
            self.candidate_id,
            "version-1",
        )

        v2 = repository.get_latest_manual_review(
            self.candidate_id,
            "version-2",
        )

        self.assertEqual(v1["action_type"], "rejected")
        self.assertEqual(v2["action_type"], "approved")

    def test_invalid_version_is_rejected(self):
        """审核记录不能关联不存在的候选版本。"""

        with self.assertRaises(sqlite3.IntegrityError):
            repository.create_manual_review(
                self.candidate_id,
                "not-exists",
                "approved",
            )

    def test_invalid_action_is_rejected(self):
        """不允许使用未定义的审核操作类型。"""

        with self.assertRaises(ValueError):
            repository.create_manual_review(
                self.candidate_id,
                self.version_id,
                "pending",
            )


if __name__ == "__main__":
    unittest.main()
