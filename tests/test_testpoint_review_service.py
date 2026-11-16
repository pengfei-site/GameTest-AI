import unittest
from unittest.mock import patch

from core.testpoint_review_service import (
    approve_test_point,
    batch_approve_test_points,
    batch_reject_test_points,
    reject_test_point,
)


class TestPointReviewService(unittest.TestCase):

    def setUp(self):
        self.test_point_id = "test-point-001"
        self.test_point_ids = ["test-point-001", "test-point-002"]

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_success(self, mock_review):
        result = approve_test_point(self.test_point_id)

        mock_review.assert_called_once_with(self.test_point_id, "")
        self.assertEqual(result["success"], True)
        self.assertEqual(result["test_point_id"], self.test_point_id)
        self.assertEqual(result["manual_review_status"], "approved")

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_comment_is_stripped(self, mock_review):
        result = approve_test_point(self.test_point_id, "  通过意见  ")

        mock_review.assert_called_once_with(self.test_point_id, "通过意见")
        self.assertTrue(result["success"])

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_empty_comment_allowed(self, mock_review):
        approve_test_point(self.test_point_id, "   ")
        mock_review.assert_called_once_with(self.test_point_id, "")

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_invalid_id_rejected(self, mock_review):
        for value in ("", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                approve_test_point(value)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_non_string_id_rejected(self, mock_review):
        with self.assertRaises(ValueError):
            approve_test_point(None)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_non_string_comment_rejected(self, mock_review):
        with self.assertRaises(TypeError):
            approve_test_point(self.test_point_id, None)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_id_is_stripped(self, mock_review):
        result = approve_test_point("  test-point-001  ")
        mock_review.assert_called_once_with(self.test_point_id, "")
        self.assertEqual(result["test_point_id"], self.test_point_id)

    @patch("core.testpoint_review_service.repository_approve_test_point")
    def test_single_approve_repository_error_propagated(self, mock_review):
        mock_review.side_effect = ValueError("只有待审核的测试点才能执行审核操作")
        with self.assertRaisesRegex(ValueError, "只有待审核"):
            approve_test_point(self.test_point_id)

    @patch("core.testpoint_review_service.repository_reject_test_point")
    def test_single_reject_success(self, mock_review):
        result = reject_test_point(self.test_point_id, "内容不完整")

        mock_review.assert_called_once_with(self.test_point_id, "内容不完整")
        self.assertTrue(result["success"])
        self.assertEqual(result["manual_review_status"], "rejected")

    @patch("core.testpoint_review_service.repository_reject_test_point")
    def test_single_reject_reason_is_stripped(self, mock_review):
        reject_test_point(self.test_point_id, "  缺少边界条件  ")
        mock_review.assert_called_once_with(self.test_point_id, "缺少边界条件")

    @patch("core.testpoint_review_service.repository_reject_test_point")
    def test_single_reject_empty_reason_rejected(self, mock_review):
        for reason in ("", "   "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                reject_test_point(self.test_point_id, reason)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_reject_test_point")
    def test_single_reject_non_string_reason_rejected(self, mock_review):
        with self.assertRaises(TypeError):
            reject_test_point(self.test_point_id, None)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_reject_test_point")
    def test_single_reject_repository_error_propagated(self, mock_review):
        mock_review.side_effect = RuntimeError("数据库操作失败")
        with self.assertRaisesRegex(RuntimeError, "数据库操作失败"):
            reject_test_point(self.test_point_id, "原因")

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_success(self, mock_review):
        result = batch_approve_test_points(self.test_point_ids)

        mock_review.assert_called_once_with(self.test_point_ids, "")
        self.assertTrue(result["success"])
        self.assertEqual(result["test_point_ids"], self.test_point_ids)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["manual_review_status"], "approved")

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_normalizes_ids_and_comment(self, mock_review):
        result = batch_approve_test_points(
            ["  test-point-001 ", "test-point-002  "],
            "  批量通过  ",
        )
        normalized = self.test_point_ids
        mock_review.assert_called_once_with(normalized, "批量通过")
        self.assertEqual(result["test_point_ids"], normalized)

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_empty_list_rejected(self, mock_review):
        with self.assertRaises(ValueError):
            batch_approve_test_points([])
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_non_list_rejected(self, mock_review):
        with self.assertRaises(TypeError):
            batch_approve_test_points(("test-point-001",))
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_empty_id_rejected(self, mock_review):
        with self.assertRaises(ValueError):
            batch_approve_test_points(["test-point-001", "  "])
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_non_string_id_rejected(self, mock_review):
        with self.assertRaises(ValueError):
            batch_approve_test_points(["test-point-001", None])
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_duplicate_ids_rejected(self, mock_review):
        with self.assertRaises(ValueError):
            batch_approve_test_points(["point-001", " point-001 "])
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_non_string_comment_rejected(self, mock_review):
        with self.assertRaises(TypeError):
            batch_approve_test_points(self.test_point_ids, None)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_approve_test_points")
    def test_batch_approve_repository_error_propagated(self, mock_review):
        mock_review.side_effect = ValueError("跨批次")
        with self.assertRaisesRegex(ValueError, "跨批次"):
            batch_approve_test_points(self.test_point_ids)

    @patch("core.testpoint_review_service.repository_batch_reject_test_points")
    def test_batch_reject_success(self, mock_review):
        result = batch_reject_test_points(self.test_point_ids, "规则不完整")

        mock_review.assert_called_once_with(self.test_point_ids, "规则不完整")
        self.assertTrue(result["success"])
        self.assertEqual(result["test_point_ids"], self.test_point_ids)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["manual_review_status"], "rejected")

    @patch("core.testpoint_review_service.repository_batch_reject_test_points")
    def test_batch_reject_reason_is_stripped(self, mock_review):
        batch_reject_test_points(self.test_point_ids, "  原因  ")
        mock_review.assert_called_once_with(self.test_point_ids, "原因")

    @patch("core.testpoint_review_service.repository_batch_reject_test_points")
    def test_batch_reject_empty_reason_rejected(self, mock_review):
        for reason in ("", "   "):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                batch_reject_test_points(self.test_point_ids, reason)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_reject_test_points")
    def test_batch_reject_non_string_reason_rejected(self, mock_review):
        with self.assertRaises(TypeError):
            batch_reject_test_points(self.test_point_ids, None)
        mock_review.assert_not_called()

    @patch("core.testpoint_review_service.repository_batch_reject_test_points")
    def test_batch_reject_repository_error_propagated(self, mock_review):
        mock_review.side_effect = RuntimeError("批量事务失败")
        with self.assertRaisesRegex(RuntimeError, "批量事务失败"):
            batch_reject_test_points(self.test_point_ids, "原因")


if __name__ == "__main__":
    unittest.main()
