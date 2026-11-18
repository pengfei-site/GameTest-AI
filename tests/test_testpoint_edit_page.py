
"""测试点管理页面编辑功能自动化测试"""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from core.schemas import TestPointEditableContent


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PAGE_PATH = PROJECT_ROOT / "pages" / "08_测试点列表.py"


def make_test_point(is_deleted=False):
    """构造页面测试使用的测试点数据。"""

    return {
        "id": "test-point-uuid-001",
        "batch_id": "batch-uuid-001",
        "point_id": "TP-001",
        "original_content": {
            "requirement_id": "REQ-001",
            "category": "positive",
            "title": "原始测试点标题",
            "test_objective": "验证原始测试目标",
            "coverage_description": "原始覆盖描述",
            "priority": "P1",
            "source_rule": "原始来源规则",
        },
        "current_content": {
            "requirement_id": "REQ-001",
            "category": "positive",
            "title": "玩家正常登录",
            "test_objective": "验证玩家可以正常登录",
            "coverage_description": "覆盖正常登录流程",
            "priority": "P1",
            "source_rule": "登录功能规则",
        },
        "ai_review_status": "approved",
        "manual_review_status": "pending",
        "manual_comment": "",
        "reviewed_at": None,
        "is_deleted": 1 if is_deleted else 0,
        "deleted_at": (
            "2026-11-01 10:00:00"
            if is_deleted else None
        ),
        "created_at": "2026-11-01 09:00:00",
        "updated_at": "2026-11-01 09:00:00",
    }


