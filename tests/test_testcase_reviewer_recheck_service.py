
import unittest
from unittest.mock import patch
from core.case_schemas import TestCaseCandidate
from core.review_schemas import TestCaseReviewResult as ReviewerResult

from core import testcase_reviewer_recheck_service as service


class TestTestcaseReviewerRecheckService(unittest.TestCase):

    def setUp(self):
        self.candidate_id = "candidate-1"
        self.version_id = "version-1"

        self.version_content = {
            "title": "有效账号登录成功",
            "objective": "验证有效账号可以成功登录",
            "priority": "P0",
            "preconditions": ["存在有效账号"],
            "steps": [],
            "postconditions": ["账号处于已登录状态"],
        }

        self.candidate_content = dict(self.version_content)

        self.candidate = {
            "id": self.candidate_id,
            "current_version": 1,
            "current_content": self.candidate_content,
            "batch_id": "batch-1",
            "batch_point_id": "batch-point-1",
            "manual_review_status": "pending",
        }

        self.version = {
            "id": self.version_id,
            "candidate_id": self.candidate_id,
            "version_no": 1,
            "content": self.version_content,
        }

        self.batch_point = {
            "id": "batch-point-1",
            "batch_id": "batch-1",
            "point_id": "point-1",
            "point_content": {
                "point_id": "point-1",
            },
        }

        self.generation_batch = {
            "id": "batch-1",
            "project_id": "project-1",
            "requirement_analysis_id": "analysis-1",
        }

        self.requirement_record = {
            "id": "analysis-1",
            "project_id": "project-1",
            "analysis_data": {},
        }

        self.candidate_model = TestCaseCandidate.model_construct(
            title="有效账号登录成功",
            objective="验证有效账号可以成功登录",
            priority="P0",
            preconditions=["存在有效账号"],
            steps=[],
            postconditions=["账号处于已登录状态"],
        )

        self.reviewer_report = ReviewerResult(
            overall_status="passed",
            summary="候选用例符合要求",
            issues=[],
            approved_candidate_indices=[1],
            review_candidate_indices=[],
        )

        self.reviewer_record = {
            "id": "reviewer-record-1",
            "candidate_id": self.candidate_id,
            "candidate_version_id": self.version_id,
            "overall_status": "passed",
            "summary": "候选用例符合要求",
        }

        # Repository Mock
        self.patches = [
            patch.object(
                service.candidate_repo,
                "get_candidate_by_id",
                return_value=self.candidate,
            ),
            patch.object(
                service.candidate_repo,
                "list_candidate_versions",
                return_value=[self.version],
            ),
            patch.object(
                service.batch_point_repo,
                "get_batch_point_by_id",
                return_value=self.batch_point,
            ),
            patch.object(
                service.batch_repo,
                "get_generation_batch",
                return_value=self.generation_batch,
            ),
            patch.object(
                service,
                "get_requirement_analysis",
                return_value=self.requirement_record,
            ),
            patch.object(
                service.quality_repo,
                "create_reviewer_record",
                return_value=self.reviewer_record,
            ),
            patch.object(
                service,
                "review_testcases",
                return_value=self.reviewer_report,
            ),
            patch.object(
                service.TestCaseCandidate,
                "model_validate",
                return_value=self.candidate_model,
            ),
            patch.object(
                service.TestPoint,
                "model_validate",
                return_value=service.TestPoint.model_construct(
                    point_id="point-1"
                ),
            ),
            patch.object(
                service.RequirementAnalysis,
                "model_validate",
                return_value=service.RequirementAnalysis.model_construct(),
            ),
        ]

        self.mocks = [p.start() for p in self.patches]

        self.addCleanup(self._stop_patches)

    def _stop_patches(self):
        for p in reversed(self.patches):
            p.stop()

    def _mock(self, index):
        return self.mocks[index]

    def _run(self):
        return service.recheck_testcase_with_reviewer(
            self.candidate_id
        )

    def test_successful_reviewer_recheck(self):
        """Reviewer 正常执行并保存报告。"""

        result = self._run()

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "completed")
        self.assertTrue(result["reviewer_saved"])
        self.assertEqual(
            result["candidate_version_id"],
            self.version_id,
        )
        self.assertEqual(result["version_no"], 1)
        self.assertEqual(
            result["reviewer_report"]["overall_status"],
            "passed",
        )

        self._mock(6).assert_called_once()
        self._mock(5).assert_called_once()

        self._mock(5).assert_called_once_with(
            candidate_id=self.candidate_id,
            candidate_version_id=self.version_id,
            report=self.reviewer_report,
        )

    def test_needs_review_report_is_saved(self):
        """Reviewer 返回 needs_review 仍然属于正常执行。"""

        needs_review_report = ReviewerResult(
            overall_status="needs_review",
            summary="存在待人工复核问题",
            issues=[],
            approved_candidate_indices=[],
            review_candidate_indices=[1],
        )

        self._mock(6).return_value = needs_review_report

        result = self._run()

        self.assertTrue(result["success"])
        self.assertTrue(result["reviewer_saved"])
        self.assertEqual(
            result["reviewer_report"]["overall_status"],
            "needs_review",
        )

        self._mock(5).assert_called_once()

    def test_reviewer_execution_failure(self):
        """Reviewer 执行异常，不保存报告。"""

        self._mock(6).side_effect = RuntimeError(
            "AI Reviewer execution failed"
        )

        result = self._run()

        self.assertFalse(result["success"])
        self.assertEqual(
            result["stage"],
            "reviewer_execution",
        )
        self.assertFalse(result["reviewer_saved"])
        self.assertIsNone(result["reviewer_record"])

        self._mock(5).assert_not_called()

    def test_reviewer_persistence_failure(self):
        """Reviewer 报告保存失败，返回持久化错误。"""

        self._mock(5).side_effect = RuntimeError(
            "Database write failed"
        )

        result = self._run()

        self.assertFalse(result["success"])
        self.assertEqual(
            result["stage"],
            "reviewer_persistence",
        )
        self.assertFalse(result["reviewer_saved"])
        self.assertIsNone(result["reviewer_record"])
        self.assertIsNotNone(result["reviewer_report"])

        self._mock(6).assert_called_once()

    def test_candidate_not_found(self):
        """候选不存在时拒绝执行。"""

        self._mock(0).return_value = None

        with self.assertRaises(ValueError):
            self._run()

        self._mock(6).assert_not_called()
        self._mock(5).assert_not_called()

    def test_candidate_content_mismatch(self):
        """候选正文与当前版本正文不一致时拒绝执行。"""

        different_candidate = TestCaseCandidate.model_construct(
            title="不同的用例标题",
            objective="不同的测试目标",
            priority="P0",
            preconditions=[],
            steps=[],
            postconditions=[],
        )

        self._mock(7).side_effect = [
            self.candidate_model,
            different_candidate,
        ]

        with self.assertRaises(ValueError):
            self._run()

        self._mock(6).assert_not_called()
        self._mock(5).assert_not_called()

    def test_reviewer_report_is_bound_to_current_version(self):
        """Reviewer 报告必须绑定候选当前版本。"""

        self.candidate["current_version"] = 2

        version_2 = {
            "id": "version-2",
            "candidate_id": self.candidate_id,
            "version_no": 2,
            "content": self.version_content,
        }

        self._mock(1).return_value = [
            self.version,
            version_2,
        ]

        result = self._run()

        self.assertTrue(result["success"])
        self.assertEqual(
            result["candidate_version_id"],
            "version-2",
        )
        self.assertEqual(result["version_no"], 2)

        self._mock(5).assert_called_once_with(
            candidate_id=self.candidate_id,
            candidate_version_id="version-2",
            report=self.reviewer_report,
        )

    def test_reviewer_recheck_does_not_modify_candidate(self):
        """独立 Reviewer 复核不能修改候选正文、版本及审核状态。"""

        original_content = dict(self.candidate["current_content"])
        original_version = self.candidate["current_version"]
        original_review_status = self.candidate[
            "manual_review_status"
        ]

        self._run()

        self.assertEqual(
            self.candidate["current_content"],
            original_content,
        )
        self.assertEqual(
            self.candidate["current_version"],
            original_version,
        )
        self.assertEqual(
            self.candidate["manual_review_status"],
            original_review_status,
        )

    def test_service_does_not_import_validator(self):
        """独立 Reviewer Service 不应依赖 Python Validator。"""

        self.assertFalse(
            hasattr(service, "validate_testcases")
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
