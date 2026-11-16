
import json
import sqlite3
import tempfile
import unittest

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from database import init_db
from database.repositories import (
    test_case_generation_batch_repository as batch_repository,
)


class TestCaseGenerationBatchRepository(unittest.TestCase):
    """测试用例生成批次 Repository 专项测试。"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "batch_test.db"

        self.connection_patches = [
            patch.object(
                init_db,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                batch_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
        ]

        for patcher in self.connection_patches:
            patcher.start()

        init_db.init_db()
        self._create_test_data()

    def tearDown(self):
        for patcher in reversed(self.connection_patches):
            patcher.stop()

        self.temp_dir.cleanup()

    # ==================================================
    # 1. 隔离数据库连接
    # ==================================================

    def _get_connection(self, write=False):

        @contextmanager
        def connection_context():
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

        return connection_context()

    # ==================================================
    # 2. 测试数据
    # ==================================================

    def _create_test_data(self):
        with self._get_connection() as conn:

            projects = [
                ("project-1", "项目一"),
                ("project-2", "项目二"),
            ]

            conn.executemany(
                """
                INSERT INTO projects (id, name)
                VALUES (?, ?)
                """,
                projects,
            )

            conn.execute(
                """
                INSERT INTO documents (
                    id,
                    project_id,
                    document_key,
                    document_name,
                    file_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "document-1",
                    "project-1",
                    "DOC-001",
                    "需求文档一",
                    "txt",
                ),
            )

            conn.execute(
                """
                INSERT INTO documents (
                    id,
                    project_id,
                    document_key,
                    document_name,
                    file_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "document-2",
                    "project-1",
                    "DOC-002",
                    "需求文档二",
                    "txt",
                ),
            )

            conn.execute(
                """
                INSERT INTO documents (
                    id,
                    project_id,
                    document_key,
                    document_name,
                    file_type
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "document-3",
                    "project-2",
                    "DOC-003",
                    "需求文档三",
                    "txt",
                ),
            )

            analyses = [
                (
                    "analysis-1",
                    "project-1",
                    "document-1",
                    "登录模块",
                    "登录需求分析",
                    "{}",
                ),
                (
                    "analysis-2",
                    "project-1",
                    "document-2",
                    "战斗模块",
                    "战斗需求分析",
                    "{}",
                ),
                (
                    "analysis-3",
                    "project-2",
                    "document-3",
                    "背包模块",
                    "背包需求分析",
                    "{}",
                ),
            ]

            conn.executemany(
                """
                INSERT INTO requirement_analyses (
                    id,
                    project_id,
                    document_id,
                    module,
                    summary,
                    analysis_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                analyses,
            )

    # ==================================================
    # 3. 创建批次辅助方法
    # ==================================================

    def _create_batch(
        self,
        project_id="project-1",
        analysis_id="analysis-1",
        module="测试模块",
        generation_config=None,
        total_points=1,
        status=None,
    ):
        batch = batch_repository.create_generation_batch(
            project_id=project_id,
            requirement_analysis_id=analysis_id,
            module=module,
            generation_config=generation_config,
            total_points=total_points,
        )

        if status is not None:
            batch = batch_repository.update_generation_batch(
                batch_id=batch["id"],
                status=status,
            )

        return batch

    # ==================================================
    # 4. 查询测试
    # ==================================================

    def test_list_all_batches_by_project(self):
        """T01：查询项目下全部批次。"""

        self._create_batch()
        self._create_batch(analysis_id="analysis-2")
        self._create_batch(
            project_id="project-2",
            analysis_id="analysis-3",
        )

        results = batch_repository.list_generation_batches(
            project_id="project-1",
        )

        self.assertEqual(len(results), 2)

        for item in results:
            self.assertEqual(item["project_id"], "project-1")

    def test_project_isolation(self):
        """T02：不同项目之间的数据隔离。"""

        self._create_batch()
        self._create_batch(
            project_id="project-2",
            analysis_id="analysis-3",
        )

        results = batch_repository.list_generation_batches(
            project_id="project-2",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["project_id"], "project-2")

    def test_filter_by_requirement_analysis(self):
        """T03：按需求分析 ID 筛选。"""

        self._create_batch(analysis_id="analysis-1")
        self._create_batch(analysis_id="analysis-2")

        results = batch_repository.list_generation_batches(
            project_id="project-1",
            requirement_analysis_id="analysis-1",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["requirement_analysis_id"],
            "analysis-1",
        )

    def test_filter_by_status(self):
        """T04：按批次状态筛选。"""

        self._create_batch(status="completed")
        self._create_batch(status="failed")
        self._create_batch(status="running")

        results = batch_repository.list_generation_batches(
            project_id="project-1",
            status="completed",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "completed")

    def test_filter_by_multiple_conditions(self):
        """T05：组合筛选条件。"""

        self._create_batch(
            analysis_id="analysis-1",
            status="completed",
        )

        self._create_batch(
            analysis_id="analysis-1",
            status="failed",
        )

        self._create_batch(
            analysis_id="analysis-2",
            status="completed",
        )

        results = batch_repository.list_generation_batches(
            project_id="project-1",
            requirement_analysis_id="analysis-1",
            status="completed",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "completed")
        self.assertEqual(
            results[0]["requirement_analysis_id"],
            "analysis-1",
        )

    def test_latest_batch_first(self):
        """T06：创建时间相同时，按 rowid 倒序。"""

        first = self._create_batch(module="第一批")
        second = self._create_batch(module="第二批")
        third = self._create_batch(module="第三批")

        results = batch_repository.list_generation_batches(
            project_id="project-1",
        )

        self.assertEqual(len(results), 3)

        self.assertEqual(
            [item["id"] for item in results],
            [
                third["id"],
                second["id"],
                first["id"],
            ],
        )

    def test_no_matching_batches(self):
        """T07：没有匹配批次时返回空列表。"""

        results = batch_repository.list_generation_batches(
            project_id="project-1",
        )

        self.assertEqual(results, [])

    # ==================================================
    # 5. 参数校验
    # ==================================================

    def test_empty_project_id_should_be_rejected(self):
        """T08：空项目 ID 必须被拒绝。"""

        invalid_ids = [
            "",
            " ",
        ]

        for project_id in invalid_ids:
            with self.subTest(project_id=project_id):
                with self.assertRaises(ValueError):
                    batch_repository.list_generation_batches(
                        project_id=project_id,
                    )

    def test_invalid_status_should_be_rejected(self):
        """T09：无效状态必须被拒绝。"""

        with self.assertRaises(ValueError):
            batch_repository.list_generation_batches(
                project_id="project-1",
                status="invalid_status",
            )

    def test_empty_requirement_analysis_id_should_be_rejected(self):
        """T10：显式传入空需求分析 ID 必须被拒绝。"""

        with self.assertRaises(ValueError):
            batch_repository.list_generation_batches(
                project_id="project-1",
                requirement_analysis_id="",
            )

        with self.assertRaises(ValueError):
            batch_repository.list_generation_batches(
                project_id="project-1",
                requirement_analysis_id=" ",
            )

    # ==================================================
    # 6. 返回结构
    # ==================================================

    def test_generation_config_should_be_parsed(self):
        """T11：generation_config 应正确解析。"""

        config = {
            "model": "deepseek-chat",
            "temperature": 0.2,
            "language": "zh-CN",
        }

        created = self._create_batch(
            generation_config=config,
        )

        results = batch_repository.list_generation_batches(
            project_id="project-1",
        )

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0]["generation_config"],
            config,
        )

        self.assertEqual(
            results[0]["id"],
            created["id"],
        )

    def test_batch_fields_should_be_preserved(self):
        """T12：批次原有字段应完整保留。"""

        created = self._create_batch(
            module="登录模块",
            total_points=5,
        )

        batch_repository.update_generation_batch(
            batch_id=created["id"],
            status="completed",
            total_candidates=8,
        )

        results = batch_repository.list_generation_batches(
            project_id="project-1",
        )

        self.assertEqual(len(results), 1)

        batch = results[0]

        self.assertEqual(batch["id"], created["id"])
        self.assertEqual(batch["project_id"], "project-1")
        self.assertEqual(
            batch["requirement_analysis_id"],
            "analysis-1",
        )
        self.assertEqual(batch["module"], "登录模块")
        self.assertEqual(batch["status"], "completed")
        self.assertEqual(batch["total_points"], 5)
        self.assertEqual(batch["total_candidates"], 8)

        self.assertIn("created_at", batch)
        self.assertIn("started_at", batch)
        self.assertIn("completed_at", batch)
        self.assertIn("error_message", batch)
        self.assertIn("generation_config", batch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
