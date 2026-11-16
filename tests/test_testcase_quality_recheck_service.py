import json
import sqlite3
import tempfile
import unittest

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from core.case_schemas import (
    TestCaseCandidate,
    TestCaseStep,
    TestCaseValidationReport,
)
from core.review_schemas import TestCaseReviewResult

from core import (
    testcase_manual_review_service as manual_review_service,
)
from core import testcase_quality_recheck_service as recheck_service

from database import init_db
from database.repositories import (
    test_case_candidate_repository as candidate_repo,
    test_case_generation_batch_point_repository as batch_point_repo,
    test_case_generation_batch_repository as batch_repo,
    test_case_quality_repository as quality_repo,
)
from database.repositories import requirement_repository


class TestTestCaseQualityRecheckService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "recheck_test.db"

        self.connection_patches = [
            patch.object(
                init_db,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                candidate_repo,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                batch_point_repo,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                batch_repo,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                quality_repo,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                requirement_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                manual_review_service,
                "get_connection",
                side_effect=self._get_connection,
            ),
        ]

        for patcher in self.connection_patches:
            patcher.start()

        init_db.init_db()
        self._create_test_data()

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
            summary="测试用例符合需求及来源测试点要求。",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[],
        )

        self.candidate = self._build_candidate()

        created = candidate_repo.create_candidate(
            batch_id="case-batch-1",
            batch_point_id="batch-point-1",
            candidate_no=1,
            candidate=self.candidate,
        )

        self.candidate_id = created["id"]

        self.version_1 = candidate_repo.list_candidate_versions(
            self.candidate_id
        )[0]

    def tearDown(self):
        for patcher in reversed(self.connection_patches):
            patcher.stop()

        self.temp_dir.cleanup()

    # =========================================================
    # 数据库连接
    # =========================================================

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

    # =========================================================
    # 测试数据
    # =========================================================

    def _create_test_data(self):
        with self._get_connection() as conn:

            conn.execute(
                """
                INSERT INTO projects (id, name)
                VALUES (?, ?)
                """,
                ("project-1", "复检测试项目"),
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
                    "登录功能需求文档",
                    "txt",
                ),
            )

            conn.execute(
                """
                INSERT INTO requirement_analyses (
                    id,
                    project_id,
                    document_id,
                    module,
                    analysis_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "analysis-1",
                    "project-1",
                    "document-1",
                    "登录模块",
                    json.dumps(
                        {
                            "module": "登录模块",
                            "summary": "验证用户登录功能",
                            "business_rules": [],
                            "preconditions": ["用户拥有有效账号"],
                            "states": [],
                            "numeric_constraints": [],
                            "exception_cases": [],
                            "open_questions": [],
                        },
                        ensure_ascii=False,
                    ),
                ),
            )

            conn.execute(
                """
                INSERT INTO generation_batches (
                    id,
                    project_id,
                    requirement_analysis_id,
                    final_status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    "point-batch-1",
                    "project-1",
                    "analysis-1",
                    "ready_for_manual_review",
                ),
            )

            conn.execute(
                """
                INSERT INTO test_points (
                    id,
                    batch_id,
                    point_id,
                    original_content,
                    current_content
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "test-point-1",
                    "point-batch-1",
                    "TP001",
                    "验证正确账号密码登录成功",
                    "验证正确账号密码登录成功",
                ),
            )

            conn.execute(
                """
                INSERT INTO test_case_generation_batches (
                    id,
                    project_id,
                    requirement_analysis_id,
                    module,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "case-batch-1",
                    "project-1",
                    "analysis-1",
                    "登录模块",
                    "completed",
                ),
            )

            conn.execute(
                """
                INSERT INTO test_case_generation_batch_points (
                    id,
                    batch_id,
                    test_point_id,
                    point_id,
                    point_content_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "batch-point-1",
                    "case-batch-1",
                    "test-point-1",
                    "TP001",
                    json.dumps(
                        {
                            "point_id": "TP001",
                            "requirement_id": "R1",
                            "category": "positive",
                            "title": "正确账号密码登录",
                            "test_objective": "验证登录成功",
                            "coverage_description": "验证有效账号和密码",
                            "priority": "P0",
                            "source_rule": "正确账号密码可以登录",
                        },
                        ensure_ascii=False,
                    ),
                ),
            )

    def _build_candidate(self, title="正确账号密码登录成功"):
        return TestCaseCandidate(
            title=title,
            objective="验证用户能够使用正确账号密码登录游戏",
            priority="P0",
            preconditions=["存在有效账号"],
            steps=[
                TestCaseStep(
                    step_no=1,
                    action="使用有效账号和正确密码发起登录",
                    expected_result="登录成功，进入游戏主界面",
                )
            ],
            postconditions=["用户处于已登录状态"],
        )

    def _mock_reports(self):
        return (
            patch.object(
                recheck_service,
                "validate_testcases",
                return_value=self.validation_report,
            ),
            patch.object(
                recheck_service,
                "review_testcases",
                return_value=self.reviewer_report,
            ),
        )

    def _get_candidate(self):
        return candidate_repo.get_candidate_by_id(
            self.candidate_id
        )

    def _get_quality_counts(self, version_id):
        with self._get_connection() as conn:
            validation_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_validation_records
                WHERE candidate_id = ?
                  AND candidate_version_id = ?
                """,
                (self.candidate_id, version_id),
            ).fetchone()[0]

            reviewer_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_reviewer_records
                WHERE candidate_id = ?
                  AND candidate_version_id = ?
                """,
                (self.candidate_id, version_id),
            ).fetchone()[0]

        return validation_count, reviewer_count

    # =========================================================
    # 测试 1：正常复检
    # =========================================================

    def test_successful_recheck(self):
        original = self._get_candidate()

        validation_patch, reviewer_patch = self._mock_reports()

        with validation_patch, reviewer_patch:
            result = recheck_service.recheck_testcase_quality(
                self.candidate_id
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "completed")
        self.assertEqual(result["version_no"], 1)
        self.assertEqual(
            result["candidate_version_id"],
            self.version_1["id"],
        )
        self.assertTrue(result["validation_saved"])
        self.assertTrue(result["reviewer_saved"])

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (1, 1),
        )

        current = self._get_candidate()

        self.assertEqual(
            current["current_version"],
            original["current_version"],
        )
        self.assertEqual(
            current["manual_review_status"],
            original["manual_review_status"],
        )
        self.assertEqual(
            current["current_content"],
            original["current_content"],
        )

    # =========================================================
    # 测试 2：人工修改后复检 V2
    # =========================================================

    def test_recheck_after_manual_edit_uses_v2(self):
        updated_candidate = self._build_candidate(
            title="使用有效账号登录并验证主界面展示"
        )

        modification = manual_review_service.modify_candidate(
            self.candidate_id,
            updated_candidate,
            "修改测试用例标题",
        )

        version_2_id = modification["new_version_id"]

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (0, 0),
        )

        validation_patch, reviewer_patch = self._mock_reports()

        with validation_patch, reviewer_patch:
            result = recheck_service.recheck_testcase_quality(
                self.candidate_id
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["version_no"], 2)
        self.assertEqual(
            result["candidate_version_id"],
            version_2_id,
        )

        self.assertEqual(
            self._get_quality_counts(version_2_id),
            (1, 1),
        )

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (0, 0),
        )

    # =========================================================
    # 测试 3：Validator 未通过仍然保存检查报告
    # =========================================================

    def test_validation_failed_report_is_still_saved(self):
        failed_report = TestCaseValidationReport(
            passed=False,
            total=1,
            error_count=1,
            warning_count=0,
            errors=["测试标题不符合要求"],
            warnings=[],
        )

        validation_patch = patch.object(
            recheck_service,
            "validate_testcases",
            return_value=failed_report,
        )

        reviewer_patch = patch.object(
            recheck_service,
            "review_testcases",
            return_value=self.reviewer_report,
        )

        with validation_patch, reviewer_patch:
            result = recheck_service.recheck_testcase_quality(
                self.candidate_id
            )

        self.assertTrue(result["success"])
        self.assertFalse(result["validation_report"]["passed"])
        self.assertTrue(result["validation_saved"])
        self.assertTrue(result["reviewer_saved"])

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (1, 1),
        )

    # =========================================================
    # 测试 4：Reviewer 执行异常，不保存任何报告
    # =========================================================

    def test_reviewer_exception_does_not_save_records(self):
        validation_patch = patch.object(
            recheck_service,
            "validate_testcases",
            return_value=self.validation_report,
        )

        reviewer_patch = patch.object(
            recheck_service,
            "review_testcases",
            side_effect=RuntimeError("AI Reviewer 调用失败"),
        )

        with validation_patch, reviewer_patch:
            with self.assertRaisesRegex(
                RuntimeError,
                "AI Reviewer 调用失败",
            ):
                recheck_service.recheck_testcase_quality(
                    self.candidate_id
                )

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (0, 0),
        )

    # =========================================================
    # 测试 5：候选不存在
    # =========================================================

    def test_candidate_not_found(self):
        with self.assertRaisesRegex(
            ValueError,
            "候选不存在",
        ):
            recheck_service.recheck_testcase_quality(
                "not-exists"
            )

    # =========================================================
    # 测试 6：候选正文与当前版本正文不一致
    # =========================================================

    def test_candidate_content_mismatch(self):
        with self._get_connection(write=True) as conn:
            conn.execute(
                """
                UPDATE test_case_candidates
                SET current_content_json = ?
                WHERE id = ?
                """,
                (
                    json.dumps(
                        {
                            **self.version_1["content"],
                            "title": "不一致的标题",
                        },
                        ensure_ascii=False,
                    ),
                    self.candidate_id,
                ),
            )

        validation_patch, reviewer_patch = self._mock_reports()

        with validation_patch, reviewer_patch:
            with self.assertRaisesRegex(
                ValueError,
                "当前正文与当前版本正文不一致",
            ):
                recheck_service.recheck_testcase_quality(
                    self.candidate_id
                )

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (0, 0),
        )

    # =========================================================
    # 测试 7：Reviewer 报告保存失败，明确返回部分保存
    # =========================================================

    def test_reviewer_persistence_failure_returns_partial_result(self):
        validation_patch = patch.object(
            recheck_service,
            "validate_testcases",
            return_value=self.validation_report,
        )

        reviewer_patch = patch.object(
            recheck_service,
            "review_testcases",
            return_value=self.reviewer_report,
        )

        save_patch = patch.object(
            recheck_service.quality_repo,
            "create_reviewer_record",
            side_effect=RuntimeError("Reviewer 保存失败"),
        )

        with validation_patch, reviewer_patch, save_patch:
            result = recheck_service.recheck_testcase_quality(
                self.candidate_id
            )

        self.assertFalse(result["success"])
        self.assertEqual(
            result["stage"],
            "reviewer_persistence",
        )
        self.assertTrue(result["validation_saved"])
        self.assertFalse(result["reviewer_saved"])

        self.assertEqual(
            self._get_quality_counts(self.version_1["id"]),
            (1, 0),
        )

    # =========================================================
    # 测试 8：人工审核状态不被复检修改
    # =========================================================

    def test_recheck_does_not_change_manual_review_status(self):
        original = self._get_candidate()

        validation_patch, reviewer_patch = self._mock_reports()

        with validation_patch, reviewer_patch:
            recheck_service.recheck_testcase_quality(
                self.candidate_id
            )

        current = self._get_candidate()

        self.assertEqual(
            current["manual_review_status"],
            original["manual_review_status"],
        )

        self.assertEqual(
            current["current_version"],
            original["current_version"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
