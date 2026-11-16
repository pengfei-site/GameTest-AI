
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from database import init_db as init_db_module
from database.repositories import (
    test_case_generation_batch_point_repository as repository,
)


class TestCaseGenerationBatchPointRepository(unittest.TestCase):

    @contextmanager
    def _open_sqlite_connection(self, db_path):
        """打开 SQLite 连接，并确保退出时关闭连接。"""
        conn = sqlite3.connect(
            db_path,
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

        self.batch_id = "batch-1"

        self.test_point = {
            "id": "test-point-1",
            "point_id": "TP-001",
            "current_content": {
                "title": "有效账号登录",
                "description": "验证有效账号可以正常登录",
                "priority": "P0",
            },
        }

    def tearDown(self):
        # 先恢复 Repository 原有的数据库连接方法。
        if hasattr(self, "connection_patcher"):
            self.connection_patcher.stop()

        # 再清理临时数据库目录。
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    def _create_test_database(self):
        """创建 Repository 测试所需的隔离数据库。"""
        with self._open_sqlite_connection(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE test_case_generation_batches (
                    id TEXT PRIMARY KEY
                );

                CREATE TABLE test_case_generation_batch_points (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    test_point_id TEXT NOT NULL,
                    point_id TEXT NOT NULL,
                    point_content_json TEXT NOT NULL,
                    collection_validation_report_json TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(batch_id, test_point_id),
                    UNIQUE(batch_id, id)
                );

                INSERT INTO test_case_generation_batches (id)
                VALUES ('batch-1');
                """
            )

    @contextmanager
    def _get_test_connection(self, *, write=False):
        """提供临时数据库连接，模拟项目数据库连接接口。"""
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

    def _create_batch_point(self):
        """创建一条测试点快照。"""
        results = repository.create_batch_points(
            batch_id=self.batch_id,
            test_points=[self.test_point],
        )

        self.assertEqual(len(results), 1)
        return results[0]

    def test_create_batch_point_report_should_be_none(self):
        """创建快照后，集合级 Validator 报告初始值应为 None。"""
        result = self._create_batch_point()

        self.assertEqual(result["batch_id"], self.batch_id)
        self.assertEqual(
            result["test_point_id"],
            self.test_point["id"],
        )
        self.assertEqual(
            result["point_id"],
            self.test_point["point_id"],
        )
        self.assertEqual(
            result["point_content"],
            self.test_point["current_content"],
        )
        self.assertIsNone(
            result["collection_validation_report"]
        )

        stored = repository.get_batch_point_by_id(result["id"])

        self.assertIsNotNone(stored)
        self.assertIsNone(
            stored["collection_validation_report"]
        )

    def test_update_collection_validation_report(self):
        """集合级 Validator 报告应成功写入数据库。"""
        batch_point = self._create_batch_point()

        report = {
            "passed": True,
            "error_count": 0,
            "warning_count": 1,
            "issues": [
                {
                    "level": "warning",
                    "message": "发现一条需要关注的测试用例",
                }
            ],
            "summary": "集合级校验通过",
        }

        result = repository.update_batch_point_collection_validation(
            batch_point_id=batch_point["id"],
            report=report,
        )

        self.assertEqual(
            result["collection_validation_report"],
            report,
        )

        with self._get_test_connection() as conn:
            row = conn.execute(
                """
                SELECT collection_validation_report_json
                FROM test_case_generation_batch_points
                WHERE id = ?
                """,
                (batch_point["id"],),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(
            json.loads(row["collection_validation_report_json"]),
            report,
        )

    def test_collection_validation_report_can_be_read_again(self):
        """保存报告后，通过单条查询和列表查询均能完整读取。"""
        batch_point = self._create_batch_point()

        report = {
            "passed": False,
            "error_count": 1,
            "warning_count": 2,
            "summary": "集合级校验需要复核",
            "details": {
                "reason": "候选用例存在重复内容",
                "language": "中文",
            },
        }

        repository.update_batch_point_collection_validation(
            batch_point_id=batch_point["id"],
            report=report,
        )

        single_result = repository.get_batch_point_by_id(
            batch_point["id"]
        )

        self.assertIsNotNone(single_result)
        self.assertEqual(
            single_result["collection_validation_report"],
            report,
        )

        list_results = repository.list_batch_points(
            self.batch_id
        )

        self.assertEqual(len(list_results), 1)
        self.assertEqual(
            list_results[0]["collection_validation_report"],
            report,
        )

    def test_update_nonexistent_batch_point_should_raise(self):
        """更新不存在的测试点快照时，应抛出 ValueError。"""
        report = {
            "passed": True,
            "error_count": 0,
            "warning_count": 0,
        }

        with self.assertRaises(ValueError):
            repository.update_batch_point_collection_validation(
                batch_point_id="not-exists",
                report=report,
            )

    def test_init_db_should_migrate_old_database(self):
        """
        旧数据库缺少集合级报告字段时：
        1. init_db 应自动新增字段；
        2. 原有快照数据应保留；
        3. 新字段初始值应为 None。
        """
        old_db_path = (
            Path(self.temp_dir.name) / "old_database.db"
        )

        with self._open_sqlite_connection(old_db_path) as conn:
            # 模拟尚未升级的旧版数据库表结构。
            conn.executescript(
                """
                CREATE TABLE test_case_generation_batch_points (
                    id TEXT PRIMARY KEY,
                    batch_id TEXT NOT NULL,
                    test_point_id TEXT NOT NULL,
                    point_id TEXT NOT NULL,
                    point_content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(batch_id, test_point_id),
                    UNIQUE(batch_id, id)
                );

                INSERT INTO test_case_generation_batch_points (
                    id,
                    batch_id,
                    test_point_id,
                    point_id,
                    point_content_json
                )
                VALUES (
                    'old-point-1',
                    'old-batch-1',
                    'old-test-point-1',
                    'TP-OLD-001',
                    '{"title": "历史测试点", "priority": "P1"}'
                );
                """
            )

        @contextmanager
        def old_database_connection(*, write=False):
            conn = sqlite3.connect(
                old_db_path,
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

        with patch.object(
            init_db_module,
            "get_connection",
            old_database_connection,
        ):
            init_db_module.init_db()

        with self._open_sqlite_connection(old_db_path) as conn:
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

            self.assertIn(
                "collection_validation_report_json",
                columns,
            )

            row = conn.execute(
                """
                SELECT *
                FROM test_case_generation_batch_points
                WHERE id = ?
                """,
                ("old-point-1",),
            ).fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row["batch_id"], "old-batch-1")
            self.assertEqual(
                row["test_point_id"],
                "old-test-point-1",
            )
            self.assertEqual(
                row["point_id"],
                "TP-OLD-001",
            )
            self.assertEqual(
                json.loads(row["point_content_json"]),
                {
                    "title": "历史测试点",
                    "priority": "P1",
                },
            )
            self.assertIsNone(
                row["collection_validation_report_json"]
            )


if __name__ == "__main__":
    unittest.main()