class TestTestPointEditPage(unittest.TestCase):

    def setUp(self):

        self.test_point = make_test_point()

        self.projects = [
            {
                "id": "project-uuid-001",
                "project_name": "页面自动化测试项目",
            }
        ]

        self.batches = [
            {
                "id": "batch-uuid-001",
                "generated_at": "2026-11-01 09:00:00",
            }
        ]

        self.mock_list_projects = patch(
            "database.repositories.project_repository.list_projects",
            return_value=self.projects,
        )

        self.mock_list_batches = patch(
            "database.repositories.generation_batch_repository.list_generation_batches",
            return_value=self.batches,
        )

        self.mock_get_batch = patch(
            "database.repositories.generation_batch_repository.get_generation_batch",
            return_value=self.batches[0],
        )

        self.mock_list_points = patch(
            "database.repositories.test_point_repository.list_test_points",
            side_effect=lambda *args, **kwargs: [
                self.test_point
            ],
        )

        self.mock_get_point = patch(
            "database.repositories.test_point_repository.get_test_point",
            side_effect=lambda point_id: self.test_point,
        )

        self.mock_edit_service = patch(
            "core.testpoint_edit_service.edit_test_point",
            return_value={
                "success": True,
                "test_point_id": "test-point-uuid-001",
                "manual_review_status": "pending",
                "message": "测试点编辑成功，已保存修改历史",
            },
        )

        self.mock_list_projects.start()
        self.mock_list_batches.start()
        self.mock_get_batch.start()
        self.mock_list_points.start()
        self.mock_get_point.start()

        self.mock_edit = self.mock_edit_service.start()

        self.app = None

    def tearDown(self):
        patch.stopall()

    # --------------------------------------------------------
    # 页面运行辅助方法
    # --------------------------------------------------------

    def run_page(self):

        self.app = AppTest.from_file(
            str(PAGE_PATH)
        )

        self.app.run(timeout=15)

        return self.app

    def get_widget(self, widgets, label):

        for widget in widgets:
            if widget.label == label:
                return widget

        self.fail(
            f"没有找到页面控件：{label}"
        )

    # --------------------------------------------------------
    # P-01 页面正常加载
    # --------------------------------------------------------

    def test_page_loads_successfully(self):

        app = self.run_page()

        self.assertEqual(
            len(app.exception),
            0,
        )

        self.assertGreater(
            len(app.get("html")),
            0,
            "??????? HTML ??",
        )

    # --------------------------------------------------------
    # P-02 页面展示测试点详情
    # --------------------------------------------------------

    def test_page_displays_test_point_details(self):

        app = self.run_page()

        self.assertEqual(
            len(app.exception),
            0,
        )

        # 验证页面存在测试点详情区域
        headers = [
            item.value
            for item in app.subheader
        ]

        self.assertIn(
            "测试点详情",
            headers,
        )

        # 验证测试点选择控件存在
        point_selector = self.get_widget(
            app.selectbox,
            "选择要查看的测试点",
        )

        # 验证测试点编号出现在选择选项中
        self.assertTrue(
            any(
                "TP-001" in str(option)
                for option in point_selector.options
            )
        )

    # --------------------------------------------------------
    # P-03 未删除测试点显示编辑表单
    # --------------------------------------------------------

    def test_active_test_point_displays_edit_form(self):

        self.test_point = make_test_point(
            is_deleted=False
        )

        app = self.run_page()

        self.assertEqual(
            len(app.exception),
            0,
        )

        title_input = self.get_widget(
            app.text_input,
            "测试点标题",
        )

        self.assertEqual(
            title_input.value,
            "玩家正常登录",
        )

    # --------------------------------------------------------
    # P-04 已删除测试点不显示编辑表单
    # --------------------------------------------------------

    def test_deleted_test_point_cannot_be_edited(self):

        self.test_point = make_test_point(
            is_deleted=True
        )

        app = self.run_page()

        self.assertEqual(
            len(app.exception),
            0,
        )

        warning_messages = [
            item.value
            for item in app.warning
        ]

        self.assertTrue(
            any(
                "已逻辑删除" in message
                for message in warning_messages
            )
        )

        self.assertFalse(
            any(
                item.label == "测试点标题"
                for item in app.text_input
            )
        )

    # --------------------------------------------------------
    # P-05 合法编辑内容调用 Service
    # --------------------------------------------------------

    def test_submit_valid_edit_calls_service(self):

        app = self.run_page()

        title_input = self.get_widget(
            app.text_input,
            "测试点标题",
        )

        title_input.set_value(
            "修改后的测试点标题"
        )

        submit_button = self.get_widget(
            app.button,
            "保存测试点修改",
        )

        submit_button.click()

        app.run(timeout=15)

        self.mock_edit.assert_called_once()

        args = self.mock_edit.call_args.args

        self.assertEqual(
            args[0],
            "test-point-uuid-001",
        )

        self.assertIsInstance(
            args[1],
            TestPointEditableContent,
        )

        self.assertEqual(
            args[1].title,
            "修改后的测试点标题",
        )

        self.assertEqual(
            len(app.exception),
            0,
        )

    # --------------------------------------------------------
    # P-06 空标题被校验拦截
    # --------------------------------------------------------

    def test_empty_title_is_rejected(self):

        app = self.run_page()

        title_input = self.get_widget(
            app.text_input,
            "测试点标题",
        )

        title_input.set_value("")

        submit_button = self.get_widget(
            app.button,
            "保存测试点修改",
        )

        submit_button.click()

        app.run(timeout=15)

        self.mock_edit.assert_not_called()

        error_messages = [
            item.value
            for item in app.error
        ]

        self.assertTrue(
            any(
                "校验失败" in message
                for message in error_messages
            )
        )

    # --------------------------------------------------------
    # P-07 Service 异常反馈
    # --------------------------------------------------------

    def test_service_exception_is_displayed(self):

        self.mock_edit.side_effect = RuntimeError(
            "模拟编辑服务异常"
        )

        app = self.run_page()

        title_input = self.get_widget(
            app.text_input,
            "测试点标题",
        )

        title_input.set_value(
            "修改后的标题"
        )

        submit_button = self.get_widget(
            app.button,
            "保存测试点修改",
        )

        submit_button.click()

        app.run(timeout=15)

        error_messages = [
            item.value
            for item in app.error
        ]

        self.assertTrue(
            any(
                "模拟编辑服务异常" in message
                for message in error_messages
            )
        )

    # --------------------------------------------------------
    # P-08 编辑成功反馈
    # --------------------------------------------------------

    def test_successful_edit_displays_success_message(self):

        app = self.run_page()

        title_input = self.get_widget(
            app.text_input,
            "测试点标题",
        )

        title_input.set_value(
            "成功修改后的标题"
        )

        submit_button = self.get_widget(
            app.button,
            "保存测试点修改",
        )

        submit_button.click()

        app.run(timeout=15)

        success_messages = [
            item.value
            for item in app.success
        ]

        self.assertTrue(
            any(
                "测试点编辑成功" in message
                for message in success_messages
            )
        )

        self.assertEqual(
            len(app.exception),
            0,
        )


if __name__ == "__main__":
    unittest.main()
