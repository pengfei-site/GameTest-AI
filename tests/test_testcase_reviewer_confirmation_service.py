
import unittest
from unittest.mock import patch

from core.testcase_reviewer_confirmation_service import (
    confirm_reviewer_report,
    get_latest_reviewer_confirmation,
    list_reviewer_confirmation_history,
)


class TestCaseReviewerConfirmationServiceTest(unittest.TestCase):

    def setUp(self):
        self.reviewer_record_id = "reviewer-001"
        self.candidate_id = "candidate-001"
        self.candidate_version_id = "version-001"
        self.confirmed_by = "tester"

        self.confirmation_record = {
            "id": "confirmation-001",
            "reviewer_record_id": self.reviewer_record_id,
            "candidate_id": self.candidate_id,
            "candidate_version_id": self.candidate_version_id,
            "confirmation_status": "confirmed_passed",
            "confirmation_comment": "人工确认通过",
            "confirmed_by": self.confirmed_by,
        }

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_confirm_reviewer_report_success(self, mock_create):
        """提交人工确认成功。"""
        mock_create.return_value = self.confirmation_record

        result = confirm_reviewer_report(
            reviewer_record_id=self.reviewer_record_id,
            candidate_id=self.candidate_id,
            candidate_version_id=self.candidate_version_id,
            confirmation_status="confirmed_passed",
            confirmed_by=self.confirmed_by,
            confirmation_comment="人工确认通过",
        )

        self.assertEqual(result, self.confirmation_record)

        mock_create.assert_called_once_with(
            reviewer_record_id=self.reviewer_record_id,
            candidate_id=self.candidate_id,
            candidate_version_id=self.candidate_version_id,
            confirmation_status="confirmed_passed",
            confirmed_by=self.confirmed_by,
            confirmation_comment="人工确认通过",
        )

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_confirm_all_supported_statuses(self, mock_create):
        """三种人工确认结果均允许提交。"""
        statuses = [
            "confirmed_passed",
            "confirmed_issues",
            "recheck_required",
        ]

        for status in statuses:
            with self.subTest(status=status):
                mock_create.reset_mock()
                mock_create.return_value = {
                    **self.confirmation_record,
                    "confirmation_status": status,
                }

                result = confirm_reviewer_report(
                    self.reviewer_record_id,
                    self.candidate_id,
                    self.candidate_version_id,
                    status,
                    self.confirmed_by,
                )

                self.assertEqual(
                    result["confirmation_status"],
                    status,
                )
                mock_create.assert_called_once()

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_invalid_confirmation_status(self, mock_create):
        """非法确认状态必须拒绝。"""
        with self.assertRaises(ValueError):
            confirm_reviewer_report(
                self.reviewer_record_id,
                self.candidate_id,
                self.candidate_version_id,
                "approved",
                self.confirmed_by,
            )

        mock_create.assert_not_called()

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_empty_required_fields(self, mock_create):
        """必填字段不能为空。"""
        cases = [
            ("", self.candidate_id, self.candidate_version_id,
             "confirmed_passed", self.confirmed_by),
            (self.reviewer_record_id, "", self.candidate_version_id,
             "confirmed_passed", self.confirmed_by),
            (self.reviewer_record_id, self.candidate_id, "",
             "confirmed_passed", self.confirmed_by),
            (self.reviewer_record_id, self.candidate_id,
             self.candidate_version_id, "confirmed_passed", ""),
        ]

        for args in cases:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    confirm_reviewer_report(*args)

        mock_create.assert_not_called()

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_comment_must_be_string(self, mock_create):
        """确认意见必须是字符串。"""
        with self.assertRaises(ValueError):
            confirm_reviewer_report(
                self.reviewer_record_id,
                self.candidate_id,
                self.candidate_version_id,
                "confirmed_passed",
                self.confirmed_by,
                None,
            )

        mock_create.assert_not_called()

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_repository_rejects_mismatched_reviewer(self, mock_create):
        """Repository 拒绝错误的报告关联时，Service 透传异常。"""
        mock_create.side_effect = ValueError(
            "Reviewer 报告不存在或版本不匹配"
        )

        with self.assertRaises(ValueError):
            confirm_reviewer_report(
                self.reviewer_record_id,
                self.candidate_id,
                "wrong-version",
                "confirmed_passed",
                self.confirmed_by,
            )

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.get_latest_reviewer_confirmation"
    )
    def test_latest_confirmation_pending(self, mock_get):
        """没有人工确认记录时返回 pending。"""
        mock_get.return_value = None

        result = get_latest_reviewer_confirmation(
            self.reviewer_record_id
        )

        self.assertEqual(
            result["reviewer_record_id"],
            self.reviewer_record_id,
        )
        self.assertEqual(
            result["confirmation_status"],
            "pending",
        )
        self.assertIsNone(result["confirmation"])

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.get_latest_reviewer_confirmation"
    )
    def test_get_latest_confirmation_success(self, mock_get):
        """查询最新人工确认记录。"""
        mock_get.return_value = self.confirmation_record

        result = get_latest_reviewer_confirmation(
            self.reviewer_record_id
        )

        self.assertEqual(
            result["confirmation_status"],
            "confirmed_passed",
        )
        self.assertEqual(
            result["confirmation"],
            self.confirmation_record,
        )

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.list_reviewer_confirmations"
    )
    def test_list_confirmation_history(self, mock_list):
        """查询完整人工确认历史。"""
        history = [
            {
                **self.confirmation_record,
                "confirmation_status": "confirmed_issues",
            },
            self.confirmation_record,
        ]
        mock_list.return_value = history

        result = list_reviewer_confirmation_history(
            self.reviewer_record_id
        )

        self.assertEqual(result, history)
        self.assertEqual(len(result), 2)

        mock_list.assert_called_once_with(
            self.reviewer_record_id
        )

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.list_reviewer_confirmations"
    )
    def test_empty_confirmation_history(self, mock_list):
        """没有确认历史时返回空列表。"""
        mock_list.return_value = []

        result = list_reviewer_confirmation_history(
            self.reviewer_record_id
        )

        self.assertEqual(result, [])

    def test_empty_reviewer_record_id_rejected(self):
        """查询时 Reviewer 报告 ID 不能为空。"""
        with self.assertRaises(ValueError):
            get_latest_reviewer_confirmation("")

        with self.assertRaises(ValueError):
            list_reviewer_confirmation_history(" ")

    @patch(
        "core.testcase_reviewer_confirmation_service."
        "quality_repo.create_reviewer_confirmation"
    )
    def test_comment_is_trimmed(self, mock_create):
        """确认意见去除首尾空格。"""
        mock_create.return_value = self.confirmation_record

        confirm_reviewer_report(
            self.reviewer_record_id,
            self.candidate_id,
            self.candidate_version_id,
            "confirmed_passed",
            self.confirmed_by,
            "  人工确认通过  ",
        )

        self.assertEqual(
            mock_create.call_args.kwargs["confirmation_comment"],
            "人工确认通过",
        )


if __name__ == "__main__":
    unittest.main()
