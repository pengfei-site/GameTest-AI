import json
import sqlite3
import tempfile
import html
from pathlib import Path

import streamlit as st
from components.header import render_header
from pydantic import ValidationError

from database.repositories.project_repository import list_projects
from database.repositories.requirement_repository import (
    list_requirement_analyses,
)
from database.repositories.test_case_generation_batch_repository import (
    list_generation_batches,
)
from database.repositories.test_case_candidate_repository import (
    list_candidates_by_batch,
    get_candidate_by_id,
    list_candidate_versions,
)
from database.repositories.test_case_generation_batch_point_repository import (
    get_batch_point_by_id,
)
from database.repositories.test_case_quality_repository import (
    get_latest_validation_record,
    get_latest_reviewer_record,
    list_reviewer_records,
)
from database.connection import get_connection

from core.case_schemas import TestCaseCandidate, TestCaseStep
from core.testcase_quality_recheck_service import (
    recheck_testcase_quality,
)
from core.testcase_reviewer_recheck_service import (
    recheck_testcase_with_reviewer,
)
from core.testcase_reviewer_confirmation_service import (
    confirm_reviewer_report,
    batch_confirm_reviewer_reports,
    get_latest_reviewer_confirmation,
    list_reviewer_confirmation_history,
)
from core.testcase_manual_review_service import (
    approve_candidate,
    reject_candidate,
    modify_candidate,
    batch_approve_candidates,
    batch_reject_candidates,
)
from core.testcase_export_service import export_approved_testcases


# ============================================================
# 页面专属 UI
# ============================================================

def render_page_styles():
    st.html("""
    <style>
    .tc-manage-hero {
        padding: 22px 26px;
        margin: 8px 0 24px 0;
        border: 1px solid #e8e5f5;
        border-radius: 16px;
        background: linear-gradient(120deg, #f5f3ff 0%, #ffffff 85%);
    }

    .tc-manage-hero-title {
        font-size: 22px;
        font-weight: 700;
        color: #302b55;
        margin-bottom: 7px;
    }

    .tc-manage-hero-desc {
        font-size: 14px;
        line-height: 1.7;
        color: #77728c;
    }

    .tc-manage-section {
        font-size: 18px;
        font-weight: 700;
        color: #302b55;
        padding: 4px 0 10px 0;
        margin: 8px 0 14px 0;
        border-bottom: 1px solid #eceaf3;
    }

    .tc-manage-stat {
        padding: 16px 18px;
        border: 1px solid #e9e7f1;
        border-radius: 13px;
        background: #ffffff;
        min-height: 94px;
    }

    .tc-manage-stat-label {
        color: #77728c;
        font-size: 13px;
        margin-bottom: 8px;
    }

    .tc-manage-stat-value {
        color: #302b55;
        font-size: 27px;
        line-height: 1.2;
        font-weight: 700;
    }

    .tc-manage-info {
        padding: 15px 18px;
        border: 1px solid #e9e7f1;
        border-radius: 12px;
        background: #ffffff;
        min-height: 78px;
    }

    .tc-manage-info-label {
        color: #858096;
        font-size: 12px;
        margin-bottom: 8px;
    }

    .tc-manage-info-value {
        color: #38334f;
        font-size: 16px;
        font-weight: 650;
        overflow-wrap: anywhere;
    }

    div[data-testid="stExpander"] {
        border-radius: 12px;
    }

    @media (max-width: 768px) {
        .tc-manage-hero {
            padding: 18px;
        }

        .tc-manage-hero-title {
            font-size: 19px;
        }

        .tc-manage-stat-value {
            font-size: 23px;
        }
    }
    </style>
    """)


def render_stat_card(label, value):
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))

    st.html(f"""
    <div class="tc-manage-stat">
        <div class="tc-manage-stat-label">{safe_label}</div>
        <div class="tc-manage-stat-value">{safe_value}</div>
    </div>
    """)


def render_info_card(label, value):
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))

    st.html(f"""
    <div class="tc-manage-info">
        <div class="tc-manage-info-label">{safe_label}</div>
        <div class="tc-manage-info-value">{safe_value}</div>
    </div>
    """)


def render_section(title):
    safe_title = html.escape(str(title))
    st.html(
        f'<div class="tc-manage-section">{safe_title}</div>'
    )


# ============================================================
# 通用辅助函数
# ============================================================

def show_json(title, data):
    st.markdown(f"**{title}**")
    if data is None:
        st.info("暂无数据")
    else:
        st.json(data)


def format_time(value):
    if not value:
        return "-"
    return str(value)


