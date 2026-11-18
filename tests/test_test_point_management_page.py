"""测试点管理页面人工审核功能自动化测试。"""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGE_PATH = PROJECT_ROOT / "pages" / "08_测试点列表.py"


def make_test_point(
    point_id="test-point-uuid-001",
    manual_review_status="pending",
    is_deleted=False,
):
    return {
        "id": point_id,
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
        "ai_review_status": "failed",
        "manual_review_status": manual_review_status,
        "manual_comment": "",
        "reviewed_at": None,
        "is_deleted": 1 if is_deleted else 0,
        "deleted_at": "2026-11-01 10:00:00" if is_deleted else None,
        "created_at": "2026-11-01 09:00:00",
        "updated_at": "2026-11-01 09:00:00",
    }


class TestTestPointManagementReviewPage(unittest.TestCase):

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

        self.patches = [
            patch(
                "database.repositories.project_repository.list_projects",
                return_value=self.projects,
            ),
            patch(
                "database.repositories.generation_batch_repository.list_generation_batches",
                return_value=self.batches,
            ),
            patch(
                "database.repositories.generation_batch_repository.get_generation_batch",
                return_value=self.batches[0],
            ),
            patch(
                "database.repositories.test_point_repository.list_test_points",
                side_effect=lambda *args, **kwargs: [self.test_point],
            ),
            patch(
                "database.repositories.test_point_repository.get_test_point",
                side_effect=lambda point_id: self.test_point,
            ),
            patch(
                "database.repositories.test_point_repository.list_test_point_history",
                return_value=[],
            ),
            patch(
                "core.testpoint_review_service.approve_test_point",
                return_value={
                    "success": True,
                    "test_point_id": "test-point-uuid-001",
                    "manual_review_status": "approved",
                    "message": "审核通过",
                },
            ),
            patch(
                "core.testpoint_review_service.reject_test_point",
                return_value={
                    "success": True,
                    "test_point_id": "test-point-uuid-001",
                    "manual_review_status": "rejected",
                    "message": "审核驳回",
                },
            ),
            patch(
                "core.testpoint_review_service.batch_approve_test_points",
                return_value={
                    "success": True,
                    "test_point_ids": ["test-point-uuid-001"],
                    "count": 1,
                    "manual_review_status": "approved",
                    "message": "批量通过",
                },
            ),
            patch(
                "core.testpoint_review_service.batch_reject_test_points",
                return_value={
                    "success": True,
                    "test_point_ids": ["test-point-uuid-001"],
                    "count": 1,
                    "manual_review_status": "rejected",
                    "message": "批量驳回",
                },
            ),
        ]

        self.mocks = [item.start() for item in self.patches]
        (
            self.mock_list_projects,
            self.mock_list_batches,
            self.mock_get_batch,
            self.mock_list_points,
            self.mock_get_point,
            self.mock_list_history,
            self.mock_approve,
            self.mock_reject,
            self.mock_batch_approve,
            self.mock_batch_reject,
        ) = self.mocks

    def tearDown(self):
        patch.stopall()

    def run_page(self):
        app = AppTest.from_file(str(PAGE_PATH))
        app.run(timeout=20)
        return app

    @staticmethod
    def get_widget(widgets, label):
        for widget in widgets:
            if widget.label == label:
                return widget
        raise AssertionError(f"没有找到页面控件：{label}")

    def test_page_loads_and_shows_review_actions(self):
        app = self.run_page()

        self.assertEqual(len(app.exception), 0)
        self.assertGreater(
            len(app.get("html")),
            0,
            "??????? HTML ??",
        )
        self.get_widget(app.button, "审核通过")
        self.get_widget(app.button, "驳回测试点")

    def test_single_approve_calls_review_service(self):
        app = self.run_page()

        self.get_widget(app.button, "审核通过").click()
        app.run(timeout=20)

        self.mock_approve.assert_called_once_with(
            "test-point-uuid-001",
            "",
        )
        self.assertEqual(len(app.exception), 0)

    def test_single_approve_passes_optional_comment(self):
        app = self.run_page()

        self.get_widget(app.text_input, "通过意见（可选）").set_value(
            "检查通过"
        )
        self.get_widget(app.button, "审核通过").click()
        app.run(timeout=20)

        self.mock_approve.assert_called_once_with(
            "test-point-uuid-001",
            "检查通过",
        )

    def test_single_reject_requires_reason(self):
        app = self.run_page()

        self.get_widget(app.button, "驳回测试点").click()
        app.run(timeout=20)

        self.mock_reject.assert_not_called()
        self.assertTrue(
            any("驳回原因不能为空" in item.value for item in app.error)
        )

    def test_single_reject_calls_service_with_reason(self):
        app = self.run_page()

        self.get_widget(
            app.text_area,
            "驳回原因（必填）",
        ).set_value("测试点覆盖范围不完整")
        self.get_widget(app.button, "驳回测试点").click()
        app.run(timeout=20)

        self.mock_reject.assert_called_once_with(
            "test-point-uuid-001",
            "测试点覆盖范围不完整",
        )

    def test_deleted_point_has_no_review_buttons(self):
        self.test_point = make_test_point(is_deleted=True)
        app = self.run_page()

        self.assertEqual(len(app.exception), 0)
        self.assertFalse(
            any(item.label == "审核通过" for item in app.button)
        )
        self.assertFalse(
            any(item.label == "驳回测试点" for item in app.button)
        )
        self.mock_approve.assert_not_called()
        self.mock_reject.assert_not_called()

    def test_non_pending_point_has_no_single_review_buttons(self):
        self.test_point = make_test_point(
            manual_review_status="approved"
        )
        app = self.run_page()

        self.assertFalse(
            any(item.label == "审核通过" for item in app.button)
        )
        self.assertFalse(
            any(item.label == "驳回测试点" for item in app.button)
        )

    def test_batch_approve_requires_selection(self):
        app = self.run_page()

        self.get_widget(app.button, "批量通过").click()
        app.run(timeout=20)

        self.mock_batch_approve.assert_not_called()
        self.assertTrue(
            any("请至少选择一条待审核测试点" in item.value for item in app.error)
        )

    def test_batch_approve_calls_service(self):
        app = self.run_page()

        selector = self.get_widget(
            app.multiselect,
            "选择待审核测试点",
        )
        selector.select("test-point-uuid-001")
        app.run(timeout=20)

        self.get_widget(app.button, "批量通过").click()
        app.run(timeout=20)

        self.mock_batch_approve.assert_called_once_with(
            ["test-point-uuid-001"],
            "",
        )

    def test_batch_reject_requires_reason(self):
        app = self.run_page()

        self.get_widget(
            app.multiselect,
            "选择待审核测试点",
        ).select("test-point-uuid-001")
        app.run(timeout=20)

        self.get_widget(app.button, "批量驳回").click()
        app.run(timeout=20)

        self.mock_batch_reject.assert_not_called()
        self.assertTrue(
            any("批量驳回原因不能为空" in item.value for item in app.error)
        )

    def test_batch_reject_calls_service_with_reason(self):
        app = self.run_page()

        self.get_widget(
            app.multiselect,
            "选择待审核测试点",
        ).select("test-point-uuid-001")
        app.run(timeout=20)

        self.get_widget(
            app.text_area,
            "批量驳回原因（必填）",
        ).set_value("批次测试点需要补充异常场景")
        self.get_widget(app.button, "批量驳回").click()
        app.run(timeout=20)

        self.mock_batch_reject.assert_called_once_with(
            ["test-point-uuid-001"],
            "批次测试点需要补充异常场景",
        )


    def test_history_empty_state_is_shown(self):
        app = self.run_page()

        self.mock_list_history.assert_called_once_with("test-point-uuid-001")
        self.assertTrue(
            any("暂无操作历史记录" in item.value for item in app.info)
        )
        self.assertEqual(len(app.exception), 0)

    def test_history_shows_edit_before_and_after_snapshots(self):
        self.mock_list_history.return_value = [
            {
                "action_type": "edited",
                "created_at": "2026-11-02 10:00:00",
                "comment": "调整测试目标",
                "before_data": {"title": "旧标题"},
                "after_data": {"title": "新标题"},
            }
        ]
        app = self.run_page()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("编辑测试点" in item.label for item in app.expander))
        self.assertTrue(any("修改前快照" in item.value for item in app.subheader))
        self.assertTrue(any("修改后快照" in item.value for item in app.subheader))
        self.assertTrue(any("调整测试目标" in item.value for item in app.get("markdown")))

    def test_history_newest_operation_is_displayed_first(self):
        self.mock_list_history.return_value = [
            {
                "action_type": "created",
                "created_at": "2026-11-01 09:00:00",
                "comment": "较早创建",
                "before_data": None,
                "after_data": {"title": "初始标题"},
            },
            {
                "action_type": "edited",
                "created_at": "2026-11-02 10:00:00",
                "comment": "最新修改",
                "before_data": {"title": "旧标题"},
                "after_data": {"title": "新标题"},
            },
        ]
        app = self.run_page()

        self.assertEqual(len(app.exception), 0)
        history_expanders = [
            item
            for item in app.expander
            if "编辑测试点" in item.label or "创建测试点" in item.label
        ]
        self.assertEqual(len(history_expanders), 2)
        self.assertIn("编辑测试点", history_expanders[0].label)
        self.assertIn("创建测试点", history_expanders[1].label)
        self.assertTrue(
            any("倒序排列（最新记录在前）" in item.value for item in app.caption)
        )

    def test_history_query_error_is_shown_without_page_crash(self):
        self.mock_list_history.side_effect = RuntimeError("history unavailable")
        app = self.run_page()

        self.assertTrue(
            any("读取测试点操作历史失败" in item.value for item in app.error)
        )
        self.assertEqual(len(app.exception), 0)

    def test_history_unknown_action_type_is_supported(self):
        self.mock_list_history.return_value = [
            {
                "action_type": "future_action",
                "created_at": "2026-11-02 10:00:00",
                "comment": "未知操作",
                "before_data": None,
                "after_data": None,
            }
        ]
        app = self.run_page()

        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("其他操作（future_action）" in item.label for item in app.expander)
        )
        self.assertTrue(
            any("没有可展示的快照数据" in item.value for item in app.info)
        )

    def test_ai_failed_status_does_not_block_manual_approval(self):
        self.test_point["ai_review_status"] = "failed"
        app = self.run_page()

        self.get_widget(app.button, "审核通过").click()
        app.run(timeout=20)

        self.mock_approve.assert_called_once()


if __name__ == "__main__":
    unittest.main()
