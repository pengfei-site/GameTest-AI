
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

from database import init_db
from database.repositories import (
    test_case_candidate_repository as candidate_repo,
    test_case_quality_repository as quality_repo,
)
from core import testcase_manual_review_service as review_service


class TestCaseManualReviewIntegration(unittest.TestCase):
    """
    STEP 10.6.6 人工审核模块集成验收。

    使用正式数据库初始化逻辑和隔离 SQLite 数据库，
    串联以下模块：

    1. 候选用例 Repository
    2. 质量记录 Repository
    3. 人工审核 Service

    不调用真实 AI，不修改正式业务数据库。
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "integration_test.db"

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
                quality_repo,
                "get_connection",
                side_effect=self._get_connection,
            ),
            patch.object(
                review_service,
                "get_connection",
                side_effect=self._get_connection,
            ),
        ]

        for patcher in self.connection_patches:
            patcher.start()

        # 使用项目正式数据库初始化逻辑创建完整表结构
        init_db.init_db()

        # 创建完整业务外键链
        self._create_test_data()

    def tearDown(self):
        for patcher in reversed(self.connection_patches):
            patcher.stop()

        self.temp_dir.cleanup()

    # =========================================================
    # 1. 隔离数据库连接
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
    # 2. 初始化完整业务测试数据
    # =========================================================

    def _create_test_data(self):
        with self._get_connection() as conn:

            # 1. 创建项目
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
                    "集成测试项目",
                ),
            )

            # 2. 创建策划文档
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

            # 3. 创建需求分析记录
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
                    "{}",
                ),
            )

            # 4. 先创建测试点生成批次
            # test_points.batch_id 依赖 generation_batches.id
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

            # 5. 再创建测试点
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
                    "验证用户使用正确账号密码登录成功",
                    "验证用户使用正确账号密码登录成功",
                ),
            )

            # 6. 创建测试用例生成批次
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

            # 7. 创建测试用例生成批次选点
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
                            "content": "验证用户使用正确账号密码登录成功",
                        },
                        ensure_ascii=False,
                    ),
                ),
            )

    # =========================================================
    # 3. 测试数据构造
    # =========================================================

    def _build_candidate(
        self,
        title="使用正确账号密码登录成功",
    ):
        return TestCaseCandidate(
            title=title,
            objective="验证用户能够使用正确账号密码登录游戏",
            priority="P0",
            preconditions=[
                "存在有效账号及对应密码",
            ],
            steps=[
                TestCaseStep(
                    step_no=1,
                    action="使用有效账号及对应密码发起登录",
                    expected_result="登录成功，系统进入游戏主界面",
                )
            ],
            postconditions=[
                "用户处于已登录状态",
            ],
        )

    def _build_validation_report(self):
        return TestCaseValidationReport(
            passed=True,
            total=1,
            error_count=0,
            warning_count=0,
            errors=[],
            warnings=[],
        )

    def _build_reviewer_report(self):
        return TestCaseReviewResult(
            overall_status="passed",
            summary="候选用例符合需求及来源测试点要求。",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[],
        )

    # =========================================================
    # 4. 保存质量记录
    # =========================================================

    def _save_quality_records(
        self,
        candidate_id,
        version_id,
    ):
        validation = quality_repo.create_validation_record(
            candidate_id=candidate_id,
            candidate_version_id=version_id,
            report=self._build_validation_report(),
        )

        reviewer = quality_repo.create_reviewer_record(
            candidate_id=candidate_id,
            candidate_version_id=version_id,
            report=self._build_reviewer_report(),
            model_name="mock-integration-test",
        )

        return validation, reviewer

    # =========================================================
    # 5. 数据查询辅助方法
    # =========================================================

    def _get_candidate(self, candidate_id):
        return candidate_repo.get_candidate_by_id(candidate_id)

    def _get_manual_reviews(self, candidate_id):
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM test_case_manual_reviews
                WHERE candidate_id = ?
                ORDER BY rowid
                """,
                (candidate_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def _get_quality_counts(
        self,
        candidate_id,
        version_id,
    ):
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

    # =========================================================
    # 6. 完整业务集成验收
    # =========================================================

    def test_complete_manual_review_lifecycle(self):
        """
        完整流程：

        创建 V1
        → 保存 V1 质量记录
        → V1 人工审核通过
        → 人工修改生成 V2
        → 验证 V2 无质量记录时不能通过
        → 保存 V2 质量记录
        → V2 人工审核通过
        → 检查版本、质量记录和审核历史
        """

        # -----------------------------------------------------
        # A. 创建候选 V1
        # -----------------------------------------------------

        original_candidate = self._build_candidate()

        created = candidate_repo.create_candidate(
            batch_id="case-batch-1",
            batch_point_id="batch-point-1",
            candidate_no=1,
            candidate=original_candidate,
        )

        candidate_id = created["id"]

        self.assertEqual(
            created["current_version"],
            1,
        )

        self.assertEqual(
            created["manual_review_status"],
            "pending",
        )

        self.assertEqual(
            created["current_content"]["title"],
            "使用正确账号密码登录成功",
        )

        versions = candidate_repo.list_candidate_versions(
            candidate_id,
        )

        self.assertEqual(len(versions), 1)

        version_1_id = versions[0]["id"]

        self.assertEqual(
            versions[0]["version_no"],
            1,
        )

        self.assertEqual(
            versions[0]["change_type"],
            "ai_generated",
        )

        # -----------------------------------------------------
        # B. 保存 V1 质量记录
        # -----------------------------------------------------

        self._save_quality_records(
            candidate_id,
            version_1_id,
        )

        validation_v1 = quality_repo.get_latest_validation_record(
            candidate_id,
            version_1_id,
        )

        reviewer_v1 = quality_repo.get_latest_reviewer_record(
            candidate_id,
            version_1_id,
        )

        self.assertIsNotNone(validation_v1)
        self.assertIsNotNone(reviewer_v1)

        self.assertTrue(validation_v1["passed"])

        self.assertEqual(
            reviewer_v1["overall_status"],
            "passed",
        )

        # -----------------------------------------------------
        # C. V1 人工审核通过
        # -----------------------------------------------------

        approval_v1 = review_service.approve_candidate(
            candidate_id,
            "V1 审核通过",
        )

        self.assertEqual(
            approval_v1["candidate_version_id"],
            version_1_id,
        )

        self.assertEqual(
            self._get_candidate(candidate_id)["manual_review_status"],
            "approved",
        )

        # -----------------------------------------------------
        # D. 人工修改，生成 V2
        # -----------------------------------------------------

        updated_candidate = self._build_candidate(
            title="使用有效账号登录并验证主界面展示",
        )

        modification = review_service.modify_candidate(
            candidate_id,
            updated_candidate,
            "优化标题，使测试目的更加明确",
        )

        version_2_id = modification["new_version_id"]

        self.assertEqual(
            modification["old_version_id"],
            version_1_id,
        )

        self.assertEqual(
            modification["new_version_no"],
            2,
        )

        current_candidate = self._get_candidate(candidate_id)

        self.assertEqual(
            current_candidate["current_version"],
            2,
        )

        self.assertEqual(
            current_candidate["manual_review_status"],
            "pending",
        )

        self.assertEqual(
            current_candidate["current_content"]["title"],
            "使用有效账号登录并验证主界面展示",
        )

        # -----------------------------------------------------
        # E. V2 没有质量记录时，禁止审核通过
        # -----------------------------------------------------

        with self.assertRaises(ValueError):
            review_service.approve_candidate(candidate_id)

        self.assertEqual(
            self._get_candidate(candidate_id)["manual_review_status"],
            "pending",
        )

        # -----------------------------------------------------
        # F. 保存 V2 独立质量记录
        # -----------------------------------------------------

        self._save_quality_records(
            candidate_id,
            version_2_id,
        )

        validation_v2 = quality_repo.get_latest_validation_record(
            candidate_id,
            version_2_id,
        )

        reviewer_v2 = quality_repo.get_latest_reviewer_record(
            candidate_id,
            version_2_id,
        )

        self.assertIsNotNone(validation_v2)
        self.assertIsNotNone(reviewer_v2)

        self.assertTrue(validation_v2["passed"])

        self.assertEqual(
            reviewer_v2["overall_status"],
            "passed",
        )

        # -----------------------------------------------------
        # G. V2 人工审核通过
        # -----------------------------------------------------

        approval_v2 = review_service.approve_candidate(
            candidate_id,
            "V2 审核通过",
        )

        self.assertEqual(
            approval_v2["candidate_version_id"],
            version_2_id,
        )

        self.assertEqual(
            self._get_candidate(candidate_id)["manual_review_status"],
            "approved",
        )

        # -----------------------------------------------------
        # H. 检查版本历史
        # -----------------------------------------------------

        versions = candidate_repo.list_candidate_versions(
            candidate_id,
        )

        self.assertEqual(len(versions), 2)

        self.assertEqual(
            versions[0]["version_no"],
            1,
        )

        self.assertEqual(
            versions[1]["version_no"],
            2,
        )

        self.assertEqual(
            versions[0]["content"]["title"],
            "使用正确账号密码登录成功",
        )

        self.assertEqual(
            versions[1]["content"]["title"],
            "使用有效账号登录并验证主界面展示",
        )

        self.assertEqual(
            versions[1]["change_type"],
            "manual_edit",
        )

        # -----------------------------------------------------
        # I. 检查两个版本的质量记录独立性
        # -----------------------------------------------------

        self.assertEqual(
            self._get_quality_counts(
                candidate_id,
                version_1_id,
            ),
            (1, 1),
        )

        self.assertEqual(
            self._get_quality_counts(
                candidate_id,
                version_2_id,
            ),
            (1, 1),
        )

        # 确认 V1 的旧质量报告仍然存在
        self.assertIsNotNone(
            quality_repo.get_latest_validation_record(
                candidate_id,
                version_1_id,
            )
        )

        self.assertIsNotNone(
            quality_repo.get_latest_reviewer_record(
                candidate_id,
                version_1_id,
            )
        )

        # -----------------------------------------------------
        # J. 检查人工审核历史
        # -----------------------------------------------------

        reviews = self._get_manual_reviews(candidate_id)

        self.assertEqual(len(reviews), 3)

        self.assertEqual(
            [item["action_type"] for item in reviews],
            [
                "approved",
                "modified",
                "approved",
            ],
        )

        # V1 首次审核通过
        self.assertEqual(
            reviews[0]["candidate_version_id"],
            version_1_id,
        )

        # 修改记录关联被修改的旧版本 V1
        self.assertEqual(
            reviews[1]["candidate_version_id"],
            version_1_id,
        )

        # V2 审核通过记录关联新版本 V2
        self.assertEqual(
            reviews[2]["candidate_version_id"],
            version_2_id,
        )

        self.assertEqual(
            reviews[1]["comment"],
            "优化标题，使测试目的更加明确",
        )

        # -----------------------------------------------------
        # K. 最终状态确认
        # -----------------------------------------------------

        final_candidate = self._get_candidate(candidate_id)

        self.assertEqual(
            final_candidate["current_version"],
            2,
        )

        self.assertEqual(
            final_candidate["manual_review_status"],
            "approved",
        )

        print("\n========== 人工审核集成验收结果 ==========")
        print("候选 ID：", candidate_id)
        print("V1 ID：", version_1_id)
        print("V2 ID：", version_2_id)
        print("候选版本数量：", len(versions))
        print("质量记录数量：4")
        print("人工审核历史：", len(reviews))
        print("最终审核状态：", final_candidate["manual_review_status"])
        print("==========================================")


if __name__ == "__main__":
    unittest.main(verbosity=2)