def get_value(data, key, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    return default


def get_status_label(status):
    labels = {
        "pending": "待审核",
        "approved": "已通过",
        "rejected": "已驳回",
        "completed": "已完成",
        "running": "执行中",
        "failed": "失败",
        "passed": "通过",
        "needs_review": "需要复核",
        "confirmed_passed": "人工确认通过",
        "confirmed_issues": "人工确认有问题",
        "recheck_required": "要求重新复核",
    }
    return labels.get(status, status or "-")


def normalize_content(content):
    if isinstance(content, str):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return {}
    return content or {}


def get_project_name(project):
    return (
        project.get("project_name")
        or project.get("name")
        or project.get("id")
        or "未命名项目"
    )


def get_candidate_content(candidate):
    return normalize_content(candidate.get("current_content"))


def get_candidate_version(candidate):
    return candidate.get("current_version")


def get_current_version_record(candidate_id, candidate):
    """
    精确获取候选当前版本记录。
    不使用版本列表中的最大值代替当前版本。
    """
    current_version_no = candidate.get("current_version")

    if (
        not isinstance(current_version_no, int)
        or isinstance(current_version_no, bool)
        or current_version_no < 1
    ):
        return None

    versions = list_candidate_versions(candidate_id)

    matched_versions = [
        item for item in versions
        if item.get("version_no") == current_version_no
        and item.get("candidate_id") == candidate_id
    ]

    if len(matched_versions) != 1:
        return None

    return matched_versions[0]


def show_candidate_content(content):
    content = normalize_content(content)

    st.markdown(f"### {content.get('title', '未命名用例')}")

    st.write("**测试目标**")
    st.write(content.get("objective", ""))

    st.write("**优先级**")
    st.write(content.get("priority", "-"))

    st.write("**前置条件**")
    for item in content.get("preconditions", []):
        st.write(f"- {item}")

    st.write("**测试步骤**")

    for step in content.get("steps", []):
        st.markdown(
            f"**步骤 {step.get('step_no', '')}**："
            f"{step.get('action', '')}"
        )
        st.write(
            f"预期结果：{step.get('expected_result', '')}"
        )

    st.write("**后置条件**")
    for item in content.get("postconditions", []):
        st.write(f"- {item}")


def build_candidate_schema(form_data):
    return TestCaseCandidate(
        title=form_data["title"],
        objective=form_data["objective"],
        priority=form_data["priority"],
        preconditions=[
            x.strip()
            for x in form_data["preconditions"].splitlines()
            if x.strip()
        ],
        steps=[
            TestCaseStep(
                step_no=index + 1,
                action=step["action"],
                expected_result=step["expected_result"],
            )
            for index, step in enumerate(form_data["steps"])
        ],
        postconditions=[
            x.strip()
            for x in form_data["postconditions"].splitlines()
            if x.strip()
        ],
    )


# ============================================================
# 人工审核历史
# ============================================================

def get_manual_review_history(candidate_id):
    """
    读取候选用例人工审核历史。
    不假定 created_at 字段一定存在。
    """
    try:
        with get_connection() as conn:
            columns = conn.execute(
                "PRAGMA table_info(test_case_manual_reviews)"
            ).fetchall()

            column_names = {
                row["name"] if isinstance(row, sqlite3.Row) else row[1]
                for row in columns
            }

            required = {
                "id",
                "candidate_id",
                "candidate_version_id",
                "action_type",
                "comment",
            }

            if not required.issubset(column_names):
                return []

            selected_columns = [
                "id",
                "candidate_version_id",
                "action_type",
                "comment",
            ]

            if "created_at" in column_names:
                selected_columns.append("created_at")

            sql = (
                f"SELECT {', '.join(selected_columns)} "
                "FROM test_case_manual_reviews "
                "WHERE candidate_id = ? "
            )

            if "created_at" in column_names:
                sql += "ORDER BY created_at DESC, rowid DESC"
            else:
                sql += "ORDER BY rowid DESC"

            rows = conn.execute(
                sql,
                (candidate_id,),
            ).fetchall()

            return [
                dict(row) if isinstance(row, sqlite3.Row)
                else dict(zip(selected_columns, row))
                for row in rows
            ]

    except Exception as exc:
        st.warning(f"读取人工审核历史失败：{exc}")
        return []


# ============================================================
# AI Reviewer 人工确认
# ============================================================

def show_reviewer_confirmation(record):
    reviewer_record_id = record.get("id")
    candidate_id = record.get("candidate_id")
    candidate_version_id = record.get("candidate_version_id")

    st.markdown("#### AI Reviewer 人工确认")

    if not reviewer_record_id:
        st.error("Reviewer 报告缺少记录 ID，无法进行人工确认")
        return

    if not candidate_id or not candidate_version_id:
        st.error("Reviewer 报告缺少候选或版本关联信息")
        return

    try:
        latest_result = get_latest_reviewer_confirmation(
            reviewer_record_id
        )

        confirmation_status = latest_result.get(
            "confirmation_status",
            "pending",
        )

        if confirmation_status == "pending":
            st.warning("当前报告：待人工确认")
        elif confirmation_status == "confirmed_passed":
            st.success("当前报告：人工确认通过")
        elif confirmation_status == "confirmed_issues":
            st.error("当前报告：人工确认有问题")
        elif confirmation_status == "recheck_required":
            st.warning("当前报告：要求重新复核")
        else:
            st.info(
                f"人工确认状态：{get_status_label(confirmation_status)}"
            )

        latest_confirmation = latest_result.get("confirmation")

        if latest_confirmation:
            col1, col2 = st.columns(2)

            col1.write(
                f"最近确认人："
                f"{latest_confirmation.get('confirmed_by', '-')}"
            )
            col2.write(
                f"最近确认时间："
                f"{format_time(latest_confirmation.get('confirmed_at'))}"
            )

            comment = latest_confirmation.get(
                "confirmation_comment",
                "",
            )

            if comment:
                st.write(f"最近确认意见：{comment}")

        st.caption(
            "人工确认只针对当前这条 AI Reviewer 报告，"
            "不会改变候选用例的最终人工审核状态。"
        )

        with st.form(
            key=f"reviewer_confirmation_form_{reviewer_record_id}"
        ):
            st.markdown("**提交人工确认**")

            confirmed_by = st.text_input(
                "确认人",
                placeholder="请输入实际确认人",
                key=f"confirmation_user_{reviewer_record_id}",
            )

            status_options = {
                "确认通过": "confirmed_passed",
                "确认有问题": "confirmed_issues",
                "要求重新复核": "recheck_required",
            }

            selected_status_label = st.selectbox(
                "人工确认结果",
                list(status_options.keys()),
                key=f"confirmation_status_{reviewer_record_id}",
            )

            confirmation_comment = st.text_area(
                "人工确认意见",
                placeholder="请填写确认依据、发现的问题或重新复核要求",
                key=f"confirmation_comment_{reviewer_record_id}",
            )

            submitted = st.form_submit_button(
                "提交人工确认",
                type="primary",
            )

        if submitted:
            if not confirmed_by.strip():
                st.error("请填写确认人")
                return

            try:
                result = confirm_reviewer_report(
                    reviewer_record_id=reviewer_record_id,
                    candidate_id=candidate_id,
                    candidate_version_id=candidate_version_id,
                    confirmation_status=status_options[
                        selected_status_label
                    ],
                    confirmed_by=confirmed_by.strip(),
                    confirmation_comment=confirmation_comment,
                )

                st.session_state[
                    "testcase_management_message"
                ] = (
                    f"AI Reviewer 人工确认已提交："
                    f"{get_status_label(result.get('confirmation_status'))}"
                )

                st.rerun()

            except ValueError as exc:
                st.error(f"人工确认校验失败：{exc}")

            except Exception as exc:
                st.error(f"人工确认提交失败：{exc}")

        history = list_reviewer_confirmation_history(
            reviewer_record_id
        )

        st.markdown("**人工确认历史**")

        if not history:
            st.info("该 Reviewer 报告尚无人工确认历史")
        else:
            st.caption(f"共 {len(history)} 条人工确认记录")

            for index, item in enumerate(history, start=1):
                st.markdown(
                    f"**第 {len(history) - index + 1} 条确认记录**"
                )

                col1, col2 = st.columns(2)

                col1.write(
                    f"确认结果："
                    f"{get_status_label(item.get('confirmation_status'))}"
                )
                col2.write(
                    f"确认人：{item.get('confirmed_by', '-')}"
                )

                st.write(
                    f"确认时间："
                    f"{format_time(item.get('confirmed_at'))}"
                )

                st.write(
                    f"确认意见："
                    f"{item.get('confirmation_comment') or '无'}"
                )

                if index < len(history):
                    st.divider()

    except Exception as exc:
        st.error(f"读取 AI Reviewer 人工确认信息失败：{exc}")


# ============================================================
# 当前版本质量报告
# ============================================================

def show_quality_reports(candidate_id, version_id):
    render_section("当前版本质量报告")

    validation = get_latest_validation_record(
        candidate_id,
        version_id,
    )

    reviewer = get_latest_reviewer_record(
        candidate_id,
        version_id,
    )

    left, right = st.columns(2)

    with left:
        st.markdown("#### Python Validator")

        if not validation:
            st.info("当前版本尚未执行 Python Validator")
        else:
            passed = validation.get("passed")

            if passed:
                st.success("Validator：通过")
            else:
                st.error("Validator：未通过")

            st.write(f"错误数：{validation.get('error_count', 0)}")
            st.write(f"警告数：{validation.get('warning_count', 0)}")
            st.write(
                f"检查时间：{format_time(validation.get('created_at'))}"
            )

            show_json(
                "Validator 详细报告",
                validation.get("report"),
            )

    with right:
        st.markdown("#### AI Reviewer")

        if not reviewer:
            st.info("当前版本尚未执行 AI Reviewer")
        else:
            status = reviewer.get("overall_status")

            if status == "passed":
                st.success("Reviewer：通过")
            elif status == "needs_review":
                st.warning("Reviewer：需要复核")
            else:
                st.error(f"Reviewer：{get_status_label(status)}")

            st.write(reviewer.get("summary", ""))
            st.write(
                f"复核时间：{format_time(reviewer.get('created_at'))}"
            )

            show_json(
                "Reviewer 详细报告",
                reviewer.get("report"),
            )

            reviewer_record_id = reviewer.get("id")

            if reviewer_record_id:
                try:
                    confirmation = get_latest_reviewer_confirmation(
                        reviewer_record_id
                    )

                    confirmation_status = confirmation.get(
                        "confirmation_status",
                        "pending",
                    )

                    st.markdown("**最新报告人工确认状态**")

                    if confirmation_status == "pending":
                        st.warning("待人工确认")
                    elif confirmation_status == "confirmed_passed":
                        st.success("人工确认通过")
                    elif confirmation_status == "confirmed_issues":
                        st.error("人工确认有问题")
                    elif confirmation_status == "recheck_required":
                        st.warning("要求重新复核")
                    else:
                        st.info(get_status_label(confirmation_status))

                except Exception as exc:
                    st.warning(f"读取人工确认状态失败：{exc}")


# ============================================================
# AI Reviewer 历史记录
# ============================================================

def show_reviewer_history(candidate_id, version_id):
    render_section("AI Reviewer 复核历史")

    records = list_reviewer_records(
        candidate_id,
        version_id,
    )

    if not records:
        st.info("当前版本暂无 Reviewer 复核历史")
        return

    st.caption(
        f"当前版本共 {len(records)} 条 Reviewer 复核记录"
    )

    for index, record in enumerate(records):
        status = record.get("overall_status")
        created_at = format_time(record.get("created_at"))

        if status == "passed":
            status_icon = "✅"
        elif status == "needs_review":
            status_icon = "⚠️"
        else:
            status_icon = "❌"

        title = (
            f"{status_icon} {get_status_label(status)}"
            f" | {created_at}"
            f" | 第 {len(records) - index} 次复核"
        )

        with st.expander(title):
            st.write(f"记录 ID：{record.get('id', '-')}")
            st.write(
                f"版本 ID："
                f"{record.get('candidate_version_id', '-')}"
            )
            st.write(f"复核时间：{created_at}")
            st.write(f"整体状态：{get_status_label(status)}")
            st.write(f"复核摘要：{record.get('summary', '-')}")

            report = record.get("report") or {}

            issues = report.get("issues", [])
            approved = report.get(
                "approved_candidate_indices",
                [],
            )
            review = report.get(
                "review_candidate_indices",
                [],
            )

            col1, col2, col3 = st.columns(3)

            col1.metric("问题数量", len(issues))
            col2.metric("通过数量", len(approved))
            col3.metric("待复核数量", len(review))

            if issues:
                st.markdown("#### 问题明细")

                for issue_index, issue in enumerate(
                    issues,
                    start=1,
                ):
                    st.markdown(f"**问题 {issue_index}**")
                    st.json(issue)

            show_json("完整 Reviewer 报告", report)

            st.divider()
            show_reviewer_confirmation(record)


# ============================================================
# 独立 AI Reviewer 复核
# ============================================================

def show_reviewer_recheck(candidate):
    render_section("独立 AI Reviewer 复核")

    st.caption(
        "仅针对候选当前版本执行 AI Reviewer。"
        "不会执行 Python Validator，不会修改用例正文、"
        "版本号或人工审核状态。每次复核都会新增历史记录。"
    )

    if st.button(
        "单独重新执行 AI Reviewer",
        key=f"reviewer_recheck_{candidate['id']}",
    ):
        try:
            with st.spinner("AI Reviewer 正在复核当前版本..."):
                result = recheck_testcase_with_reviewer(
                    candidate["id"]
                )

            if result.get("success"):
                report = result.get("reviewer_report") or {}
                status = report.get("overall_status")

                st.success(
                    f"AI Reviewer 复核完成，"
                    f"V{result.get('version_no')} 报告已保存。"
                )

                if status == "passed":
                    st.success("Reviewer 结论：通过")
                elif status == "needs_review":
                    st.warning("Reviewer 结论：需要人工复核")
                else:
                    st.error(
                        f"Reviewer 结论：{get_status_label(status)}"
                    )

                st.write(report.get("summary", ""))

                st.info(
                    "新生成的 Reviewer 报告尚未进行人工确认，"
                    "请在下方 Reviewer 复核历史中完成确认。"
                )

            else:
                stage = result.get("stage", "-")
                error = result.get("error", "未知错误")

                st.error(
                    f"Reviewer 复核失败，阶段：{stage}。{error}"
                )

                if result.get("reviewer_report"):
                    st.warning(
                        "Reviewer 已生成报告，但未能成功保存。"
                    )

                    show_json(
                        "未保存的 Reviewer 报告",
                        result["reviewer_report"],
                    )

            st.rerun()

        except ValueError as exc:
            st.error(f"复核前置校验失败：{exc}")

        except Exception as exc:
            st.error(f"Reviewer 复核异常：{exc}")


# ============================================================
# 来源测试点
# ============================================================

def show_source_point(candidate):
    render_section("来源测试点快照")

    batch_point_id = candidate.get("batch_point_id")

    if not batch_point_id:
        st.warning("候选记录没有来源测试点快照 ID")
        return

    point = get_batch_point_by_id(batch_point_id)

    if not point:
        st.warning("未找到来源测试点快照")
        return

    st.write(f"业务编号：{point.get('point_id', '-')}")
    show_json("测试点快照内容", point.get("point_content"))
    show_json(
        "测试点集合校验报告",
        point.get("collection_validation_report"),
    )


# ============================================================
# 版本历史
# ============================================================

def show_version_history(candidate_id):
    render_section("版本历史")

    versions = list_candidate_versions(candidate_id)

    if not versions:
        st.info("暂无版本历史")
        return

    for version in versions:
        version_no = version.get("version_no", "?")

        with st.expander(f"V{version_no}"):
            st.write(f"版本 ID：{version.get('id', '-')}")
            st.write(f"变更类型：{version.get('change_type', '-')}")
            st.write(
                f"创建时间：{format_time(version.get('created_at'))}"
            )

            show_candidate_content(version.get("content"))


# ============================================================
# 人工审核历史
# ============================================================

def show_manual_review_history(candidate_id):
    render_section("人工审核历史")

    history = get_manual_review_history(candidate_id)

    if not history:
        st.info("暂无人工审核历史")
        return

    for record in history:
        with st.expander(
            f"{record.get('action_type', '-')} "
            f"| {record.get('created_at', '-')}"
        ):
            st.write(
                f"版本 ID：{record.get('candidate_version_id', '-')}"
            )
            st.write(f"审核意见：{record.get('comment', '-')}")


# ============================================================
# 编辑功能
# ============================================================

def edit_candidate_form(candidate):
    render_section("编辑测试用例")

    content = get_candidate_content(candidate)
    steps = content.get("steps", [])

    with st.form("edit_candidate_form"):
        title = st.text_input(
            "用例标题",
            value=content.get("title", ""),
        )

        objective = st.text_area(
            "测试目标",
            value=content.get("objective", ""),
        )

        priorities = ["P0", "P1", "P2", "P3"]
        current_priority = content.get("priority", "P2")

        priority = st.selectbox(
            "优先级",
            priorities,
            index=(
                priorities.index(current_priority)
                if current_priority in priorities
                else 2
            ),
        )

        preconditions = st.text_area(
            "前置条件（每行一条）",
            value="\n".join(content.get("preconditions", [])),
        )

        st.markdown("#### 测试步骤")

        edited_steps = []

        for index, step in enumerate(steps):
            st.markdown(f"步骤 {index + 1}")

            action = st.text_area(
                f"操作动作 {index + 1}",
                value=step.get("action", ""),
                key=f"edit_action_{candidate['id']}_{index}",
            )

            expected = st.text_area(
                f"预期结果 {index + 1}",
                value=step.get("expected_result", ""),
                key=f"edit_expected_{candidate['id']}_{index}",
            )

            edited_steps.append({
                "action": action,
                "expected_result": expected,
            })

        postconditions = st.text_area(
            "后置条件（每行一条）",
            value="\n".join(content.get("postconditions", [])),
        )

        comment = st.text_input(
            "修改说明",
            placeholder="说明本次人工修改内容",
        )

        submitted = st.form_submit_button(
            "保存修改并创建新版本",
            type="primary",
        )

    if not submitted:
        return

    try:
        updated_candidate = build_candidate_schema({
            "title": title,
            "objective": objective,
            "priority": priority,
            "preconditions": preconditions,
            "steps": edited_steps,
            "postconditions": postconditions,
        })

        result = modify_candidate(
            candidate["id"],
            updated_candidate,
            comment=comment,
        )

        new_version_id = result.get("new_version_id")

        if not new_version_id:
            st.error(
                "修改操作未返回新版本 ID，请检查数据库记录。"
            )
            st.json(result)
            return

        st.toast(
            f"修改成功！已创建 V{result['new_version_no']} 新版本。",
            icon="✅",
        )

        st.session_state["testcase_management_message"] = (
            f"修改成功！已创建 V{result['new_version_no']} 新版本。"
        )

        st.rerun()

    except ValidationError as exc:
        st.error("测试用例内容不符合 Schema")
        st.json(exc.errors())

    except Exception as exc:
        st.error(f"修改失败：{exc}")


# ============================================================
# 人工审核
# ============================================================

def show_manual_review_actions(candidate):
    render_section("人工审核")

    status = candidate.get("manual_review_status")

    st.write(f"当前审核状态：{get_status_label(status)}")

    if status != "pending":
        st.info("当前候选不处于待审核状态，不能重复审核")
        return

    comment = st.text_input(
        "审核意见",
        key=f"review_comment_{candidate['id']}",
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "审核通过",
            key=f"approve_{candidate['id']}",
            type="primary",
        ):
            try:
                result = approve_candidate(
                    candidate["id"],
                    comment=comment,
                )

                if result.get("manual_review_status") == "approved":
                    st.toast("审核通过！", icon="✅")

                    st.session_state[
                        "testcase_management_message"
                    ] = "审核通过！候选用例已正式通过人工审核。"

                    st.rerun()

                st.error(result.get("error", "审核未通过"))

            except Exception as exc:
                st.error(f"审核失败：{exc}")

    with col2:
        reject_reason = st.text_input(
            "驳回原因",
            key=f"reject_reason_{candidate['id']}",
        )

        if st.button(
            "驳回",
            key=f"reject_{candidate['id']}",
        ):
            if not reject_reason.strip():
                st.warning("请填写驳回原因")
            else:
                try:
                    result = reject_candidate(
                        candidate["id"],
                        reason=reject_reason,
                    )

                    if result.get("manual_review_status") == "rejected":
                        st.toast("驳回成功！", icon="✅")

                        st.session_state[
                            "testcase_management_message"
                        ] = "驳回成功！候选用例已被驳回。"

                        st.rerun()

                    st.error(
                        "驳回操作未返回预期结果，请检查数据库记录。"
                    )
                    st.json(result)

                except ValueError as exc:
                    st.error(f"驳回失败：{exc}")

                except Exception as exc:
                    st.error(f"驳回失败：{exc}")


# ============================================================
# 批量人工审核
# ============================================================

def show_batch_manual_review(candidates, batch_id):
    render_section("批量人工审核")

    pending_candidates = [
        item for item in candidates
        if item.get("manual_review_status") == "pending"
    ]

    if not pending_candidates:
        st.info("当前批次没有待审核候选用例")
        return

    st.caption(
        "仅展示待审核候选。批量审核仍会逐条执行单条审核的全部质量校验，"
        "每条候选独立成功或失败。"
    )

    candidate_options = {}

    for item in pending_candidates:
        content = get_candidate_content(item)
        label = (
            f"{item.get('candidate_no', '-')} | "
            f"{content.get('title', '未命名用例')} | "
            f"{item['id'][:8]}"
        )
        candidate_options[label] = item["id"]

    select_all = st.checkbox(
        "全选当前批次待审核候选",
        key=f"batch_review_select_all_{batch_id}",
    )

    selected_labels = st.multiselect(
        "选择需要批量审核的候选用例",
        options=list(candidate_options.keys()),
        key=f"batch_review_candidates_{batch_id}",
        help="可以多选；勾选全选后将处理当前批次全部待审核候选。",
    )

    if select_all:
        selected_ids = list(candidate_options.values())
    else:
        selected_ids = [
            candidate_options[label]
            for label in selected_labels
        ]

    st.write(f"已选择：{len(selected_ids)} 条候选")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "批量审核通过",
            key=f"batch_approve_{batch_id}",
            type="primary",
            disabled=not selected_ids,
        ):
            try:
                with st.spinner("正在逐条执行审核通过..."):
                    result = batch_approve_candidates(selected_ids)

                st.session_state[
                    f"batch_review_result_{batch_id}"
                ] = {
                    "action": "approve",
                    "result": result,
                }

                st.rerun()

            except Exception as exc:
                st.error(f"批量审核通过执行失败：{exc}")

    with col2:
        reject_reason = st.text_input(
            "批量驳回原因",
            key=f"batch_reject_reason_{batch_id}",
            placeholder="批量驳回时必须填写原因",
        )

        if st.button(
            "批量驳回",
            key=f"batch_reject_{batch_id}",
            disabled=not selected_ids,
        ):
            if not reject_reason.strip():
                st.warning("请先填写批量驳回原因")
            else:
                try:
                    with st.spinner("正在逐条执行驳回..."):
                        result = batch_reject_candidates(
                            selected_ids,
                            reason=reject_reason.strip(),
                        )

                    st.session_state[
                        f"batch_review_result_{batch_id}"
                    ] = {
                        "action": "reject",
                        "result": result,
                    }

                    st.rerun()

                except Exception as exc:
                    st.error(f"批量驳回执行失败：{exc}")

    saved_result = st.session_state.get(
        f"batch_review_result_{batch_id}"
    )

    if isinstance(saved_result, dict):
        result = saved_result.get("result") or {}

        st.divider()
        st.markdown("#### 最近一次批量审核结果")

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric("处理总数", result.get("total", 0))
        metric2.metric("成功", result.get("succeeded", 0))
        metric3.metric("失败", result.get("failed", 0))

        for item in result.get("results", []):
            candidate_id = item.get("candidate_id", "-")
            success = item.get("success", False)

            if success:
                st.success(f"候选 {candidate_id[:8]}：处理成功")
            else:
                st.error(
                    f"候选 {candidate_id[:8]}：处理失败。"
                    f"原因：{item.get('error') or '未知错误'}"
                )

        if st.button(
            "清除批量审核结果",
            key=f"clear_batch_review_result_{batch_id}",
        ):
            st.session_state.pop(
                f"batch_review_result_{batch_id}",
                None,
            )
            st.rerun()


