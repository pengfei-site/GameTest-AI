
import json
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from database.repositories import test_point_repository as repository


class TestTestPointRepository(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"

        self._create_test_database()

        self.connection_patcher = patch.object(
            repository,
            "get_connection",
            self._get_test_connection,
        )
        self.connection_patcher.start()

        self.original_content = self._valid_content(
            title="有效账号登录测试点",
        )
        self.original_content["point_id"] = "TP-001"

        self._insert_test_point()

    def tearDown(self):
        self.connection_patcher.stop()
        self.temp_dir.cleanup()

    # ============================================================
    # 测试数据
    # ============================================================

    def _valid_content(self, **overrides):
        content = {
            "requirement_id": "REQ-001",
            "category": "positive",
            "title": "有效账号登录测试点",
            "test_objective": "验证有效账号可以成功登录",
            "coverage_description": "覆盖有效账号和正确密码的登录场景",
            "priority": "P0",
            "source_rule": "用户使用有效账号和正确密码可以登录",
        }
        content.update(overrides)
        return content

    def _create_test_database(self):
        """创建隔离测试数据库及必要的数据表。"""

        conn = sqlite3.connect(self.db_path)

        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE generation_batches (
                id TEXT PRIMARY KEY
            );

            CREATE TABLE test_points (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                point_id TEXT NOT NULL,
                original_content TEXT NOT NULL,
                current_content TEXT NOT NULL,

                ai_review_status TEXT NOT NULL DEFAULT 'not_reviewed'
                    CHECK (
                        ai_review_status IN (
                            'not_reviewed',
                            'approved',
                            'needs_review'
                        )
                    ),

                manual_review_status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        manual_review_status IN (
                            'pending',
                            'approved',
                            'rejected'
                        )
                    ),

                manual_comment TEXT DEFAULT '',
                reviewed_at TEXT,

                is_deleted INTEGER NOT NULL DEFAULT 0
                    CHECK (is_deleted IN (0, 1)),

                deleted_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (batch_id)
                    REFERENCES generation_batches(id)
                    ON DELETE RESTRICT,

                UNIQUE (batch_id, point_id)
            );

            CREATE TABLE test_point_history (
                id TEXT PRIMARY KEY,
                test_point_id TEXT NOT NULL,
                batch_id TEXT NOT NULL,

                action_type TEXT NOT NULL
                    CHECK (
                        action_type IN (
                            'created',
                            'edited',
                            'approved',
                            'rejected',
                            'deleted',
                            'restored',
                            'batch_approved',
                            'batch_rejected'
                        )
                    ),

                before_data TEXT,
                after_data TEXT,
                comment TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (test_point_id)
                    REFERENCES test_points(id)
                    ON DELETE RESTRICT,

                FOREIGN KEY (batch_id)
                    REFERENCES generation_batches(id)
                    ON DELETE RESTRICT
            );

            INSERT INTO generation_batches (id)
            VALUES ('batch-1');
            """
        )

        conn.commit()
        conn.close()

    @contextmanager
    def _get_test_connection(self, *, write=False):
        """提供临时数据库连接，模拟项目连接接口。"""

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

    def _insert_test_point(
        self,
        *,
        test_point_id="test-point-1",
        point_id="TP-001",
        current_content=None,
        ai_review_status="not_reviewed",
        manual_review_status="pending",
        manual_comment="",
        reviewed_at=None,
        is_deleted=0,
        deleted_at=None,
    ):
        """插入测试点数据。"""

        original = dict(self.original_content)
        original["point_id"] = point_id

        current = (
            dict(current_content)
            if current_content is not None
            else dict(original)
        )

        current["point_id"] = point_id

        with self._get_test_connection() as conn:
            conn.execute(
                """
                INSERT INTO test_points (
                    id,
                    batch_id,
                    point_id,
                    original_content,
                    current_content,
                    ai_review_status,
                    manual_review_status,
                    manual_comment,
                    reviewed_at,
                    is_deleted,
                    deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_point_id,
                    "batch-1",
                    point_id,
                    json.dumps(original, ensure_ascii=False),
                    json.dumps(current, ensure_ascii=False),
                    ai_review_status,
                    manual_review_status,
                    manual_comment,
                    reviewed_at,
                    is_deleted,
                    deleted_at,
                ),
            )

    def _edit(self, content=None, test_point_id="test-point-1"):
        """执行编辑操作。"""

        if content is None:
            content = self._valid_content(
                title="修改后的测试点标题",
            )

        return repository.edit_test_point(
            test_point_id,
            content,
        )

    def _get_test_point_row(self, test_point_id="test-point-1"):
        with self._get_test_connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM test_points
                WHERE id = ?
                """,
                (test_point_id,),
            ).fetchone()

    def _get_history(self, test_point_id="test-point-1"):
        with self._get_test_connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM test_point_history
                WHERE test_point_id = ?
                ORDER BY created_at
                """,
                (test_point_id,),
            ).fetchall()

    # ============================================================
    # R-01：正常编辑
    # ============================================================

    def test_R01_normal_edit(self):
        """正常编辑应成功更新 current_content。"""

        new_content = self._valid_content(
            title="修改后的测试点标题",
            priority="P1",
        )

        repository.edit_test_point(
            "test-point-1",
            new_content,
        )

        row = self._get_test_point_row()
        current = json.loads(row["current_content"])

        self.assertEqual(
            current["title"],
            "修改后的测试点标题",
        )
        self.assertEqual(current["priority"], "P1")
        self.assertEqual(
            row["manual_review_status"],
            "pending",
        )

        history = self._get_history()

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_type"], "edited")

    # ============================================================
    # R-02：禁止修改 point_id
    # ============================================================

    def test_R02_point_id_is_not_editable(self):
        """提交 point_id 应被专用模型拒绝。"""

        content = self._valid_content()
        content["point_id"] = "TP-999"

        with self.assertRaises(ValidationError):
            self._edit(content)

        row = self._get_test_point_row()

        self.assertEqual(row["point_id"], "TP-001")
        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-03：禁止额外字段
    # ============================================================

    def test_R03_extra_field_is_rejected(self):
        """提交未定义的额外字段应被拒绝。"""

        content = self._valid_content()
        content["unknown_field"] = "unexpected"

        with self.assertRaises(ValidationError):
            self._edit(content)

        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-04：标题不能为空
    # ============================================================

    def test_R04_empty_title_is_rejected(self):
        """标题为空白字符时应被拒绝。"""

        content = self._valid_content(title="   ")

        with self.assertRaises(ValidationError):
            self._edit(content)

        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-05：category 必须合法
    # ============================================================

    def test_R05_invalid_category_is_rejected(self):
        """非法 category 应被拒绝。"""

        content = self._valid_content(
            category="invalid_category",
        )

        with self.assertRaises(ValidationError):
            self._edit(content)

        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-06：priority 必须合法
    # ============================================================

    def test_R06_invalid_priority_is_rejected(self):
        """非法 priority 应被拒绝。"""

        content = self._valid_content(
            priority="P5",
        )

        with self.assertRaises(ValidationError):
            self._edit(content)

        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-07：禁止直接编辑已删除测试点
    # ============================================================

    def test_R07_deleted_test_point_cannot_be_edited(self):
        """已删除测试点应先恢复再编辑。"""

        with self._get_test_connection() as conn:
            conn.execute(
                """
                UPDATE test_points
                SET is_deleted = 1,
                    deleted_at = '2026-01-01 10:00:00'
                WHERE id = ?
                """,
                ("test-point-1",),
            )

        with self.assertRaises(ValueError):
            self._edit()

        row = self._get_test_point_row()

        self.assertEqual(row["is_deleted"], 1)
        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-08：不存在的测试点
    # ============================================================

    def test_R08_nonexistent_test_point(self):
        """编辑不存在的测试点应抛出 ValueError。"""

        with self.assertRaises(ValueError):
            self._edit(
                self._valid_content(),
                test_point_id="not-exists",
            )

        self.assertEqual(len(self._get_history()), 0)

    # ============================================================
    # R-09：original_content 不允许被修改
    # ============================================================

    def test_R09_original_content_remains_unchanged(self):
        """编辑前后的 original_content 必须完全一致。"""

        before = self._get_test_point_row()
        original_before = before["original_content"]

        self._edit(
            self._valid_content(
                title="全新标题",
                priority="P2",
            )
        )

        after = self._get_test_point_row()

        self.assertEqual(
            after["original_content"],
            original_before,
        )

    # ============================================================
    # R-10：point_id 不允许被修改
    # ============================================================

    def test_R10_point_id_remains_unchanged(self):
        """编辑后 point_id 必须保持原值。"""

        self._edit()

        row = self._get_test_point_row()

        self.assertEqual(row["point_id"], "TP-001")

        current = json.loads(row["current_content"])

        self.assertEqual(
            current["point_id"],
            "TP-001",
        )

    # ============================================================
    # R-11：人工审核状态重置
    # ============================================================

    def test_R11_manual_review_status_is_reset(self):
        """编辑后人工审核状态应重置为 pending。"""

        with self._get_test_connection() as conn:
            conn.execute(
                """
                UPDATE test_points
                SET manual_review_status = 'approved',
                    manual_comment = '原审核意见',
                    reviewed_at = '2026-01-01 10:00:00'
                WHERE id = ?
                """,
                ("test-point-1",),
            )

        self._edit()

        row = self._get_test_point_row()

        self.assertEqual(
            row["manual_review_status"],
            "pending",
        )
        self.assertEqual(row["manual_comment"], "")
        self.assertIsNone(row["reviewed_at"])

    # ============================================================
    # R-12：AI 审核状态保留
    # ============================================================

    def test_R12_ai_review_status_is_preserved(self):
        """编辑后 AI 审核状态应保持不变。"""

        with self._get_test_connection() as conn:
            conn.execute(
                """
                UPDATE test_points
                SET ai_review_status = 'needs_review'
                WHERE id = ?
                """,
                ("test-point-1",),
            )

        self._edit()

        row = self._get_test_point_row()

        self.assertEqual(
            row["ai_review_status"],
            "needs_review",
        )

    # ============================================================
    # R-13：历史快照完整
    # ============================================================

    def test_R13_history_snapshot_is_complete(self):
        """编辑历史必须保存完整的前后数据快照。"""

        with self._get_test_connection() as conn:
            conn.execute(
                """
                UPDATE test_points
                SET ai_review_status = 'needs_review',
                    manual_review_status = 'rejected',
                    manual_comment = '原审核意见',
                    reviewed_at = '2026-01-01 10:00:00'
                WHERE id = ?
                """,
                ("test-point-1",),
            )

        before_row = self._get_test_point_row()

        expected_before = {
            "point_id": before_row["point_id"],
            "original_content": json.loads(
                before_row["original_content"]
            ),
            "current_content": json.loads(
                before_row["current_content"]
            ),
            "ai_review_status": before_row["ai_review_status"],
            "manual_review_status": before_row[
                "manual_review_status"
            ],
            "manual_comment": before_row["manual_comment"],
            "reviewed_at": before_row["reviewed_at"],
            "is_deleted": before_row["is_deleted"],
            "deleted_at": before_row["deleted_at"],
        }

        new_content = self._valid_content(
            title="历史快照测试：修改后标题",
            priority="P1",
        )

        repository.edit_test_point(
            "test-point-1",
            new_content,
        )

        history = self._get_history()

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_type"], "edited")

        before_data = json.loads(history[0]["before_data"])
        after_data = json.loads(history[0]["after_data"])

        self.assertEqual(before_data, expected_before)

        expected_after = {
            "point_id": "TP-001",
            "original_content": expected_before["original_content"],
            "current_content": {
                **new_content,
                "point_id": "TP-001",
            },
            "ai_review_status": "needs_review",
            "manual_review_status": "pending",
            "manual_comment": "",
            "reviewed_at": None,
            "is_deleted": 0,
            "deleted_at": None,
        }

        self.assertEqual(after_data, expected_after)

        # 确认历史记录的基本元数据
        self.assertEqual(
            history[0]["test_point_id"],
            "test-point-1",
        )
        self.assertEqual(history[0]["batch_id"], "batch-1")
        self.assertTrue(history[0]["comment"])

    # ============================================================
    # R-14：历史写入失败时整体回滚
    # ============================================================

    def test_R14_history_insert_failure_rolls_back_edit(self):
        """历史记录写入失败时，测试点编辑也必须回滚。"""

        before_row = self._get_test_point_row()

        before_current_content = before_row["current_content"]
        before_manual_status = before_row["manual_review_status"]
        before_manual_comment = before_row["manual_comment"]
        before_reviewed_at = before_row["reviewed_at"]
        before_updated_at = before_row["updated_at"]

        with self._get_test_connection() as conn:
            conn.execute(
                """
                UPDATE test_points
                SET manual_review_status = 'approved',
                    manual_comment = '回滚测试原审核意见',
                    reviewed_at = '2026-01-01 10:00:00'
                WHERE id = ?
                """,
                ("test-point-1",),
            )

            conn.execute(
                """
                CREATE TRIGGER fail_test_point_history_insert
                BEFORE INSERT ON test_point_history
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        '模拟历史记录写入失败'
                    );
                END;
                """
            )

        before_row = self._get_test_point_row()

        before_current_content = before_row["current_content"]
        before_manual_status = before_row["manual_review_status"]
        before_manual_comment = before_row["manual_comment"]
        before_reviewed_at = before_row["reviewed_at"]
        before_updated_at = before_row["updated_at"]

        new_content = self._valid_content(
            title="这次编辑不应该保存",
        )

        with self.assertRaises(sqlite3.IntegrityError):
            repository.edit_test_point(
                "test-point-1",
                new_content,
            )

        after_row = self._get_test_point_row()

        # UPDATE 必须回滚
        self.assertEqual(
            after_row["current_content"],
            before_current_content,
        )
        self.assertEqual(
            after_row["manual_review_status"],
            before_manual_status,
        )
        self.assertEqual(
            after_row["manual_comment"],
            before_manual_comment,
        )
        self.assertEqual(
            after_row["reviewed_at"],
            before_reviewed_at,
        )
        self.assertEqual(
            after_row["updated_at"],
            before_updated_at,
        )

        # 历史记录不得留下部分数据
        self.assertEqual(len(self._get_history()), 0)


    # ============================================================
    # STEP 11.2.5：人工审核 Repository 测试
    # ============================================================

    def _insert_second_test_point(
        self,
        *,
        test_point_id="test-point-2",
        point_id="TP-002",
        batch_id="batch-1",
        ai_review_status="not_reviewed",
        manual_review_status="pending",
        is_deleted=0,
    ):
        """插入同批次或指定批次的第二条测试点。"""

        with self._get_test_connection() as conn:
            if batch_id != "batch-1":
                conn.execute(
                    "INSERT OR IGNORE INTO generation_batches (id) VALUES (?)",
                    (batch_id,),
                )

            content = self._valid_content(title=f"{point_id} 测试点")
            content["point_id"] = point_id

            conn.execute(
                """
                INSERT INTO test_points (
                    id, batch_id, point_id,
                    original_content, current_content,
                    ai_review_status, manual_review_status,
                    is_deleted
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_point_id,
                    batch_id,
                    point_id,
                    json.dumps(content, ensure_ascii=False),
                    json.dumps(content, ensure_ascii=False),
                    ai_review_status,
                    manual_review_status,
                    is_deleted,
                ),
            )

    def _get_all_history(self):
        with self._get_test_connection() as conn:
            return conn.execute(
                """
                SELECT *
                FROM test_point_history
                ORDER BY created_at, rowid
                """
            ).fetchall()

    def _create_history_failure_trigger(self):
        with self._get_test_connection() as conn:
            conn.execute(
                """
                CREATE TRIGGER fail_test_point_history_insert
                BEFORE INSERT ON test_point_history
                BEGIN
                    SELECT RAISE(ABORT, '模拟历史记录写入失败');
                END;
                """
            )

    # R-15：单条审核通过，允许空意见
    def test_R15_single_approve_allows_empty_comment(self):
        result = repository.approve_test_point("test-point-1")

        row = self._get_test_point_row()
        history = self._get_history()

        self.assertEqual(result["manual_review_status"], "approved")
        self.assertEqual(row["manual_review_status"], "approved")
        self.assertEqual(row["manual_comment"], "")
        self.assertIsNotNone(row["reviewed_at"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_type"], "approved")
        self.assertEqual(history[0]["comment"], "")

        before_data = json.loads(history[0]["before_data"])
        after_data = json.loads(history[0]["after_data"])
        self.assertEqual(before_data["manual_review_status"], "pending")
        self.assertEqual(after_data["manual_review_status"], "approved")

    # R-16：单条驳回成功，原因去除首尾空格
    def test_R16_single_reject_strips_reason(self):
        result = repository.reject_test_point(
            "test-point-1",
            "  缺少异常流程覆盖  ",
        )

        row = self._get_test_point_row()
        history = self._get_history()

        self.assertEqual(result["manual_review_status"], "rejected")
        self.assertEqual(row["manual_review_status"], "rejected")
        self.assertEqual(row["manual_comment"], "缺少异常流程覆盖")
        self.assertIsNotNone(row["reviewed_at"])
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["action_type"], "rejected")
        self.assertEqual(history[0]["comment"], "缺少异常流程覆盖")

    # R-17：空驳回原因被拒绝
    def test_R17_empty_reject_reason_is_rejected(self):
        for reason in ("", "   ", "\t\n"):
            with self.subTest(reason=repr(reason)):
                with self.assertRaises(ValueError):
                    repository.reject_test_point("test-point-1", reason)

        row = self._get_test_point_row()
        self.assertEqual(row["manual_review_status"], "pending")
        self.assertEqual(len(self._get_history()), 0)

    # R-18：不存在的测试点不能审核
    def test_R18_nonexistent_test_point_cannot_be_reviewed(self):
        with self.assertRaisesRegex(ValueError, "测试点不存在"):
            repository.approve_test_point("not-exists")

        self.assertEqual(len(self._get_history()), 0)

    # R-19：已删除测试点不能审核
    def test_R19_deleted_test_point_cannot_be_reviewed(self):
        with self._get_test_connection() as conn:
            conn.execute(
                "UPDATE test_points SET is_deleted = 1 WHERE id = ?",
                ("test-point-1",),
            )

        with self.assertRaisesRegex(ValueError, "已删除"):
            repository.approve_test_point("test-point-1")

        row = self._get_test_point_row()
        self.assertEqual(row["manual_review_status"], "pending")
        self.assertEqual(len(self._get_history()), 0)

    # R-20：已通过的测试点不能重复审核
    def test_R20_approved_test_point_cannot_be_reviewed_again(self):
        repository.approve_test_point("test-point-1", "首次通过")
        history_before = len(self._get_history())
        row_before = dict(self._get_test_point_row())

        with self.assertRaisesRegex(ValueError, "只有待审核"):
            repository.reject_test_point("test-point-1", "再次驳回")

        row_after = self._get_test_point_row()
        self.assertEqual(row_after["manual_review_status"], row_before["manual_review_status"])
        self.assertEqual(row_after["manual_comment"], row_before["manual_comment"])
        self.assertEqual(row_after["reviewed_at"], row_before["reviewed_at"])
        self.assertEqual(len(self._get_history()), history_before)

    # R-21：已驳回的测试点不能重复审核
    def test_R21_rejected_test_point_cannot_be_reviewed_again(self):
        repository.reject_test_point("test-point-1", "首次驳回")
        history_before = len(self._get_history())
        row_before = dict(self._get_test_point_row())

        with self.assertRaisesRegex(ValueError, "只有待审核"):
            repository.approve_test_point("test-point-1", "再次通过")

        row_after = self._get_test_point_row()
        self.assertEqual(row_after["manual_review_status"], row_before["manual_review_status"])
        self.assertEqual(row_after["manual_comment"], row_before["manual_comment"])
        self.assertEqual(row_after["reviewed_at"], row_before["reviewed_at"])
        self.assertEqual(len(self._get_history()), history_before)

    # R-22：AI 审核未通过仍允许人工审核
    def test_R22_ai_needs_review_does_not_block_manual_approval(self):
        with self._get_test_connection() as conn:
            conn.execute(
                "UPDATE test_points SET ai_review_status = 'needs_review' WHERE id = ?",
                ("test-point-1",),
            )

        result = repository.approve_test_point("test-point-1")

        row = self._get_test_point_row()
        self.assertEqual(result["manual_review_status"], "approved")
        self.assertEqual(row["ai_review_status"], "needs_review")
        self.assertEqual(row["manual_review_status"], "approved")

    # R-23：单条审核历史写入失败时整体回滚
    def test_R23_single_review_history_failure_rolls_back(self):
        before = dict(self._get_test_point_row())
        self._create_history_failure_trigger()

        with self.assertRaises(sqlite3.IntegrityError):
            repository.approve_test_point("test-point-1", "应回滚")

        after = self._get_test_point_row()
        self.assertEqual(after["manual_review_status"], before["manual_review_status"])
        self.assertEqual(after["manual_comment"], before["manual_comment"])
        self.assertEqual(after["reviewed_at"], before["reviewed_at"])
        self.assertEqual(after["updated_at"], before["updated_at"])
        self.assertEqual(len(self._get_history()), 0)

    # R-24：批量审核通过成功
    def test_R24_batch_approve_success(self):
        self._insert_second_test_point()

        results = repository.batch_approve_test_points(
            ["test-point-1", "test-point-2"],
            "批量通过",
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(
            {item["manual_review_status"] for item in results},
            {"approved"},
        )

        rows = [
            self._get_test_point_row("test-point-1"),
            self._get_test_point_row("test-point-2"),
        ]
        self.assertTrue(all(row["manual_review_status"] == "approved" for row in rows))

        history = self._get_all_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(
            [item["action_type"] for item in history],
            ["batch_approved", "batch_approved"],
        )
        self.assertTrue(all(item["comment"] == "批量通过" for item in history))

    # R-25：批量驳回成功
    def test_R25_batch_reject_success(self):
        self._insert_second_test_point()

        results = repository.batch_reject_test_points(
            ["test-point-1", "test-point-2"],
            "  缺少边界条件  ",
        )

        self.assertEqual(len(results), 2)
        rows = [
            self._get_test_point_row("test-point-1"),
            self._get_test_point_row("test-point-2"),
        ]
        self.assertTrue(all(row["manual_review_status"] == "rejected" for row in rows))
        self.assertTrue(all(row["manual_comment"] == "缺少边界条件" for row in rows))

        history = self._get_all_history()
        self.assertEqual(len(history), 2)
        self.assertTrue(all(item["action_type"] == "batch_rejected" for item in history))
        self.assertTrue(all(item["comment"] == "缺少边界条件" for item in history))

    # R-26：批量审核参数校验
    def test_R26_batch_review_rejects_invalid_id_lists(self):
        invalid_cases = [
            [],
            [""],
            ["   "],
            ["test-point-1", "test-point-1"],
        ]

        for ids in invalid_cases:
            with self.subTest(ids=ids):
                with self.assertRaises(ValueError):
                    repository.batch_approve_test_points(ids)

        with self.assertRaises(ValueError):
            repository.batch_reject_test_points(["test-point-1"], "  ")

        row = self._get_test_point_row()
        self.assertEqual(row["manual_review_status"], "pending")
        self.assertEqual(len(self._get_history()), 0)

    # R-27：不存在的 ID 导致整批失败
    def test_R27_batch_review_nonexistent_id_rolls_back_all(self):
        self._insert_second_test_point()

        with self.assertRaisesRegex(ValueError, "不存在"):
            repository.batch_approve_test_points(
                ["test-point-1", "missing-point"],
            )

        for point_id in ("test-point-1", "test-point-2"):
            self.assertEqual(
                self._get_test_point_row(point_id)["manual_review_status"],
                "pending",
            )
        self.assertEqual(len(self._get_all_history()), 0)

    # R-28：跨批次测试点不能批量审核
    def test_R28_batch_review_rejects_different_batches(self):
        self._insert_second_test_point(batch_id="batch-2")

        with self.assertRaisesRegex(ValueError, "同一个生成批次"):
            repository.batch_approve_test_points(
                ["test-point-1", "test-point-2"],
            )

        for point_id in ("test-point-1", "test-point-2"):
            self.assertEqual(
                self._get_test_point_row(point_id)["manual_review_status"],
                "pending",
            )
        self.assertEqual(len(self._get_all_history()), 0)

    # R-29：已删除成员导致整批失败
    def test_R29_batch_review_rejects_deleted_member(self):
        self._insert_second_test_point(is_deleted=1)

        with self.assertRaisesRegex(ValueError, "已删除"):
            repository.batch_approve_test_points(
                ["test-point-1", "test-point-2"],
            )

        self.assertEqual(
            self._get_test_point_row("test-point-1")["manual_review_status"],
            "pending",
        )
        self.assertEqual(
            self._get_test_point_row("test-point-2")["manual_review_status"],
            "pending",
        )
        self.assertEqual(len(self._get_all_history()), 0)

    # R-30：非 pending 成员导致整批失败
    def test_R30_batch_review_rejects_non_pending_member(self):
        self._insert_second_test_point(manual_review_status="approved")

        with self.assertRaisesRegex(ValueError, "不是待审核"):
            repository.batch_approve_test_points(
                ["test-point-1", "test-point-2"],
            )

        self.assertEqual(
            self._get_test_point_row("test-point-1")["manual_review_status"],
            "pending",
        )
        self.assertEqual(
            self._get_test_point_row("test-point-2")["manual_review_status"],
            "approved",
        )
        self.assertEqual(len(self._get_all_history()), 0)

    # R-31：批量历史写入失败时整批回滚
    def test_R31_batch_history_failure_rolls_back_all(self):
        self._insert_second_test_point()
        before_rows = {
            point_id: dict(self._get_test_point_row(point_id))
            for point_id in ("test-point-1", "test-point-2")
        }
        self._create_history_failure_trigger()

        with self.assertRaises(sqlite3.IntegrityError):
            repository.batch_approve_test_points(
                ["test-point-1", "test-point-2"],
                "整批应回滚",
            )

        for point_id, before in before_rows.items():
            after = self._get_test_point_row(point_id)
            self.assertEqual(after["manual_review_status"], before["manual_review_status"])
            self.assertEqual(after["manual_comment"], before["manual_comment"])
            self.assertEqual(after["reviewed_at"], before["reviewed_at"])
            self.assertEqual(after["updated_at"], before["updated_at"])

        self.assertEqual(len(self._get_all_history()), 0)


if __name__ == "__main__":
    unittest.main()
