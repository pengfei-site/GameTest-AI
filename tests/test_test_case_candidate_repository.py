
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from core.case_schemas import TestCaseCandidate
from database.repositories import test_case_candidate_repository as repository


class TestCaseCandidateRepository(unittest.TestCase):

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

        self.candidate = TestCaseCandidate(
            title="有效账号登录测试",
            objective="验证有效账号可以成功登录",
            priority="P0",
            preconditions=["存在有效账号"],
            steps=[
                {
                    "step_no": 1,
                    "action": "使用有效账号和正确密码发起登录",
                    "expected_result": "登录成功",
                },
            ],
            postconditions=["账号处于已登录状态"],
        )

    def tearDown(self):
        self.connection_patcher.stop()
        self.temp_dir.cleanup()

    def _create_test_database(self):
        """创建隔离测试数据库及必要的数据表。"""

        conn = sqlite3.connect(self.db_path)

        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE test_case_generation_batch_points (
                id TEXT NOT NULL,
                batch_id TEXT NOT NULL,
                UNIQUE(batch_id, id)
            );

            CREATE TABLE test_case_candidates (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                batch_point_id TEXT NOT NULL,
                candidate_no INTEGER NOT NULL CHECK(candidate_no >= 1),
                current_content_json TEXT NOT NULL,
                current_version INTEGER NOT NULL DEFAULT 1,
                manual_review_status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(batch_id, batch_point_id, candidate_no),
                UNIQUE(id, batch_id),

                FOREIGN KEY(batch_id, batch_point_id)
                    REFERENCES test_case_generation_batch_points(batch_id, id)
            );

            CREATE TABLE test_case_candidate_versions (
                id TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                version_no INTEGER NOT NULL CHECK(version_no >= 1),
                content_json TEXT NOT NULL,
                change_type TEXT NOT NULL,
                change_note TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(candidate_id, version_no),
                UNIQUE(candidate_id, id),

                FOREIGN KEY(candidate_id)
                    REFERENCES test_case_candidates(id)
            );

            INSERT INTO test_case_generation_batch_points (
                id,
                batch_id
            )
            VALUES ('point-1', 'batch-1');
            """
        )

        conn.commit()
        conn.close()

    @contextmanager
    def _get_test_connection(self, *, write=False):
        """提供临时数据库连接，模拟项目连接接口。"""

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

    def test_create_candidate_and_initial_version(self):
        """创建候选时必须同时创建 V1。"""

        result = repository.create_candidate(
            batch_id="batch-1",
            batch_point_id="point-1",
            candidate_no=1,
            candidate=self.candidate,
        )

        self.assertEqual(result["current_version"], 1)
        self.assertEqual(result["manual_review_status"], "pending")
        self.assertEqual(
            result["current_content"],
            self.candidate.model_dump(mode="json"),
        )

        versions = repository.list_candidate_versions(
            result["id"]
        )

        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["version_no"], 1)
        self.assertEqual(versions[0]["change_type"], "ai_generated")

        self.assertEqual(
            versions[0]["content"],
            result["current_content"],
        )

    def test_get_candidate_by_id(self):
        """根据候选 ID 查询。"""

        created = repository.create_candidate(
            "batch-1",
            "point-1",
            1,
            self.candidate,
        )

        result = repository.get_candidate_by_id(
            created["id"]
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], created["id"])
        self.assertEqual(
            result["current_content"],
            self.candidate.model_dump(mode="json"),
        )

    def test_get_nonexistent_candidate(self):
        """查询不存在的候选应返回 None。"""

        result = repository.get_candidate_by_id(
            "not-exists"
        )

        self.assertIsNone(result)

    def test_list_candidates_by_batch(self):
        """按生成批次查询候选。"""

        repository.create_candidate(
            "batch-1",
            "point-1",
            1,
            self.candidate,
        )

        results = repository.list_candidates_by_batch(
            "batch-1"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["candidate_no"], 1)

        empty_results = repository.list_candidates_by_batch(
            "not-exists"
        )

        self.assertEqual(empty_results, [])

    def test_list_candidate_versions(self):
        """查询候选用例版本历史。"""

        created = repository.create_candidate(
            "batch-1",
            "point-1",
            1,
            self.candidate,
        )

        versions = repository.list_candidate_versions(
            created["id"]
        )

        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["version_no"], 1)

    def test_invalid_candidate_no(self):
        """候选序号小于 1 时应拒绝创建。"""

        with self.assertRaises(ValueError):
            repository.create_candidate(
                "batch-1",
                "point-1",
                0,
                self.candidate,
            )

    def test_duplicate_candidate_rolls_back(self):
        """重复候选序号时，不应产生孤立版本记录。"""

        repository.create_candidate(
            "batch-1",
            "point-1",
            1,
            self.candidate,
        )

        with self.assertRaises(sqlite3.IntegrityError):
            repository.create_candidate(
                "batch-1",
                "point-1",
                1,
                self.candidate,
            )

        with self._get_test_connection() as conn:
            candidate_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_candidates
                """
            ).fetchone()[0]

            version_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_candidate_versions
                """
            ).fetchone()[0]

        self.assertEqual(candidate_count, 1)
        self.assertEqual(version_count, 1)


if __name__ == "__main__":
    unittest.main()
