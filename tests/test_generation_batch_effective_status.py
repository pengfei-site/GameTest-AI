"""测试点生成批次有效状态 Repository 测试。"""

import sqlite3
import tempfile
import unittest

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from database import init_db
from database.repositories import generation_batch_repository as batch_repository


class TestGenerationBatchEffectiveStatus(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "generation_batch_status.db"
        self.connection_patches = [
            patch.object(init_db, "get_connection", side_effect=self._get_connection),
            patch.object(batch_repository, "get_connection", side_effect=self._get_connection),
        ]
        for patcher in self.connection_patches:
            patcher.start()

        init_db.init_db()
        self._create_test_data()

    def tearDown(self):
        for patcher in reversed(self.connection_patches):
            patcher.stop()
        self.temp_dir.cleanup()

    def _get_connection(self, write=False):
        @contextmanager
        def connection_context():
            conn = sqlite3.connect(self.db_path, timeout=30)
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

    def _create_test_data(self):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO projects (id, name) VALUES ('project-1', '项目一')"
            )
            for document_id, document_key in (
                ("document-v1", "DOC-001"),
                ("document-v2", "DOC-002"),
            ):
                conn.execute(
                    """
                    INSERT INTO documents (
                        id, project_id, document_key, document_name, file_type
                    ) VALUES (?, 'project-1', ?, ?, 'txt')
                    """,
                    (document_id, document_key, document_key),
                )
            analyses = [
                ("analysis-v1-a", "document-v1"),
                ("analysis-v1-b", "document-v1"),
                ("analysis-v2", "document-v2"),
            ]
            for analysis_id, document_id in analyses:
                conn.execute(
                    """
                    INSERT INTO requirement_analyses (
                        id, project_id, document_id, module, analysis_json
                    ) VALUES (?, 'project-1', ?, '测试模块', '{}')
                    """,
                    (analysis_id, document_id),
                )

    def _create_batch(self, analysis_id):
        return batch_repository.create_generation_batch(
            project_id="project-1",
            requirement_analysis_id=analysis_id,
        )

    def test_setting_effective_batch_obsoletes_previous_batch_for_same_version(self):
        first = self._create_batch("analysis-v1-a")
        second = self._create_batch("analysis-v1-b")

        batch_repository.set_generation_batch_effective(first["id"])
        batch_repository.set_generation_batch_effective(second["id"])

        first_after = batch_repository.get_generation_batch(first["id"])
        second_after = batch_repository.get_generation_batch(second["id"])

        self.assertEqual(first_after["batch_status"], "obsolete")
        self.assertEqual(second_after["batch_status"], "effective")

    def test_effective_status_is_isolated_between_document_versions(self):
        version_one = self._create_batch("analysis-v1-a")
        version_two = self._create_batch("analysis-v2")

        batch_repository.set_generation_batch_effective(version_one["id"])
        batch_repository.set_generation_batch_effective(version_two["id"])

        self.assertEqual(
            batch_repository.get_generation_batch(version_one["id"])["batch_status"],
            "effective",
        )
        self.assertEqual(
            batch_repository.get_generation_batch(version_two["id"])["batch_status"],
            "effective",
        )

    def test_missing_batch_cannot_be_set_effective(self):
        with self.assertRaises(ValueError):
            batch_repository.set_generation_batch_effective("missing-batch")


if __name__ == "__main__":
    unittest.main(verbosity=2)