# ============================================================
# 批量 AI Reviewer 人工复核
# ============================================================

def show_batch_reviewer_confirmation(candidates, batch_id):
    render_section("批量 AI Reviewer 人工复核")

    st.caption(
        "仅处理候选当前版本最新的 needs_review Reviewer 报告。"
        "每条记录均调用单条人工确认 Service，"
        "独立保存确认历史，不修改 Reviewer 原始报告和候选最终审核状态。"
    )

    reviewable_items = []

    for candidate in candidates:
        candidate_id = candidate.get("id")

        if not candidate_id:
            continue

        current_version = get_current_version_record(
            candidate_id,
            candidate,
        )

        if not current_version:
            continue

        version_id = current_version.get("id")

        if not version_id:
            continue

        reviewer = get_latest_reviewer_record(
            candidate_id,
            version_id,
        )

        if not reviewer:
            continue

        if reviewer.get("overall_status") != "needs_review":
            continue

        reviewer_record_id = reviewer.get("id")

        if not reviewer_record_id:
            continue

        if reviewer.get("candidate_version_id") != version_id:
            continue

        content = get_candidate_content(candidate)

        latest_confirmation = get_latest_reviewer_confirmation(
            reviewer_record_id
        )

        confirmation_status = latest_confirmation.get(
            "confirmation_status",
            "pending",
        )

        reviewable_items.append({
            "reviewer_record_id": reviewer_record_id,
            "candidate_id": candidate_id,
            "candidate_version_id": version_id,
            "confirmation_status": confirmation_status,
            "label": (
                f"{candidate.get('candidate_no', '-')} | "
                f"{content.get('title', '未命名用例')} | "
                f"V{candidate.get('current_version', '-')} | "
                f"{get_status_label(confirmation_status)}"
            ),
        })

    if not reviewable_items:
        st.info("当前批次没有需要人工复核的最新 Reviewer 报告。")
        return

    st.write(f"当前需要人工复核：{len(reviewable_items)} 条")

    item_options = {
        item["label"]: item
        for item in reviewable_items
    }

    select_all = st.checkbox(
        "全选当前批次需要人工复核的报告",
        key=f"batch_reviewer_select_all_{batch_id}",
    )

    selected_labels = st.multiselect(
        "选择需要人工确认的 Reviewer 报告",
        options=list(item_options.keys()),
        key=f"batch_reviewer_items_{batch_id}",
        help="每条报告对应一个候选当前版本。",
    )

    if select_all:
        selected_items = reviewable_items
    else:
        selected_items = [
            item_options[label]
            for label in selected_labels
        ]

    st.write(f"已选择：{len(selected_items)} 条")

    confirmed_by = st.text_input(
        "批量确认人",
        key=f"batch_reviewer_confirmed_by_{batch_id}",
        placeholder="请输入实际确认人",
    )

    confirmation_comment = st.text_area(
        "批量人工确认意见",
        key=f"batch_reviewer_comment_{batch_id}",
        placeholder="填写本次批量确认的依据、问题说明或复核要求",
    )

    def execute_batch_confirmation(status):
        if not selected_items:
            st.warning("请至少选择一条 Reviewer 报告")
            return

        if not confirmed_by.strip():
            st.warning("请填写批量确认人")
            return

        confirmations = [
            {
                "reviewer_record_id": item["reviewer_record_id"],
                "candidate_id": item["candidate_id"],
                "candidate_version_id": item["candidate_version_id"],
            }
            for item in selected_items
        ]

        try:
            with st.spinner("正在逐条提交人工确认..."):
                result = batch_confirm_reviewer_reports(
                    confirmations=confirmations,
                    confirmation_status=status,
                    confirmed_by=confirmed_by.strip(),
                    confirmation_comment=confirmation_comment.strip(),
                )

            st.session_state[
                f"batch_reviewer_confirmation_result_{batch_id}"
            ] = {
                "status": status,
                "result": result,
            }

            st.rerun()

        except Exception as exc:
            st.error(f"批量人工复核执行失败：{exc}")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button(
            "批量确认通过",
            key=f"batch_reviewer_pass_{batch_id}",
            type="primary",
            disabled=not selected_items,
        ):
            execute_batch_confirmation("confirmed_passed")

    with col2:
        if st.button(
            "批量确认有问题",
            key=f"batch_reviewer_issues_{batch_id}",
            disabled=not selected_items,
        ):
            execute_batch_confirmation("confirmed_issues")

    with col3:
        if st.button(
            "批量要求重新复核",
            key=f"batch_reviewer_recheck_{batch_id}",
            disabled=not selected_items,
        ):
            execute_batch_confirmation("recheck_required")

    saved_result = st.session_state.get(
        f"batch_reviewer_confirmation_result_{batch_id}"
    )

    if isinstance(saved_result, dict):
        result = saved_result.get("result") or {}
        status = saved_result.get("status")

        st.divider()
        st.markdown("#### 最近一次批量人工复核结果")

        st.write(f"本次操作：{get_status_label(status)}")

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric("处理总数", result.get("total", 0))
        metric2.metric("成功", result.get("succeeded", 0))
        metric3.metric("失败", result.get("failed", 0))

        for item in result.get("results", []):
            candidate_id = str(item.get("candidate_id") or "-")

            if item.get("success"):
                st.success(
                    f"候选 {candidate_id[:8]}：人工确认成功"
                )
            else:
                st.error(
                    f"候选 {candidate_id[:8]}：人工确认失败。"
                    f"原因：{item.get('error') or '未知错误'}"
                )

        if st.button(
            "清除批量人工复核结果",
            key=f"clear_batch_reviewer_result_{batch_id}",
        ):
            st.session_state.pop(
                f"batch_reviewer_confirmation_result_{batch_id}",
                None,
            )
            st.rerun()


