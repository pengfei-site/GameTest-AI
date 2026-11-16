
import json
import unittest
from unittest.mock import patch

from core.schemas import RequirementAnalysis, TestPoint
from core.case_schemas import (
    TestCaseStep,
    TestCaseCandidate,
    TestCaseCandidateCollection,
)
from core.testcase_reviewer import review_testcases


class TestTestCaseReviewer(unittest.TestCase):

    def setUp(self):
        # 使用 model_construct 构造测试输入，不依赖真实业务数据
        self.requirement = RequirementAnalysis.model_construct()
        self.test_point = TestPoint.model_construct()

        self.candidates = TestCaseCandidateCollection(
            candidates=[
                TestCaseCandidate(
                    title="有效账号登录成功",
                    objective="验证有效账号可以成功登录",
                    priority="P0",
                    preconditions=["存在有效账号"],
                    steps=[
                        TestCaseStep(
                            step_no=1,
                            action="使用有效账号和正确密码发起登录",
                            expected_result="登录成功"
                        )
                    ],
                    postconditions=["账号处于已登录状态"]
                ),
                TestCaseCandidate(
                    title="错误密码登录",
                    objective="验证错误密码的处理",
                    priority="P1",
                    preconditions=["存在有效账号"],
                    steps=[
                        TestCaseStep(
                            step_no=1,
                            action="使用错误密码发起登录",
                            expected_result="系统提示密码错误"
                        )
                    ],
                    postconditions=[]
                )
            ]
        )

    def mock_review(self, data):
        return patch(
            "core.testcase_reviewer.ai_client.chat_json",
            return_value=json.dumps(
                data,
                ensure_ascii=False
            )
        )

    def test_normal_review(self):
        """正常审查：所有候选用例均通过"""

        data = {
            "overall_status": "passed",
            "summary": "所有候选用例均符合审查要求",
            "issues": [],
            "approved_candidate_indices": [1, 2],
            "review_candidate_indices": []
        }

        with self.mock_review(data):
            result = review_testcases(
                self.requirement,
                self.test_point,
                self.candidates
            )

        self.assertEqual(result.overall_status, "passed")
        self.assertEqual(
            result.approved_candidate_indices,
            [1, 2]
        )
        self.assertEqual(
            result.review_candidate_indices,
            []
        )

    def test_issue_candidate_must_be_reviewed(self):
        """存在问题的候选必须进入人工复核"""

        data = {
            "overall_status": "passed",
            "summary": "发现一个问题",
            "issues": [
                {
                    "candidate_index": 1,
                    "issue_type": "unclear_step",
                    "severity": "major",
                    "description": "操作步骤不够明确",
                    "suggestion": "补充具体操作方式"
                }
            ],
            "approved_candidate_indices": [1, 2],
            "review_candidate_indices": []
        }

        with self.mock_review(data):
            result = review_testcases(
                self.requirement,
                self.test_point,
                self.candidates
            )

        self.assertEqual(
            result.approved_candidate_indices,
            [2]
        )
        self.assertEqual(
            result.review_candidate_indices,
            [1]
        )
        self.assertEqual(
            result.overall_status,
            "needs_review"
        )

    def test_unclassified_candidate_must_be_reviewed(self):
        """未分类候选不能默认通过"""

        data = {
            "overall_status": "passed",
            "summary": "第一个候选通过",
            "issues": [],
            "approved_candidate_indices": [1],
            "review_candidate_indices": []
        }

        with self.mock_review(data):
            result = review_testcases(
                self.requirement,
                self.test_point,
                self.candidates
            )

        self.assertEqual(
            result.approved_candidate_indices,
            [1]
        )
        self.assertEqual(
            result.review_candidate_indices,
            [2]
        )
        self.assertEqual(
            result.overall_status,
            "needs_review"
        )

    def test_invalid_candidate_index_is_removed(self):
        """无效序号被清理，未分类候选自动进入人工复核"""

        data = {
            "overall_status": "passed",
            "summary": "审查完成",
            "issues": [
                {
                    "candidate_index": 99,
                    "issue_type": "logic_error",
                    "severity": "critical",
                    "description": "无效候选的问题",
                    "suggestion": "无需处理"
                }
            ],
            "approved_candidate_indices": [1, 99],
            "review_candidate_indices": []
        }

        with self.mock_review(data):
            result = review_testcases(
                self.requirement,
                self.test_point,
                self.candidates
            )

        # 无效序号 99 被清理
        self.assertEqual(
            result.approved_candidate_indices,
            [1]
        )

        # 候选 2 未分类，自动进入人工复核
        self.assertEqual(
            result.review_candidate_indices,
            [2]
        )

        # 无效问题记录被忽略
        self.assertEqual(result.issues, [])

        # 存在待复核候选，整体状态不能是 passed
        self.assertEqual(
            result.overall_status,
            "needs_review"
        )

    def test_review_list_has_priority(self):
        """同一候选同时出现在两个列表时，以复核为准"""

        data = {
            "overall_status": "passed",
            "summary": "审查完成",
            "issues": [],
            "approved_candidate_indices": [1, 2],
            "review_candidate_indices": [1]
        }

        with self.mock_review(data):
            result = review_testcases(
                self.requirement,
                self.test_point,
                self.candidates
            )

        self.assertEqual(
            result.approved_candidate_indices,
            [2]
        )
        self.assertEqual(
            result.review_candidate_indices,
            [1]
        )
        self.assertEqual(
            result.overall_status,
            "needs_review"
        )

    def test_failed_status_is_preserved(self):
        """failed 状态不能被自动降级为 passed"""

        data = {
            "overall_status": "failed",
            "summary": "存在严重业务逻辑错误",
            "issues": [
                {
                    "candidate_index": 1,
                    "issue_type": "logic_error",
                    "severity": "critical",
                    "description": "业务逻辑错误",
                    "suggestion": "重新检查测试逻辑"
                }
            ],
            "approved_candidate_indices": [2],
            "review_candidate_indices": [1]
        }

        with self.mock_review(data):
            result = review_testcases(
                self.requirement,
                self.test_point,
                self.candidates
            )

        self.assertEqual(
            result.overall_status,
            "failed"
        )
        self.assertEqual(
            result.review_candidate_indices,
            [1]
        )

    def test_empty_candidates(self):
        """零候选用例不调用 AI，直接返回 needs_review"""

        empty_candidates = TestCaseCandidateCollection(
            candidates=[]
        )

        with patch(
            "core.testcase_reviewer.ai_client.chat_json"
        ) as mock_ai:
            result = review_testcases(
                self.requirement,
                self.test_point,
                empty_candidates
            )

        mock_ai.assert_not_called()

        self.assertEqual(
            result.overall_status,
            "needs_review"
        )
        self.assertEqual(result.issues, [])
        self.assertEqual(
            result.approved_candidate_indices,
            []
        )
        self.assertEqual(
            result.review_candidate_indices,
            []
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
