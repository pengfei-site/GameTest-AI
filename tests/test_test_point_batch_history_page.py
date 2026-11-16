"""STEP 11.2.6.3.2：批次操作历史页面测试。"""

from streamlit.testing.v1 import AppTest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PAGE_PATH = PROJECT_ROOT / "pages" / "05_测试点批次管理.py"


def _history(
    history_id,
    action_type="created",
    point_uuid="uuid-1",
    point_label="TP-001",
    created_at="2026-11-15 10:00:00",
    before_data=None,
    after_data=None,
    comment="",
):
    return {
        "id": history_id,
        "test_point_id": point_uuid,
        "batch_id": "batch-1",
        "action_type": action_type,
        "before_data": before_data,
        "after_data": (
            after_data
            if after_data is not None
            else {"point_id": point_label}
        ),
        "comment": comment,
        "created_at": created_at,
    }


def _run_page(monkeypatch, history, history_error=None):
    import database.repositories.project_repository as project_repo
    import database.repositories.requirement_repository as requirement_repo
    import database.repositories.generation_batch_repository as batch_repo
    import database.repositories.test_point_repository as point_repo

    monkeypatch.setattr(
        project_repo,
        "list_projects",
        lambda: [{"id": "project-1", "name": "测试项目"}],
    )
    monkeypatch.setattr(
        requirement_repo,
        "list_requirement_analyses",
        lambda project_id: [],
    )
    monkeypatch.setattr(
        requirement_repo,
        "get_requirement_analysis",
        lambda analysis_id: None,
    )
    monkeypatch.setattr(
        batch_repo,
        "list_generation_batches",
        lambda project_id, requirement_analysis_id=None: [
            {
                "id": "batch-1",
                "generated_at": "2026-11-15 09:00:00",
                "final_status": "ready_for_manual_review",
                "requirement_analysis_id": None,
            }
        ],
    )
    monkeypatch.setattr(
        batch_repo,
        "get_generation_batch",
        lambda batch_id: {
            "id": "batch-1",
            "project_id": "project-1",
            "requirement_analysis_id": None,
            "generated_at": "2026-11-15 09:00:00",
            "final_status": "ready_for_manual_review",
            "validation_report": {},
            "review_report": {},
        },
    )
    monkeypatch.setattr(
        point_repo,
        "get_test_point_review_statistics",
        lambda batch_id: {
            "total": 1,
            "pending": 1,
            "approved": 0,
            "rejected": 0,
            "deleted": 0,
        },
    )
    monkeypatch.setattr(
        point_repo,
        "list_test_points",
        lambda batch_id: [
            {
                "id": "uuid-1",
                "point_id": "TP-001",
                "current_content": {"point_id": "TP-001"},
                "ai_review_status": "not_reviewed",
                "manual_review_status": "pending",
            }
        ],
    )

    def fake_history(batch_id):
        if history_error:
            raise RuntimeError(history_error)
        return history

    monkeypatch.setattr(
        point_repo,
        "list_batch_test_point_history",
        fake_history,
    )

    return AppTest.from_file(PAGE_PATH).run()


def test_batch_history_empty_state(monkeypatch):
    app = _run_page(monkeypatch, [])

    assert not app.exception
    assert any("该批次暂无操作历史记录" in item.value for item in app.info)


def test_batch_history_renders_action_and_snapshot(monkeypatch):
    history = [
        _history(
            "history-1",
            action_type="edited",
            before_data={"point_id": "TP-001", "value": "旧内容"},
            after_data={"point_id": "TP-001", "value": "新内容"},
            comment="人工编辑测试点",
        )
    ]

    app = _run_page(monkeypatch, history)

    assert not app.exception
    labels = [item.label for item in app.expander]
    assert any("编辑测试点" in label for label in labels)
    assert any("TP-001" in label for label in labels)


def test_batch_history_newest_record_is_first(monkeypatch):
    history = [
        _history(
            "history-old",
            action_type="created",
            created_at="2026-11-15 09:00:00",
        ),
        _history(
            "history-new",
            action_type="approved",
            created_at="2026-11-15 10:00:00",
        ),
    ]

    app = _run_page(monkeypatch, history)

    assert not app.exception
    history_labels = [
        item.label
        for item in app.expander
        if "创建测试点" in item.label or "人工审核通过" in item.label
    ]
    assert history_labels[0].startswith("人工审核通过")


def test_batch_history_query_error_is_shown(monkeypatch):
    app = _run_page(monkeypatch, [], history_error="history database unavailable")

    assert not app.exception
    assert any(
        "读取批次操作历史失败" in item.value
        for item in app.error
    )


def test_batch_history_unknown_action_is_compatible(monkeypatch):
    app = _run_page(
        monkeypatch,
        [_history("history-unknown", action_type="future_action")],
    )

    assert not app.exception
    assert any(
        "其他操作（future_action）" in item.label
        for item in app.expander
    )
