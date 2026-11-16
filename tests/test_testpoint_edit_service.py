
import unittest
from unittest.mock import patch

from core.schemas import TestPointEditableContent
from core.testpoint_edit_service import edit_test_point


class TestPointEditService(unittest.TestCase):

    def setUp(self):
        self.test_point_id = "test-point-001"

        self.updated_content = TestPointEditableContent(
            requirement_id="REQ-001",
            category="positive",
            title="修改后的测试点标题",
            test_objective="验证修改后的测试目标",
            coverage_description="覆盖修改后的测试场景",
            priority="P1",
            source_rule="修改后的需求来源规则",
        )

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_normal_edit_success(self, mock_edit):
        """S-01：正常编辑成功"""

        result = edit_test_point(
            self.test_point_id,
            self.updated_content,
        )

        mock_edit.assert_called_once_with(
            self.test_point_id,
            self.updated_content,
        )

        self.assertEqual(result["success"], True)
        self.assertEqual(
            result["test_point_id"],
            self.test_point_id,
        )
        self.assertEqual(
            result["manual_review_status"],
            "pending",
        )

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_empty_test_point_id_rejected(self, mock_edit):
        """S-02：空测试点 ID 被拒绝"""

        with self.assertRaises(ValueError):
            edit_test_point("", self.updated_content)

        mock_edit.assert_not_called()

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_whitespace_test_point_id_rejected(self, mock_edit):
        """S-03：纯空白测试点 ID 被拒绝"""

        with self.assertRaises(ValueError):
            edit_test_point("   ", self.updated_content)

        mock_edit.assert_not_called()

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_non_string_test_point_id_rejected(self, mock_edit):
        """S-04：非法测试点 ID 类型被拒绝"""

        with self.assertRaises(ValueError):
            edit_test_point(None, self.updated_content)

        mock_edit.assert_not_called()

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_dict_content_rejected(self, mock_edit):
        """S-05：dict 不允许直接作为编辑内容"""

        with self.assertRaises(TypeError):
            edit_test_point(
                self.test_point_id,
                self.updated_content.model_dump(),
            )

        mock_edit.assert_not_called()

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_none_content_rejected(self, mock_edit):
        """S-06：None 编辑内容被拒绝"""

        with self.assertRaises(TypeError):
            edit_test_point(self.test_point_id, None)

        mock_edit.assert_not_called()

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_repository_error_propagated(self, mock_edit):
        """S-07：Repository 异常正确传递"""

        mock_edit.side_effect = ValueError("测试点不存在")

        with self.assertRaisesRegex(ValueError, "测试点不存在"):
            edit_test_point(
                self.test_point_id,
                self.updated_content,
            )

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_repository_runtime_error_propagated(self, mock_edit):
        """S-08：Repository 运行时异常正确传递"""

        mock_edit.side_effect = RuntimeError("数据库操作失败")

        with self.assertRaisesRegex(RuntimeError, "数据库操作失败"):
            edit_test_point(
                self.test_point_id,
                self.updated_content,
            )

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_test_point_id_is_stripped(self, mock_edit):
        """S-09：测试点 ID 首尾空格被清理"""

        result = edit_test_point(
            "  test-point-001  ",
            self.updated_content,
        )

        mock_edit.assert_called_once_with(
            "test-point-001",
            self.updated_content,
        )

        self.assertEqual(
            result["test_point_id"],
            "test-point-001",
        )

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_edit_content_is_not_modified(self, mock_edit):
        """S-10：Service 不擅自修改编辑内容"""

        original_data = self.updated_content.model_dump()

        edit_test_point(
            self.test_point_id,
            self.updated_content,
        )

        self.assertEqual(
            self.updated_content.model_dump(),
            original_data,
        )

    @patch("core.testpoint_edit_service.repository_edit_test_point")
    def test_success_result_structure(self, mock_edit):
        """S-11：成功返回结构完整"""

        result = edit_test_point(
            self.test_point_id,
            self.updated_content,
        )

        self.assertEqual(
            set(result.keys()),
            {
                "success",
                "test_point_id",
                "manual_review_status",
                "message",
            },
        )

        self.assertIs(result["success"], True)
        self.assertTrue(result["message"])


if __name__ == "__main__":
    unittest.main()
