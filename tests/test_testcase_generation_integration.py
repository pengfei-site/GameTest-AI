
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
    TestCaseGenerationResult,
)
from core.review_schemas import TestCaseReviewResult

from database import init_db
from database.repositories import (
    requirement_repository,
    generation_batch_repository,
    test_point_repository,
    test_case_generation_batch_repository,
    test_case_generation_batch_point_repository,
    test_case_candidate_repository,
    test_case_quality_repository,
)

from core import testcase_generation_service as generation_service


class TestCaseGenerationIntegration(unittest.TestCase):
    """
    STEP 10.7.5 测试用例生成业务编排集成测试。

    使用临时 SQLite 数据库和正式数据库初始化逻辑。
    不调用真实 AI，不修改正式业务数据库。
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "generation_test.db"

        self.connection_patches = [
            patch.object(
                init_db,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                requirement_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                generation_batch_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                test_point_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                test_case_generation_batch_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                test_case_generation_batch_point_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                test_case_candidate_repository,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                test_case_quality_repository,
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

    def _build_requirement(self):
        return {
            "module": "登录模块",
            "summary": "验证用户使用账号密码登录游戏。",
            "business_rules": [
                {
                    "rule_id": "R1",
                    "rule_text": "用户可以使用账号和密码登录。",
                    "source_text": "用户使用账号和密码进入游戏。",
                    "status": "confirmed",
                },
                {
                    "rule_id": "R2",
                    "rule_text": "登录成功后进入游戏主界面。",
                    "source_text": "登录成功进入游戏主界面。",
                    "status": "confirmed",
                },
            ],
            "preconditions": [],
            "states": [],
            "numeric_constraints": [],
            "exception_cases": [],
            "open_questions": [],
        }

    def _build_test_point(self):
        return {
            "point_id": "TP001",
            "requirement_id": "R1",
            "category": "positive",
            "title": "正确账号密码登录成功",
            "test_objective": "验证用户能够正常登录游戏。",
            "coverage_description": "使用有效账号和密码登录，检查登录结果。",
            "priority": "P0",
            "source_rule": "用户可以使用账号和密码登录。",
        }

    def _create_test_data(self):
        with self._get_connection() as conn:

            # 项目
            conn.execute(
                """
                INSERT INTO projects (
                    id,
                    name
                )
                VALUES (?, ?)
                """,
                (
                    "project-1",
                    "测试用例生成集成测试项目",
                ),
            )

            # 策划文档
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

            # 需求分析
            conn.execute(
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
                (
                    "analysis-1",
                    "project-1",
                    "document-1",
                    "登录模块",
                    "验证用户登录功能。",
                    json.dumps(
                        self._build_requirement(),
                        ensure_ascii=False,
                    ),
                ),
            )

            # 测试点生成批次
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

            # 已审核通过测试点
            conn.execute(
                """
                INSERT INTO test_points (
                    id,
                    batch_id,
                    point_id,
                    original_content,
                    current_content,
                    manual_review_status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "test-point-1",
                    "point-batch-1",
                    "TP001",
                    json.dumps(
                        self._build_test_point(),
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        self._build_test_point(),
                        ensure_ascii=False,
                    ),
                    "approved",
                ),
            )

            # 待审核测试点：不应被选中
            pending_point = self._build_test_point()
            pending_point["point_id"] = "TP002"
            pending_point["title"] = "待审核测试点"

            conn.execute(
                """
                INSERT INTO test_points (
                    id,
                    batch_id,
                    point_id,
                    original_content,
                    current_content,
                    manual_review_status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "test-point-2",
                    "point-batch-1",
                    "TP002",
                    json.dumps(
                        pending_point,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        pending_point,
                        ensure_ascii=False,
                    ),
                    "pending",
                ),
            )

    # ==================================================
    # 3. Mock AI 数据
    # ==================================================

    def _build_candidate(self, title):
        return TestCaseCandidate(
            title=title,
            objective="验证用户能够使用正确账号密码登录游戏。",
            priority="P0",
            preconditions=[
                "存在有效账号及对应密码。",
            ],
            steps=[
                TestCaseStep(
                    step_no=1,
                    action="使用有效账号及密码发起登录。",
                    expected_result="登录成功，系统进入游戏主界面。",
                )
            ],
            postconditions=[
                "用户处于已登录状态。",
            ],
        )

    def _build_generation_result(self):
        candidates = [
            self._build_candidate(
                "使用正确账号密码登录成功"
            ),
            self._build_candidate(
                "登录成功后进入游戏主界面"
            ),
        ]

        return TestCaseGenerationResult(
            success=True,
            candidate_count=2,
            candidates=candidates,
            error_message="",
        )

    def _build_passed_review(self):
        return TestCaseReviewResult(
            overall_status="passed",
            summary="候选用例符合需求及测试点要求。",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[],
        )

    def _build_needs_review(self):
        return TestCaseReviewResult(
            overall_status="needs_review",
            summary="候选用例需要人工进一步确认。",
            issues=[],
            approved_candidate_indices=[],
            review_candidate_indices=[1],
        )

    # ==================================================
    # 4. 查询辅助方法
    # ==================================================

    def _get_batch(self, batch_id):
        return (
            test_case_generation_batch_repository
            .get_generation_batch(batch_id)
        )

    def _get_candidates(self, batch_id):
        return (
            test_case_candidate_repository
            .list_candidates_by_batch(batch_id)
        )

    def _get_quality_counts(self, candidate_id, version_id):
        with self._get_connection() as conn:

            validation_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_validation_records
                WHERE candidate_id = ?
                  AND candidate_version_id = ?
                """,
                (
                    candidate_id,
                    version_id,
                ),
            ).fetchone()[0]

            reviewer_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_reviewer_records
                WHERE candidate_id = ?
                  AND candidate_version_id = ?
                """,
                (
                    candidate_id,
                    version_id,
                ),
            ).fetchone()[0]

        return validation_count, reviewer_count

    # ==================================================
    # 5. 完整生成链路集成测试
    # ==================================================

    def test_complete_generation_lifecycle(self):
        generation_mock = self._build_generation_result()

        reviewer_results = [
            self._build_passed_review(),
            self._build_needs_review(),
        ]

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ) as generator_mock:

            with patch.object(
                generation_service,
                "review_testcases",
                side_effect=reviewer_results,
            ) as reviewer_mock:

                result = generation_service.run_testcase_generation(
                    project_id="project-1",
                    requirement_analysis_id="analysis-1",
                    test_point_batch_id="point-batch-1",
                )

        # A. 检查批次结果
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")

        self.assertEqual(result["total_points"], 1)
        self.assertEqual(result["successful_points"], 1)
        self.assertEqual(result["failed_points"], 0)
        self.assertEqual(result["total_candidates"], 2)

        batch_id = result["batch_id"]
        batch = self._get_batch(batch_id)

        self.assertIsNotNone(batch)
        self.assertEqual(batch["status"], "completed")
        self.assertEqual(batch["total_candidates"], 2)

        # B. 检查 Generator 和 Reviewer 调用次数
        generator_mock.assert_called_once()
        self.assertEqual(reviewer_mock.call_count, 2)

        # C. 检查测试点快照
        batch_points = (
            test_case_generation_batch_point_repository
            .list_batch_points(batch_id)
        )

        self.assertEqual(len(batch_points), 1)
        self.assertEqual(batch_points[0]["point_id"], "TP001")

        self.assertEqual(
            batch_points[0]["point_content"]["title"],
            "正确账号密码登录成功",
        )

        # D. 检查候选用例
        candidates = self._get_candidates(batch_id)

        self.assertEqual(len(candidates), 2)

        for candidate in candidates:
            self.assertEqual(
                candidate["manual_review_status"],
                "pending",
            )

            self.assertEqual(
                candidate["current_version"],
                1,
            )

        self.assertEqual(
            candidates[0]["current_content"]["title"],
            "使用正确账号密码登录成功",
        )

        self.assertEqual(
            candidates[1]["current_content"]["title"],
            "登录成功后进入游戏主界面",
        )

        # E. 检查候选版本和质量记录
        for candidate in candidates:
            candidate_id = candidate["id"]

            versions = (
                test_case_candidate_repository
                .list_candidate_versions(candidate_id)
            )

            self.assertEqual(len(versions), 1)
            self.assertEqual(versions[0]["version_no"], 1)

            version_id = versions[0]["id"]

            self.assertEqual(
                self._get_quality_counts(
                    candidate_id,
                    version_id,
                ),
                (1, 1),
            )

        # F. 检查候选级 Reviewer 报告独立性
        first_version = (
            test_case_candidate_repository
            .list_candidate_versions(candidates[0]["id"])[0]
        )

        second_version = (
            test_case_candidate_repository
            .list_candidate_versions(candidates[1]["id"])[0]
        )

        first_reviewer = (
            test_case_quality_repository
            .get_latest_reviewer_record(
                candidates[0]["id"],
                first_version["id"],
            )
        )

        second_reviewer = (
            test_case_quality_repository
            .get_latest_reviewer_record(
                candidates[1]["id"],
                second_version["id"],
            )
        )

        self.assertEqual(
            first_reviewer["overall_status"],
            "passed",
        )

        self.assertEqual(
            second_reviewer["overall_status"],
            "needs_review",
        )

        # G. 检查测试点筛选
        self.assertEqual(
            [
                item["point_id"]
                for item in batch_points
            ],
            ["TP001"],
        )

        print("\n========== 测试用例生成集成验收 ==========")
        print("生成批次 ID：", batch_id)
        print("来源测试点数量：", len(batch_points))
        print("候选用例数量：", len(candidates))
        print("Generator 调用次数：", generator_mock.call_count)
        print("Reviewer 调用次数：", reviewer_mock.call_count)
        print("候选 V1 及质量记录：全部存在")
        print("候选级 Reviewer 状态：")
        print("  候选 1：", first_reviewer["overall_status"])
        print("  候选 2：", second_reviewer["overall_status"])
        print("最终批次状态：", batch["status"])
        print("==========================================")

    # ==================================================
    # 6. 没有已审核测试点时不创建批次
    # ==================================================

    def test_no_approved_points_should_not_create_batch(self):
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE test_points
                SET manual_review_status = 'pending'
                WHERE batch_id = ?
                """,
                ("point-batch-1",),
            )

        with self.assertRaises(ValueError):
            generation_service.run_testcase_generation(
                project_id="project-1",
                requirement_analysis_id="analysis-1",
                test_point_batch_id="point-batch-1",
            )

        with self._get_connection() as conn:
            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_generation_batches
                WHERE project_id = ?
                """,
                ("project-1",),
            ).fetchone()[0]

        self.assertEqual(count, 0)

    # ==================================================
    # 7. FIX-10.1：来源测试点批次校验
    # ==================================================

    def test_source_batch_not_exists_should_be_rejected(self):
        with self.assertRaises(ValueError):
            generation_service.run_testcase_generation(
                project_id="project-1",
                requirement_analysis_id="analysis-1",
                test_point_batch_id="not-exists",
            )

        # 来源批次校验失败时，不应创建测试用例生成批次
        with self._get_connection() as conn:
            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_generation_batches
                """
            ).fetchone()[0]

        self.assertEqual(count, 0)

    def test_source_batch_project_mismatch_should_be_rejected(self):
        with patch.object(
            generation_service,
            "get_test_point_generation_batch",
            return_value={
                "id": "point-batch-1",
                "project_id": "project-2",
                "requirement_analysis_id": "analysis-1",
            },
        ):
            with self.assertRaises(ValueError):
                generation_service.run_testcase_generation(
                    project_id="project-1",
                    requirement_analysis_id="analysis-1",
                    test_point_batch_id="point-batch-1",
                )

        with self._get_connection() as conn:
            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_generation_batches
                """
            ).fetchone()[0]

        self.assertEqual(count, 0)

    def test_source_batch_analysis_mismatch_should_be_rejected(self):
        with patch.object(
            generation_service,
            "get_test_point_generation_batch",
            return_value={
                "id": "point-batch-1",
                "project_id": "project-1",
                "requirement_analysis_id": "analysis-other",
            },
        ):
            with self.assertRaises(ValueError):
                generation_service.run_testcase_generation(
                    project_id="project-1",
                    requirement_analysis_id="analysis-1",
                    test_point_batch_id="point-batch-1",
                )

        with self._get_connection() as conn:
            count = conn.execute(
                """
                SELECT COUNT(*)
                FROM test_case_generation_batches
                """
            ).fetchone()[0]

        self.assertEqual(count, 0)

    # ==================================================
    # 8. FIX-10.2：单条候选异常不应中断后续候选
    # ==================================================

    def test_candidate_failure_should_not_stop_next_candidate(self):
        generation_mock = self._build_generation_result()

        # 第一条候选 Reviewer 异常，第二条正常返回
        reviewer_results = [
            RuntimeError("模拟第一条候选 Reviewer 处理失败"),
            self._build_passed_review(),
        ]

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ) as generator_mock:

            with patch.object(
                generation_service,
                "review_testcases",
                side_effect=reviewer_results,
            ) as reviewer_mock:

                result = generation_service.run_testcase_generation(
                    project_id="project-1",
                    requirement_analysis_id="analysis-1",
                    test_point_batch_id="point-batch-1",
                )

        # 第一条候选失败，因此整体批次应标记为 failed
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["total_points"], 1)
        self.assertEqual(result["failed_points"], 1)

        # Generator 仍然只调用一次
        generator_mock.assert_called_once()

        # Reviewer 应被调用两次，证明第二条候选继续执行
        self.assertEqual(reviewer_mock.call_count, 2)

        batch_id = result["batch_id"]
        batch = self._get_batch(batch_id)

        self.assertIsNotNone(batch)
        self.assertEqual(batch["status"], "failed")

        # 两条候选都应已创建，因为异常发生在 Reviewer 阶段
        candidates = self._get_candidates(batch_id)
        self.assertEqual(len(candidates), 2)

        # 第二条候选应有 Reviewer 质量记录
        second_candidate = candidates[1]

        second_versions = (
            test_case_candidate_repository
            .list_candidate_versions(second_candidate["id"])
        )

        self.assertEqual(len(second_versions), 1)

        second_reviewer = (
            test_case_quality_repository
            .get_latest_reviewer_record(
                second_candidate["id"],
                second_versions[0]["id"],
            )
        )

        self.assertIsNotNone(second_reviewer)
        self.assertEqual(
            second_reviewer["overall_status"],
            "passed",
        )

        # 第一条候选的 Reviewer 失败，不应有 Reviewer 记录
        first_candidate = candidates[0]

        first_versions = (
            test_case_candidate_repository
            .list_candidate_versions(first_candidate["id"])
        )

        self.assertEqual(len(first_versions), 1)

        first_reviewer = (
            test_case_quality_repository
            .get_latest_reviewer_record(
                first_candidate["id"],
                first_versions[0]["id"],
            )
        )

        self.assertIsNone(first_reviewer)

        # 验证服务返回的候选级结果记录
        point_results = result.get("point_results", [])

        self.assertEqual(len(point_results), 1)

        candidate_results = point_results[0].get(
            "candidate_results",
            [],
        )

        self.assertEqual(len(candidate_results), 2)
        self.assertFalse(candidate_results[0]["success"])
        self.assertTrue(candidate_results[1]["success"])

        print("\n========== FIX-10.2 候选异常隔离测试 ==========")
        print("候选数量：", len(candidates))
        print("Reviewer 调用次数：", reviewer_mock.call_count)
        print("候选 1：处理失败")
        print("候选 2：继续处理并成功")
        print("最终批次状态：", batch["status"])
        print("===============================================")


if __name__ == "__main__":
    unittest.main(verbosity=2)
