
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from openpyxl import load_workbook

from core.case_schemas import (
    TestCaseCandidate,
    TestCaseStep,
)

from core import testcase_export_service as export_service


class TestCaseExportService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_path = (
            Path(self.temp_dir.name) / "testcases.xlsx"
        )

        self.batch_id = "batch-001"

        self.requirement_record = {
            "id": "analysis-001",
            "analysis_data": {
                "module": "登录模块",
                "summary": "用户登录功能",
                "business_rules": [
                    {
                        "rule_id": "R1",
                        "rule_text": "用户可以使用账号和密码登录",
                        "source_text": "用户输入账号和密码后可以登录游戏",
                        "status": "confirmed",
                    }
                ],
                "preconditions": [],
                "states": [],
                "numeric_constraints": [],
                "exception_cases": [],
                "open_questions": [],
            },
        }

        self.batch_record = {
            "id": self.batch_id,
            "requirement_analysis_id": "analysis-001",
            "module": "登录模块",
            "status": "completed",
        }

        self.point_content = {
            "point_id": "TP001",
            "requirement_id": "R1",
            "category": "positive",
            "title": "正确账号密码登录",
            "test_objective": "验证用户能够成功登录",
            "coverage_description": "验证登录成功及主界面展示",
            "priority": "P0",
            "source_rule": "用户可以使用账号和密码登录",
        }

        self.batch_point_record = {
            "id": "batch-point-001",
            "batch_id": self.batch_id,
            "test_point_id": "point-001",
            "point_id": "TP001",
            "point_content": self.point_content,
        }

        self.candidate_1 = TestCaseCandidate(
            title="使用正确账号密码登录成功",
            objective="验证用户能够使用正确账号密码登录游戏",
            priority="P0",
            preconditions=[
                "存在有效账号",
                "账号对应密码正确",
            ],
            steps=[
                TestCaseStep(
                    step_no=1,
                    action="打开游戏登录界面",
                    expected_result="显示登录界面",
                ),
                TestCaseStep(
                    step_no=2,
                    action="输入有效账号和密码",
                    expected_result="账号和密码输入成功",
                ),
                TestCaseStep(
                    step_no=3,
                    action="点击登录",
                    expected_result="登录成功并进入游戏主界面",
                ),
            ],
            postconditions=[
                "用户处于已登录状态",
            ],
        )

        self.candidate_2 = TestCaseCandidate(
            title="登录成功后验证主界面",
            objective="验证登录成功后进入游戏主界面",
            priority="P1",
            preconditions=[
                "存在有效账号",
            ],
            steps=[
                TestCaseStep(
                    step_no=1,
                    action="使用有效账号登录",
                    expected_result="登录成功",
                ),
                TestCaseStep(
                    step_no=2,
                    action="观察登录后的界面",
                    expected_result="显示游戏主界面",
                ),
            ],
            postconditions=[],
        )

        self.candidates = [
            {
                "id": "candidate-001",
                "batch_id": self.batch_id,
                "batch_point_id": "batch-point-001",
                "candidate_no": 1,
                "current_version": 1,
                "manual_review_status": "approved",
                "current_content": self.candidate_1.model_dump(
                    mode="json"
                ),
            },
            {
                "id": "candidate-002",
                "batch_id": self.batch_id,
                "batch_point_id": "batch-point-001",
                "candidate_no": 2,
                "current_version": 1,
                "manual_review_status": "pending",
                "current_content": self.candidate_2.model_dump(
                    mode="json"
                ),
            },
            {
                "id": "candidate-003",
                "batch_id": self.batch_id,
                "batch_point_id": "batch-point-001",
                "candidate_no": 3,
                "current_version": 1,
                "manual_review_status": "rejected",
                "current_content": self.candidate_2.model_dump(
                    mode="json"
                ),
            },
        ]

        self.patches = [
            patch.object(
                export_service.batch_repo,
                "get_generation_batch",
                return_value=self.batch_record,
            ),
            patch.object(
                export_service.requirement_repo,
                "get_requirement_analysis",
                return_value=self.requirement_record,
            ),
            patch.object(
                export_service.candidate_repo,
                "list_candidates_by_batch",
                return_value=self.candidates,
            ),
            patch.object(
                export_service.batch_point_repo,
                "get_batch_point_by_id",
                return_value=self.batch_point_record,
            ),
        ]

        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()

        self.temp_dir.cleanup()

    # =====================================================
    # 1. 正常导出
    # =====================================================

    def test_export_only_approved_candidates(self):

        result = export_service.export_approved_testcases(
            self.batch_id,
            str(self.output_path),
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["exported_count"], 1)
        self.assertTrue(self.output_path.exists())

        workbook = load_workbook(self.output_path)

        self.assertEqual(
            workbook.sheetnames,
            ["测试用例", "来源追溯"],
        )

        workbook.close()

    # =====================================================
    # 2. 测试用例工作表内容
    # =====================================================

    def test_testcase_sheet_content(self):

        export_service.export_approved_testcases(
            self.batch_id,
            str(self.output_path),
        )

        workbook = load_workbook(self.output_path)
        worksheet = workbook["测试用例"]

        self.assertEqual(worksheet.max_row, 2)

        self.assertEqual(
            worksheet.cell(1, 1).value,
            "用例编号",
        )

        self.assertEqual(
            worksheet.cell(2, 1).value,
            "TC001",
        )

        self.assertEqual(
            worksheet.cell(2, 2).value,
            "使用正确账号密码登录成功",
        )

        self.assertEqual(
            worksheet.cell(2, 4).value,
            "P0",
        )

        # 验证多步骤以换行方式展示
        actions = worksheet.cell(2, 6).value
        expected_results = worksheet.cell(2, 7).value

        self.assertIn(
            "1. 打开游戏登录界面",
            actions,
        )

        self.assertIn(
            "2. 输入有效账号和密码",
            actions,
        )

        self.assertIn(
            "3. 点击登录",
            actions,
        )

        self.assertIn(
            "\n",
            actions,
        )

        self.assertIn(
            "\n",
            expected_results,
        )

        workbook.close()

    # =====================================================
    # 3. 来源追溯工作表内容
    # =====================================================

    def test_traceability_sheet_content(self):

        export_service.export_approved_testcases(
            self.batch_id,
            str(self.output_path),
        )

        workbook = load_workbook(self.output_path)
        worksheet = workbook["来源追溯"]

        self.assertEqual(worksheet.max_row, 2)

        self.assertEqual(
            worksheet.cell(2, 1).value,
            "TC001",
        )

        self.assertEqual(
            worksheet.cell(2, 2).value,
            "TP001",
        )

        self.assertIn(
            "正确账号密码登录",
            worksheet.cell(2, 3).value,
        )

        self.assertIn(
            "R1",
            worksheet.cell(2, 4).value,
        )

        self.assertIn(
            "用户可以使用账号和密码登录",
            worksheet.cell(2, 4).value,
        )

        workbook.close()

    # =====================================================
    # 4. 多条已通过候选用例
    # =====================================================

    def test_multiple_approved_candidates(self):

        self.candidates[1]["manual_review_status"] = "approved"

        result = export_service.export_approved_testcases(
            self.batch_id,
            str(self.output_path),
        )

        self.assertEqual(result["exported_count"], 2)

        workbook = load_workbook(self.output_path)
        worksheet = workbook["测试用例"]

        self.assertEqual(worksheet.max_row, 3)

        self.assertEqual(
            worksheet.cell(2, 1).value,
            "TC001",
        )

        self.assertEqual(
            worksheet.cell(3, 1).value,
            "TC002",
        )

        workbook.close()

    # =====================================================
    # 5. 没有审核通过的候选
    # =====================================================

    def test_no_approved_candidates_should_fail(self):

        for candidate in self.candidates:
            candidate["manual_review_status"] = "pending"

        with self.assertRaisesRegex(
            ValueError,
            "没有人工审核通过",
        ):
            export_service.export_approved_testcases(
                self.batch_id,
                str(self.output_path),
            )

        self.assertFalse(self.output_path.exists())

    # =====================================================
    # 6. 批次不存在
    # =====================================================

    def test_nonexistent_batch_should_fail(self):

        with patch.object(
            export_service.batch_repo,
            "get_generation_batch",
            return_value=None,
        ):

            with self.assertRaisesRegex(
                ValueError,
                "生成批次不存在",
            ):
                export_service.export_approved_testcases(
                    "not-exist",
                    str(self.output_path),
                )

    # =====================================================
    # 7. 需求分析不存在
    # =====================================================

    def test_nonexistent_requirement_should_fail(self):

        with patch.object(
            export_service.requirement_repo,
            "get_requirement_analysis",
            return_value=None,
        ):

            with self.assertRaisesRegex(
                ValueError,
                "需求分析记录不存在",
            ):
                export_service.export_approved_testcases(
                    self.batch_id,
                    str(self.output_path),
                )

    # =====================================================
    # 8. 文件扩展名不正确
    # =====================================================

    def test_invalid_file_extension_should_fail(self):

        invalid_path = (
            Path(self.temp_dir.name) / "testcases.csv"
        )

        with self.assertRaisesRegex(
            ValueError,
            r"\.xlsx",
        ):
            export_service.export_approved_testcases(
                self.batch_id,
                str(invalid_path),
            )

        self.assertFalse(invalid_path.exists())

    # =====================================================
    # 9. 测试点快照不存在
    # =====================================================

    def test_missing_batch_point_snapshot_should_fail(self):

        with patch.object(
            export_service.batch_point_repo,
            "get_batch_point_by_id",
            return_value=None,
        ):

            with self.assertRaisesRegex(
                ValueError,
                "测试点快照不存在",
            ):
                export_service.export_approved_testcases(
                    self.batch_id,
                    str(self.output_path),
                )

    # =====================================================
    # 10. 快照编号不一致
    # =====================================================

    def test_snapshot_point_id_mismatch_should_fail(self):

        invalid_snapshot = dict(self.batch_point_record)

        invalid_snapshot["point_content"] = {
            **self.point_content,
            "point_id": "TP999",
        }

        with patch.object(
            export_service.batch_point_repo,
            "get_batch_point_by_id",
            return_value=invalid_snapshot,
        ):

            with self.assertRaisesRegex(
                ValueError,
                "编号与内容不一致",
            ):
                export_service.export_approved_testcases(
                    self.batch_id,
                    str(self.output_path),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