# ============================================================
# 完整质量复检
# ============================================================

def show_quality_recheck(candidate):
    render_section("完整质量复检")

    st.caption(
        "完整质量复检会同时执行 Python Validator 和 AI Reviewer。"
    )

    candidate_id = candidate["id"]
    result_session_key = "testcase_quality_recheck_display"

    if st.button(
        "重新执行质量复检",
        key=f"recheck_{candidate_id}",
        type="primary",
    ):
        try:
            with st.spinner(
                "正在执行 Python Validator 和 AI Reviewer..."
            ):
                result = recheck_testcase_quality(candidate_id)

            if not isinstance(result, dict):
                result = {
                    "success": False,
                    "stage": "invalid_result",
                    "error": "质量复检 Service 返回了非字典类型结果",
                    "raw_result": str(result),
                }

            st.session_state[result_session_key] = {
                "candidate_id": candidate_id,
                "result": result,
                "exception": None,
            }

            st.rerun()

        except Exception as exc:
            st.session_state[result_session_key] = {
                "candidate_id": candidate_id,
                "result": None,
                "exception": str(exc),
            }

            st.rerun()

    saved_result = st.session_state.get(result_session_key)

    if (
        isinstance(saved_result, dict)
        and saved_result.get("candidate_id") == candidate_id
    ):
        st.divider()
        st.markdown("#### 本次完整质量复检执行结果")

        exception_message = saved_result.get("exception")
        result = saved_result.get("result")

        if exception_message:
            st.error("完整质量复检执行异常")
            st.write(f"异常信息：{exception_message}")

        elif isinstance(result, dict):
            if result.get("success"):
                st.success("完整质量复检执行成功，报告保存流程已完成。")

                st.caption(
                    "执行成功不代表质量检查通过。"
                    "请分别查看下方 Validator 和 Reviewer 的实际检查结论。"
                )

                validation_saved = result.get("validation_saved")
                reviewer_saved = result.get("reviewer_saved")

                if validation_saved is not None:
                    st.write(
                        "Validator 报告保存状态："
                        + ("已保存" if validation_saved else "未保存")
                    )

                if reviewer_saved is not None:
                    st.write(
                        "Reviewer 报告保存状态："
                        + ("已保存" if reviewer_saved else "未保存")
                    )

            else:
                stage = result.get("stage", "-")
                error = result.get("error")

                st.error(f"完整质量复检失败，阶段：{stage}")

                if error:
                    st.write(f"失败原因：{error}")

                if stage == "version_consistency":
                    st.warning(
                        "复检过程中候选版本发生变化，"
                        "本次复检报告未保存。请重新确认当前版本后再执行。"
                    )

                elif stage == "quality_persistence":
                    st.warning(
                        "质量报告持久化失败。"
                        "请检查数据库事务执行结果，不应存在单份报告被单独保存的情况。"
                    )

            with st.expander("查看完整复检执行结果", expanded=True):
                st.json(result)

        else:
            st.error("当前保存的复检结果格式不正确")

        if st.button(
            "清除本次复检结果",
            key=f"clear_quality_recheck_{candidate_id}",
        ):
            st.session_state.pop(result_session_key, None)
            st.rerun()

    st.caption(
        "说明：复检成功只代表检查流程执行及报告保存成功，"
        "不代表用例质量合格。Validator 未通过或 Reviewer "
        "提出问题时，报告仍可能成功保存。审核通过仍需满足 "
        "Validator 和 Reviewer 的通过条件。"
    )


