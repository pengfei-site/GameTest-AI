
import unittest

from core.case_schemas import (
    TestCaseCandidate,
    TestCaseCandidateCollection,
    TestCaseStep,
)
from core.testcase_validator import validate_testcases


def make_candidate(
    title="验证用户登录成功",
    objective="验证有效账号能够成功登录",
    steps=None,
    preconditions=None,
    postconditions=None,
):
    """构造单条测试用例测试数据。"""

    if steps is None:
        steps = [
            TestCaseStep(
                step_no=1,
                action="使用有效账号发起登录",
                expected_result="登录成功",
            ),
            TestCaseStep(
                step_no=2,
                action="确认当前界面",
                expected_result="进入游戏主界面",
            ),
        ]

    return TestCaseCandidate(
        title=title,
        objective=objective,
        priority="P0",
        preconditions=(
            ["存在有效账号"] if preconditions is None
            else preconditions
        ),
        steps=steps,
        postconditions=(
            ["账号处于已登录状态"]
            if postconditions is None
            else postconditions
        ),
    )


class TestCaseValidatorTests(unittest.TestCase):

    # --------------------------------------------------
    # 基础校验
    # --------------------------------------------------

    def test_valid_candidate(self):
        """正常候选用例应通过校验。"""

        collection = TestCaseCandidateCollection(
            candidates=[make_candidate()]
        )

        report = validate_testcases(collection)

        self.assertTrue(report.passed)
        self.assertEqual(report.total, 1)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.warning_count, 0)

    # --------------------------------------------------
    # V01：标题检查
    # --------------------------------------------------

    def test_empty_title(self):
        """标题纯空白应产生错误。"""

        candidate = make_candidate(title="   ")

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("标题" in error for error in report.errors)
        )

    # --------------------------------------------------
    # V02：测试目的检查
    # --------------------------------------------------

    def test_empty_objective(self):
        """测试目的纯空白应产生错误。"""

        candidate = make_candidate(objective="   ")

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("测试目的" in error for error in report.errors)
        )

    # --------------------------------------------------
    # V03：步骤序号检查
    # --------------------------------------------------

    def test_non_continuous_step_numbers(self):
        """步骤序号不连续应产生错误。"""

        steps = [
            TestCaseStep(
                step_no=1,
                action="执行第一步",
                expected_result="第一步完成",
            ),
            TestCaseStep(
                step_no=3,
                action="执行第二步",
                expected_result="第二步完成",
            ),
        ]

        candidate = make_candidate(steps=steps)

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("步骤序号不连续" in error for error in report.errors)
        )

    # --------------------------------------------------
    # V04、V05：操作和预期结果检查
    # --------------------------------------------------

    def test_empty_action(self):
        """测试操作纯空白应产生错误。"""

        steps = [
            TestCaseStep(
                step_no=1,
                action="   ",
                expected_result="操作完成",
            )
        ]

        candidate = make_candidate(steps=steps)

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("测试操作" in error for error in report.errors)
        )

    def test_empty_expected_result(self):
        """预期结果纯空白应产生错误。"""

        steps = [
            TestCaseStep(
                step_no=1,
                action="执行登录",
                expected_result="   ",
            )
        ]

        candidate = make_candidate(steps=steps)

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("预期结果" in error for error in report.errors)
        )

    # --------------------------------------------------
    # V06：前置条件和后置条件检查
    # --------------------------------------------------

    def test_empty_precondition(self):
        """纯空白前置条件应产生错误。"""

        candidate = make_candidate(
            preconditions=["   "]
        )

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("前置条件" in error for error in report.errors)
        )

    def test_empty_postcondition(self):
        """纯空白后置条件应产生错误。"""

        candidate = make_candidate(
            postconditions=["   "]
        )

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertFalse(report.passed)
        self.assertTrue(
            any("后置条件" in error for error in report.errors)
        )

    # --------------------------------------------------
    # V07：重复步骤检查
    # --------------------------------------------------

    def test_duplicate_steps_warning(self):
        """同一用例内完全重复的步骤应产生警告。"""

        steps = [
            TestCaseStep(
                step_no=1,
                action="执行登录",
                expected_result="登录成功",
            ),
            TestCaseStep(
                step_no=2,
                action="执行登录",
                expected_result="登录成功",
            ),
        ]

        candidate = make_candidate(steps=steps)

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.error_count, 0)
        self.assertGreater(report.warning_count, 0)

    # --------------------------------------------------
    # V08：重复候选用例检查
    # --------------------------------------------------

    def test_duplicate_candidates_warning(self):
        """完全重复的候选用例应产生警告。"""

        candidate_a = make_candidate()
        candidate_b = make_candidate()

        report = validate_testcases(
            TestCaseCandidateCollection(
                candidates=[candidate_a, candidate_b]
            )
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.error_count, 0)
        self.assertTrue(
            any("候选用例完全重复" in warning
                for warning in report.warnings)
        )

    # --------------------------------------------------
    # V09：零条候选用例检查
    # --------------------------------------------------

    def test_empty_candidate_collection(self):
        """零条候选用例应通过，但产生警告。"""

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[])
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.total, 0)
        self.assertEqual(report.error_count, 0)
        self.assertEqual(report.warning_count, 1)

    # --------------------------------------------------
    # ERROR 和 WARNING 关系检查
    # --------------------------------------------------

    def test_warning_does_not_block_validation(self):
        """只有警告时，校验仍然通过。"""

        steps = [
            TestCaseStep(
                step_no=1,
                action="执行登录",
                expected_result="登录成功",
            ),
            TestCaseStep(
                step_no=2,
                action="执行登录",
                expected_result="登录成功",
            ),
        ]

        candidate = make_candidate(steps=steps)

        report = validate_testcases(
            TestCaseCandidateCollection(candidates=[candidate])
        )

        self.assertTrue(report.passed)
        self.assertEqual(report.error_count, 0)
        self.assertGreater(report.warning_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
