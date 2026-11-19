
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

    def _build_batch_review(self):
        """
        构造两条候选的批量审核报告。

        candidate_index 从 1 开始：
        1 -> 第一条候选
        2 -> 第二条候选
        """
        return TestCaseReviewResult(
            overall_status="needs_review",
            summary="第一条候选通过审核，第二条候选需要人工复核。",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[2],
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

        batch_review = self._build_batch_review()

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ) as generator_mock:

            with patch.object(
                generation_service,
                "review_testcases",
                return_value=batch_review,
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
        reviewer_mock.assert_called_once()

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
    # 8. 批量 Reviewer 异常处理
    # ==================================================

    def test_batch_reviewer_failure_should_mark_all_candidates_failed(self):
        generation_mock = self._build_generation_result()

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ) as generator_mock:

            with patch.object(
                generation_service,
                "review_testcases",
                side_effect=RuntimeError("模拟批量 Reviewer 处理失败"),
            ) as reviewer_mock:

                result = generation_service.run_testcase_generation(
                    project_id="project-1",
                    requirement_analysis_id="analysis-1",
                    test_point_batch_id="point-batch-1",
                )

        # 批量审核失败，整体批次应标记为 failed
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["total_points"], 1)
        self.assertEqual(result["failed_points"], 1)

        generator_mock.assert_called_once()
        reviewer_mock.assert_called_once()

        batch_id = result["batch_id"]
        batch = self._get_batch(batch_id)

        self.assertIsNotNone(batch)
        self.assertEqual(batch["status"], "failed")

        # 批量审核发生在候选创建之后，因此两条候选都应存在
        candidates = self._get_candidates(batch_id)
        self.assertEqual(len(candidates), 2)

        # 两条候选都应有独立版本，但没有成功保存的 Reviewer 记录
        for candidate in candidates:
            versions = (
                test_case_candidate_repository
                .list_candidate_versions(candidate["id"])
            )

            self.assertEqual(len(versions), 1)

            reviewer_record = (
                test_case_quality_repository
                .get_latest_reviewer_record(
                    candidate["id"],
                    versions[0]["id"],
                )
            )

            self.assertIsNone(reviewer_record)

        # 服务返回的两条候选结果都应标记失败
        point_results = result.get("point_results", [])
        self.assertEqual(len(point_results), 1)

        candidate_results = point_results[0].get(
            "candidate_results",
            [],
        )

        self.assertEqual(len(candidate_results), 2)

        for candidate_result in candidate_results:
            self.assertFalse(candidate_result["success"])

        print("\n========== 批量 Reviewer 异常隔离测试 ==========")
        print("候选数量：", len(candidates))
        print("Reviewer 调用次数：", reviewer_mock.call_count)
        print("两条候选均创建成功，批量审核失败")
        print("最终批次状态：", batch["status"])
        print("==============================================")

    # ==================================================
    # 9. 单条 Reviewer 记录保存失败隔离
    # ==================================================

    def test_single_reviewer_record_failure_should_not_stop_other_candidates(self):
        generation_mock = self._build_generation_result()
        batch_review = self._build_batch_review()

        # 保存真实 Repository 方法，供第二条候选正常执行
        real_create_reviewer_record = (
            generation_service.create_reviewer_record
        )

        save_call_count = 0

        def reviewer_record_side_effect(*args, **kwargs):
            nonlocal save_call_count
            save_call_count += 1

            # 第一条候选模拟数据库保存失败
            if save_call_count == 1:
                raise RuntimeError("模拟第一条候选 Reviewer 记录保存失败")

            # 第二条候选调用真实 Repository 方法
            return real_create_reviewer_record(*args, **kwargs)

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ) as generator_mock:

            with patch.object(
                generation_service,
                "review_testcases",
                return_value=batch_review,
            ) as reviewer_mock:

                with patch.object(
                    generation_service,
                    "create_reviewer_record",
                    side_effect=reviewer_record_side_effect,
                ) as save_mock:

                    result = generation_service.run_testcase_generation(
                        project_id="project-1",
                        requirement_analysis_id="analysis-1",
                        test_point_batch_id="point-batch-1",
                    )

        # A. 检查整体结果
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["total_points"], 1)
        self.assertEqual(result["failed_points"], 1)
        self.assertEqual(result["total_candidates"], 2)

        # B. 检查 AI 调用次数
        generator_mock.assert_called_once()
        reviewer_mock.assert_called_once()

        # 两条候选分别保存 Reviewer 记录
        self.assertEqual(save_mock.call_count, 2)

        # C. 检查批次状态
        batch_id = result["batch_id"]
        batch = self._get_batch(batch_id)

        self.assertIsNotNone(batch)
        self.assertEqual(batch["status"], "failed")

        # D. 检查两条候选
        candidates = self._get_candidates(batch_id)
        self.assertEqual(len(candidates), 2)

        first_candidate = candidates[0]
        second_candidate = candidates[1]

        first_version = (
            test_case_candidate_repository
            .list_candidate_versions(first_candidate["id"])[0]
        )

        second_version = (
            test_case_candidate_repository
            .list_candidate_versions(second_candidate["id"])[0]
        )

        # 第一条候选保存 Reviewer 记录失败
        first_reviewer = (
            test_case_quality_repository
            .get_latest_reviewer_record(
                first_candidate["id"],
                first_version["id"],
            )
        )

        self.assertIsNone(first_reviewer)

        # 第二条候选应继续保存成功
        second_reviewer = (
            test_case_quality_repository
            .get_latest_reviewer_record(
                second_candidate["id"],
                second_version["id"],
            )
        )

        self.assertIsNotNone(second_reviewer)
        self.assertEqual(
            second_reviewer["overall_status"],
            "needs_review",
        )

        # E. 检查候选处理结果
        point_results = result.get("point_results", [])
        self.assertEqual(len(point_results), 1)

        candidate_results = point_results[0].get(
            "candidate_results",
            [],
        )

        self.assertEqual(len(candidate_results), 2)

        # 第一条失败，第二条成功
        self.assertFalse(candidate_results[0]["success"])
        self.assertTrue(candidate_results[1]["success"])

        self.assertIn(
            "Reviewer 结果失败",
            candidate_results[0]["error_message"],
        )

        self.assertEqual(
            candidate_results[1]["error_message"],
            "",
        )

        print("\n========== 单条 Reviewer 保存失败隔离测试 ==========")
        print("候选数量：", len(candidates))
        print("批量 Reviewer 调用次数：", reviewer_mock.call_count)
        print("Reviewer 记录保存次数：", save_mock.call_count)
        print("第一条候选：保存失败")
        print("第二条候选：保存成功")
        print("最终批次状态：", batch["status"])
        print("================================================")

    # ==================================================
    # 10. 单候选 Validator 失败隔离
    # ==================================================

    def test_single_candidate_validator_failure_should_not_stop_other_candidates(self):
        generation_mock = self._build_generation_result()

        # 只有第二条进入 Reviewer，因此批量报告的索引从 1 开始
        batch_review = TestCaseReviewResult(
            overall_status="passed",
            summary="剩余候选通过审核。",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[],
        )

        # 保存真实 Validator
        real_validator = generation_service.validate_testcases

        validator_call_count = 0

        def validator_side_effect(collection):
            nonlocal validator_call_count
            validator_call_count += 1

            # 第一次：集合级 Validator，正常执行
            if validator_call_count == 1:
                return real_validator(collection)

            # 第二次：第一条候选 Validator，模拟失败
            if validator_call_count == 2:
                raise RuntimeError("模拟第一条候选 Validator 失败")

            # 第三次：第二条候选 Validator，正常执行
            return real_validator(collection)

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ) as generator_mock:

            with patch.object(
                generation_service,
                "validate_testcases",
                side_effect=validator_side_effect,
            ) as validator_mock:

                with patch.object(
                    generation_service,
                    "review_testcases",
                    return_value=batch_review,
                ) as reviewer_mock:

                    result = generation_service.run_testcase_generation(
                        project_id="project-1",
                        requirement_analysis_id="analysis-1",
                        test_point_batch_id="point-batch-1",
                    )

        # A. 检查整体结果
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["total_points"], 1)
        self.assertEqual(result["failed_points"], 1)
        self.assertEqual(result["total_candidates"], 2)

        generator_mock.assert_called_once()

        # 集合级一次 + 两条候选各一次
        self.assertEqual(validator_mock.call_count, 3)

        # Reviewer 仍然只调用一次
        reviewer_mock.assert_called_once()

        # B. 检查 Reviewer 实际收到的候选
        reviewer_candidates = reviewer_mock.call_args.kwargs["candidates"]

        self.assertEqual(len(reviewer_candidates.candidates), 1)

        self.assertEqual(
            reviewer_candidates.candidates[0].title,
            "登录成功后进入游戏主界面",
        )

        # C. 检查候选记录
        batch_id = result["batch_id"]
        candidates = self._get_candidates(batch_id)

        self.assertEqual(len(candidates), 2)

        first_candidate = candidates[0]
        second_candidate = candidates[1]

        first_version = (
            test_case_candidate_repository
            .list_candidate_versions(first_candidate["id"])[0]
        )

        second_version = (
            test_case_candidate_repository
            .list_candidate_versions(second_candidate["id"])[0]
        )

        # 第一条 Validator 失败，不应产生候选级 Validator 记录
        first_counts = self._get_quality_counts(
            first_candidate["id"],
            first_version["id"],
        )

        self.assertEqual(first_counts, (0, 0))

        # 第二条 Validator 和 Reviewer 都应正常保存
        second_counts = self._get_quality_counts(
            second_candidate["id"],
            second_version["id"],
        )

        self.assertEqual(second_counts, (1, 1))

        # D. 检查候选处理结果
        point_results = result["point_results"]
        self.assertEqual(len(point_results), 1)

        candidate_results = point_results[0]["candidate_results"]

        self.assertEqual(len(candidate_results), 2)

        self.assertFalse(candidate_results[0]["success"])
        self.assertTrue(candidate_results[1]["success"])

        self.assertIn(
            "Validator 失败",
            candidate_results[0]["error_message"],
        )

        self.assertEqual(
            candidate_results[1]["error_message"],
            "",
        )

        print("\n========== 单候选 Validator 异常隔离测试 ==========")
        print("候选数量：", len(candidates))
        print("Validator 调用次数：", validator_mock.call_count)
        print("Reviewer 调用次数：", reviewer_mock.call_count)
        print("第一条候选：Validator 失败")
        print("第二条候选：Validator 和 Reviewer 均成功")
        print("最终批次状态：", result["status"])
        print("================================================")

    # ==================================================
    # 11. 批量 Reviewer 问题索引拆分
    # ==================================================

    def test_batch_reviewer_issues_should_be_split_by_candidate_index(self):
        generation_mock = self._build_generation_result()

        # 构造两条候选各自存在一个问题的批量审核报告
        batch_review = TestCaseReviewResult.model_validate({
            "overall_status": "needs_review",
            "summary": "两条候选均存在问题。",
            "issues": [
                {
                    "candidate_index": 1,
                    "issue_type": "unclear_step",
                    "severity": "major",
                    "description": "第一条候选的问题",
                    "suggestion": "补充第一条候选的操作说明。",
                },
                {
                    "candidate_index": 2,
                    "issue_type": "logic_error",
                    "severity": "critical",
                    "description": "第二条候选的问题",
                    "suggestion": "修正第二条候选的逻辑。",
                },
            ],
            "approved_candidate_indices": [],
            "review_candidate_indices": [1, 2],
        })

        with patch.object(
            generation_service,
            "generate_testcases",
            return_value=generation_mock,
        ):

            with patch.object(
                generation_service,
                "review_testcases",
                return_value=batch_review,
            ) as reviewer_mock:

                result = generation_service.run_testcase_generation(
                    project_id="project-1",
                    requirement_analysis_id="analysis-1",
                    test_point_batch_id="point-batch-1",
                )

        # A. 批量 Reviewer 只调用一次
        reviewer_mock.assert_called_once()

        # B. 检查两条候选均正常完成结果保存
        point_results = result["point_results"]
        self.assertEqual(len(point_results), 1)

        candidate_results = point_results[0]["candidate_results"]
        self.assertEqual(len(candidate_results), 2)

        self.assertTrue(candidate_results[0]["success"])
        self.assertTrue(candidate_results[1]["success"])

        # C. 检查批量报告是否正确拆分
        first_report = candidate_results[0]["review_report"]
        second_report = candidate_results[1]["review_report"]

        self.assertEqual(len(first_report["issues"]), 1)
        self.assertEqual(
            first_report["issues"][0]["candidate_index"],
            1,
        )
        self.assertEqual(
            first_report["issues"][0]["description"],
            "第一条候选的问题",
        )

        self.assertEqual(len(second_report["issues"]), 1)
        self.assertEqual(
            second_report["issues"][0]["candidate_index"],
            1,
        )
        self.assertEqual(
            second_report["issues"][0]["description"],
            "第二条候选的问题",
        )

        # D. 检查候选 Reviewer 记录分别保存
        batch_id = result["batch_id"]
        candidates = self._get_candidates(batch_id)

        self.assertEqual(len(candidates), 2)

        for candidate in candidates:
            versions = (
                test_case_candidate_repository
                .list_candidate_versions(candidate["id"])
            )

            self.assertEqual(len(versions), 1)

            reviewer_record = (
                test_case_quality_repository
                .get_latest_reviewer_record(
                    candidate["id"],
                    versions[0]["id"],
                )
            )

            self.assertIsNotNone(reviewer_record)

        print("\n========== 批量 Reviewer 索引拆分测试 ==========")
        print("Reviewer 调用次数：", reviewer_mock.call_count)
        print("第一条候选问题：", first_report["issues"][0]["description"])
        print("第二条候选问题：", second_report["issues"][0]["description"])
        print("拆分后的 candidate_index：1、1")
        print("两条候选 Reviewer 记录：均已保存")
        print("==============================================")


if __name__ == "__main__":
    unittest.main(verbosity=2)