# ============================================================
# 候选统计
# ============================================================

def show_candidate_statistics(candidates):
    active = [
        item for item in candidates
        if not item.get("is_deleted", False)
    ]

    pending = [
        item for item in active
        if item.get("manual_review_status") == "pending"
    ]

    approved = [
        item for item in active
        if item.get("manual_review_status") == "approved"
    ]

    rejected = [
        item for item in active
        if item.get("manual_review_status") == "rejected"
    ]

    columns = st.columns(4)

    statistics = [
        ("候选总数", len(active)),
        ("待审核", len(pending)),
        ("已通过", len(approved)),
        ("已驳回", len(rejected)),
    ]

    for column, (label, value) in zip(columns, statistics):
        with column:
            render_stat_card(label, value)


# ============================================================
# Excel 导出
# ============================================================

def show_export(batch_id):
    render_section("已通过用例导出")

    if st.button(
        "生成已通过用例 Excel",
        type="primary",
    ):
        temp_file = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".xlsx",
                delete=False,
            ) as file:
                temp_file = Path(file.name)

            result = export_approved_testcases(
                batch_id,
                str(temp_file),
            )

            if not result.get("success"):
                st.error(result.get("error", "导出失败"))
                return

            if not temp_file.exists():
                st.error("导出服务未生成 Excel 文件")
                return

            with open(temp_file, "rb") as file:
                excel_data = file.read()

            st.success(
                f"导出成功，共 {result.get('exported_count', 0)} 条用例"
            )

            st.download_button(
                label="下载 Excel",
                data=excel_data,
                file_name=f"approved_testcases_{batch_id[:8]}.xlsx",
                mime=(
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
            )

        except Exception as exc:
            st.error(f"导出异常：{exc}")

        finally:
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass


# ============================================================
# 主页面
# ============================================================

def main():
    render_page_styles()

    render_header(
        title="测试用例管理",
        description=(
            "管理 AI 生成的测试用例候选，执行质量复检、"
            "AI Reviewer 人工确认、人工编辑、审核和 Excel 导出。"
        ),
        breadcrumb=["工作空间", "AI 测试中心", "测试用例管理"],
    )

    st.html("""
    <div class="tc-manage-hero">
        <div class="tc-manage-hero-title">测试用例工作台</div>
        <div class="tc-manage-hero-desc">
            集中查看生成批次、候选用例和质量报告。
            通过独立的审核与复检区域管理用例质量及版本。
        </div>
    </div>
    """)

    message = st.session_state.pop(
        "testcase_management_message",
        None,
    )

    if message:
        st.success(f"✓ {message}", icon="✅")

    # --------------------------------------------------------
    # 1. 项目选择
    # --------------------------------------------------------

    render_section("工作上下文")

    projects = list_projects()

    if not projects:
        st.warning("当前没有项目，请先创建项目")
        return

    project_options = {
        get_project_name(project): project
        for project in projects
    }

    selected_project_name = st.selectbox(
        "选择项目",
        list(project_options.keys()),
    )

    project = project_options[selected_project_name]
    project_id = project["id"]

    # --------------------------------------------------------
    # 2. 需求分析选择
    # --------------------------------------------------------

    analyses = list_requirement_analyses(project_id)

    if not analyses:
        st.warning("当前项目没有需求分析记录")
        return

    analysis_options = {
        (
            f"{item.get('module', '未命名模块')} "
            f"| {item.get('created_at', '')} "
            f"| {item['id'][:8]}"
        ): item
        for item in analyses
    }

    selected_analysis_name = st.selectbox(
        "选择需求分析",
        list(analysis_options.keys()),
    )

    analysis = analysis_options[selected_analysis_name]

    # --------------------------------------------------------
    # 3. 测试用例生成批次
    # --------------------------------------------------------

    batches = list_generation_batches(
        project_id,
        requirement_analysis_id=analysis["id"],
    )

    if not batches:
        st.warning("当前需求分析尚无测试用例生成批次")
        return

    batch_options = {
        (
            f"{item.get('module', '未命名模块')} "
            f"| {get_status_label(item.get('status'))} "
            f"| {item['id'][:8]}"
        ): item
        for item in batches
    }

    selected_batch_name = st.selectbox(
        "选择测试用例生成批次",
        list(batch_options.keys()),
    )

    batch = batch_options[selected_batch_name]
    batch_id = batch["id"]

    # --------------------------------------------------------
    # 4. 批次信息
    # --------------------------------------------------------

    st.divider()
    render_section("生成批次信息")

    batch_columns = st.columns(3)

    with batch_columns[0]:
        render_info_card(
            "批次状态",
            get_status_label(batch.get("status")),
        )

    with batch_columns[1]:
        render_info_card(
            "测试点数量",
            batch.get("total_points", 0),
        )

    with batch_columns[2]:
        render_info_card(
            "候选数量",
            batch.get("total_candidates", 0),
        )

    st.caption(
        f"创建时间：{format_time(batch.get('created_at'))}"
    )

    # --------------------------------------------------------
    # 5. 候选数据
    # --------------------------------------------------------

    candidates = list_candidates_by_batch(batch_id)

    if not candidates:
        st.info("当前批次没有测试用例候选")
        show_export(batch_id)
        return

    candidates = [
        item for item in candidates
        if not item.get("is_deleted", False)
    ]

    st.divider()
    render_section("候选用例统计")
    show_candidate_statistics(candidates)

    # --------------------------------------------------------
    # 6. 批量 AI Reviewer 人工复核
    # --------------------------------------------------------

    with st.expander("批量 AI Reviewer 人工复核", expanded=True):
        show_batch_reviewer_confirmation(
            candidates,
            batch_id,
        )

    # --------------------------------------------------------
    # 7. 候选筛选
    # --------------------------------------------------------

    st.divider()
    render_section("候选用例列表")

    status_options = [
        "全部",
        "pending",
        "approved",
        "rejected",
    ]

    selected_status = st.selectbox(
        "人工审核状态筛选",
        status_options,
        format_func=lambda value: (
            "全部" if value == "全部"
            else get_status_label(value)
        ),
    )

    filtered_candidates = candidates

    if selected_status != "全部":
        filtered_candidates = [
            item for item in candidates
            if item.get("manual_review_status") == selected_status
        ]

    if not filtered_candidates:
        st.info("当前筛选条件下没有候选用例")
        show_export(batch_id)
        return

    # --------------------------------------------------------
    # 8. 批量人工审核
    # --------------------------------------------------------

    with st.expander("批量人工审核", expanded=True):
        show_batch_manual_review(
            candidates,
            batch_id,
        )

    candidate_options = {
        (
            f"{item.get('candidate_no', '-')}"
            f" | {get_candidate_content(item).get('title', '未命名用例')}"
            f" | {get_status_label(item.get('manual_review_status'))}"
        ): item
        for item in filtered_candidates
    }

    selected_candidate_name = st.selectbox(
        "选择候选用例",
        list(candidate_options.keys()),
    )

    selected_candidate = candidate_options[
        selected_candidate_name
    ]

    # --------------------------------------------------------
    # 9. 刷新候选详情
    # --------------------------------------------------------

    candidate = get_candidate_by_id(
        selected_candidate["id"]
    )

    if not candidate:
        st.error("候选用例不存在")
        return

    st.divider()
    render_section("候选用例详情")

    detail_columns = st.columns(3)

    with detail_columns[0]:
        render_info_card(
            "候选编号",
            candidate.get("candidate_no", "-"),
        )

    with detail_columns[1]:
        render_info_card(
            "当前版本",
            f"V{get_candidate_version(candidate)}",
        )

    with detail_columns[2]:
        render_info_card(
            "审核状态",
            get_status_label(candidate.get("manual_review_status")),
        )

    show_candidate_content(
        get_candidate_content(candidate)
    )

    # --------------------------------------------------------
    # 10. 来源测试点
    # --------------------------------------------------------

    st.divider()
    show_source_point(candidate)

    # --------------------------------------------------------
    # 11. 当前版本质量报告及 Reviewer 历史
    # --------------------------------------------------------

    st.divider()

    current_version = get_current_version_record(
        candidate["id"],
        candidate,
    )

    version_id = None

    if current_version:
        version_id = current_version.get("id")

        if version_id:
            show_quality_reports(
                candidate["id"],
                version_id,
            )

            with st.expander(
                "查看当前版本 Reviewer 复核历史"
            ):
                show_reviewer_history(
                    candidate["id"],
                    version_id,
                )
        else:
            st.warning("当前版本记录缺少版本 ID")
    else:
        st.warning(
            "当前版本记录不存在或不唯一，无法读取质量报告"
        )

    # --------------------------------------------------------
    # 12. 独立 AI Reviewer 复核
    # --------------------------------------------------------

    st.divider()

    if version_id:
        show_reviewer_recheck(candidate)
    else:
        st.warning(
            "无法确认当前版本，暂不可执行 Reviewer 复核"
        )

    # --------------------------------------------------------
    # 13. 完整质量复检
    # --------------------------------------------------------

    st.divider()
    show_quality_recheck(candidate)

    # --------------------------------------------------------
    # 14. 编辑
    # --------------------------------------------------------

    st.divider()

    with st.expander("编辑测试用例"):
        edit_candidate_form(candidate)

    # --------------------------------------------------------
    # 15. 人工审核
    # --------------------------------------------------------

    st.divider()
    show_manual_review_actions(candidate)

    # --------------------------------------------------------
    # 16. 版本历史
    # --------------------------------------------------------

    st.divider()

    with st.expander("查看版本历史"):
        show_version_history(candidate["id"])

    # --------------------------------------------------------
    # 17. 人工审核历史
    # --------------------------------------------------------

    st.divider()

    with st.expander("查看人工审核历史"):
        show_manual_review_history(candidate["id"])

    # --------------------------------------------------------
    # 18. Excel 导出
    # --------------------------------------------------------

    st.divider()
    show_export(batch_id)


if __name__ == "__main__":
    main()