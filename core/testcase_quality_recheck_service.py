
import json

from core.case_schemas import (
    TestCaseCandidate,
    TestCaseCandidateCollection,
)
from core.schemas import RequirementAnalysis, TestPoint
from core.testcase_validator import validate_testcases
from core.testcase_reviewer import review_testcases

from database.connection import get_connection
from database.repositories import (
    test_case_candidate_repository as candidate_repo,
    test_case_generation_batch_point_repository as batch_point_repo,
    test_case_generation_batch_repository as batch_repo,
    test_case_quality_repository as quality_repo,
)
from database.repositories.requirement_repository import (
    get_requirement_analysis,
)


class _CandidateVersionChangedError(Exception):
    """质量复检执行期间候选当前版本发生变化。"""


def _normalize_candidate_content(content: dict) -> dict:
    """使用候选 Schema 规范化正文，确保比较口径一致。"""
    return TestCaseCandidate.model_validate(
        content
    ).model_dump(mode="json")


def _verify_candidate_version_in_transaction(
    conn,
    candidate_id: str,
    expected_version_no: int,
    expected_version_id: str,
    expected_content: dict,
) -> None:
    """
    在即将保存质量报告的同一事务中重新检查候选版本。

    使用 BEGIN IMMEDIATE 后调用，避免检查与保存之间
    发生其他数据库写入。
    """
    candidate_row = conn.execute(
        """
        SELECT
            id,
            current_version,
            current_content_json
        FROM test_case_candidates
        WHERE id = ?
        """,
        (candidate_id,),
    ).fetchone()

    if candidate_row is None:
        raise _CandidateVersionChangedError(
            "质量复检期间候选记录已不存在，拒绝保存报告。"
        )

    current_version_no = candidate_row["current_version"]

    if current_version_no != expected_version_no:
        raise _CandidateVersionChangedError(
            "质量复检期间候选当前版本号发生变化，拒绝保存报告。"
        )

    version_row = conn.execute(
        """
        SELECT
            id,
            candidate_id,
            version_no,
            content_json
        FROM test_case_candidate_versions
        WHERE candidate_id = ?
          AND version_no = ?
        """,
        (
            candidate_id,
            expected_version_no,
        ),
    ).fetchone()

    if version_row is None:
        raise _CandidateVersionChangedError(
            "质量复检期间候选当前版本记录不存在，拒绝保存报告。"
        )

    if version_row["id"] != expected_version_id:
        raise _CandidateVersionChangedError(
            "质量复检期间候选版本记录 ID 发生变化，拒绝保存报告。"
        )

    if version_row["candidate_id"] != candidate_id:
        raise _CandidateVersionChangedError(
            "候选版本归属发生变化，拒绝保存报告。"
        )

    if version_row["version_no"] != expected_version_no:
        raise _CandidateVersionChangedError(
            "候选版本号与版本记录不一致，拒绝保存报告。"
        )

    try:
        candidate_content = json.loads(
            candidate_row["current_content_json"]
        )
        version_content = json.loads(
            version_row["content_json"]
        )

        candidate_normalized = _normalize_candidate_content(
            candidate_content
        )
        version_normalized = _normalize_candidate_content(
            version_content
        )

    except Exception as exc:
        raise _CandidateVersionChangedError(
            f"质量复检期间候选正文无法正确解析，拒绝保存报告：{exc}"
        ) from exc

    if candidate_normalized != expected_content:
        raise _CandidateVersionChangedError(
            "质量复检期间候选当前正文发生变化，拒绝保存报告。"
        )

    if version_normalized != expected_content:
        raise _CandidateVersionChangedError(
            "质量复检期间候选版本正文发生变化，拒绝保存报告。"
        )

    if candidate_normalized != version_normalized:
        raise _CandidateVersionChangedError(
            "候选当前正文与版本记录正文不一致，拒绝保存报告。"
        )


def recheck_testcase_quality(candidate_id: str) -> dict:
    """
    对测试用例候选的当前版本重新执行质量检查。

    业务规则：
    1. 以候选当前版本记录中的 content 为检查依据。
    2. 候选当前正文必须与当前版本正文一致。
    3. 必须能够完整追溯来源测试点快照、生成批次和需求分析。
    4. Python Validator 和 AI Reviewer 都执行成功后才保存报告。
    5. 两类质量报告均关联当前 candidate_version_id。
    6. 不修改候选正文、版本号和人工审核状态。
    7. 不覆盖历史质量记录。
    8. 两份质量报告在同一事务中原子保存。
    9. 保存前再次核对候选版本，防止并发修改。

    返回：
        dict，包含执行状态、版本信息、检查报告及持久化状态。
    """
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        raise ValueError("candidate_id 不能为空")

    candidate_id = candidate_id.strip()

    # =========================================================
    # 1. 查询候选及当前版本
    # =========================================================

    candidate = candidate_repo.get_candidate_by_id(candidate_id)

    if candidate is None:
        raise ValueError("测试用例候选不存在")

    current_version_no = candidate.get("current_version")

    if (
        not isinstance(current_version_no, int)
        or isinstance(current_version_no, bool)
        or current_version_no < 1
    ):
        raise ValueError("候选当前版本号无效")

    versions = candidate_repo.list_candidate_versions(candidate_id)

    current_versions = [
        version
        for version in versions
        if version.get("version_no") == current_version_no
    ]

    if len(current_versions) != 1:
        raise ValueError("候选当前版本记录不存在或不唯一")

    version = current_versions[0]

    if version.get("candidate_id") != candidate_id:
        raise ValueError("候选版本归属不一致")

    version_id = version.get("id")

    if not isinstance(version_id, str) or not version_id.strip():
        raise ValueError("候选当前版本 ID 无效")

    # =========================================================
    # 2. 恢复当前版本候选正文
    # =========================================================

    version_content = version.get("content")
    candidate_content = candidate.get("current_content")

    if not isinstance(version_content, dict):
        raise ValueError("当前版本正文格式无效")

    if not isinstance(candidate_content, dict):
        raise ValueError("候选当前正文格式无效")

    current_candidate = TestCaseCandidate.model_validate(
        version_content
    )

    candidate_current_model = TestCaseCandidate.model_validate(
        candidate_content
    )

    expected_content = current_candidate.model_dump(mode="json")

    if (
        expected_content
        != candidate_current_model.model_dump(mode="json")
    ):
        raise ValueError(
            "候选当前正文与当前版本正文不一致，拒绝执行质量复检"
        )

    # =========================================================
    # 3. 查询来源测试点快照
    # =========================================================

    batch_point_id = candidate.get("batch_point_id")

    if not isinstance(batch_point_id, str) or not batch_point_id.strip():
        raise ValueError("候选缺少来源测试点快照关联")

    batch_point = batch_point_repo.get_batch_point_by_id(
        batch_point_id
    )

    if batch_point is None:
        raise ValueError("来源测试点快照不存在")

    batch_id = candidate.get("batch_id")

    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("候选缺少测试用例生成批次关联")

    if batch_point.get("batch_id") != batch_id:
        raise ValueError("候选与来源测试点快照的批次归属不一致")

    point_content = batch_point.get("point_content")

    if not isinstance(point_content, dict):
        raise ValueError("来源测试点快照内容无效")

    test_point = TestPoint.model_validate(point_content)

    if test_point.point_id != batch_point.get("point_id"):
        raise ValueError("来源测试点编号与快照编号不一致")

    # =========================================================
    # 4. 查询测试用例生成批次
    # =========================================================

    generation_batch = batch_repo.get_generation_batch(batch_id)

    if generation_batch is None:
        raise ValueError("测试用例生成批次不存在")

    requirement_analysis_id = generation_batch.get(
        "requirement_analysis_id"
    )

    if (
        not isinstance(requirement_analysis_id, str)
        or not requirement_analysis_id.strip()
    ):
        raise ValueError("生成批次缺少需求分析关联")

    project_id = generation_batch.get("project_id")

    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("生成批次缺少项目关联")

    # =========================================================
    # 5. 查询并恢复需求分析
    # =========================================================

    requirement_record = get_requirement_analysis(
        requirement_analysis_id
    )

    if requirement_record is None:
        raise ValueError("关联需求分析记录不存在")

    if requirement_record.get("project_id") != project_id:
        raise ValueError("需求分析与生成批次的项目归属不一致")

    analysis_data = requirement_record.get("analysis_data")

    if not isinstance(analysis_data, dict):
        raise ValueError("需求分析结构化内容无效")

    requirement = RequirementAnalysis.model_validate(
        analysis_data
    )

    # =========================================================
    # 6. 执行两项质量检查
    # =========================================================

    candidate_collection = TestCaseCandidateCollection(
        candidates=[current_candidate]
    )

    validation_report = validate_testcases(
        candidate_collection
    )

    reviewer_report = review_testcases(
        requirement,
        test_point,
        candidate_collection,
    )

    validation_report_data = validation_report.model_dump(
        mode="json"
    )

    reviewer_report_data = reviewer_report.model_dump(
        mode="json"
    )

    # =========================================================
    # 7. 原子保存两份质量报告
    # =========================================================

    validation_saved = False
    reviewer_saved = False

    validation_record = None
    reviewer_record = None

    try:
        with get_connection(write=True) as conn:
            # 先取得 SQLite 写锁。
            # 从此处开始，其他写事务不能在本次事务提交前
            # 修改候选当前版本。
            conn.execute("BEGIN IMMEDIATE")

            # 在同一个事务连接中再次核对候选版本。
            _verify_candidate_version_in_transaction(
                conn=conn,
                candidate_id=candidate_id,
                expected_version_no=current_version_no,
                expected_version_id=version_id,
                expected_content=expected_content,
            )

            # 保存 Validator 报告。
            validation_record = quality_repo.create_validation_record(
                candidate_id=candidate_id,
                candidate_version_id=version_id,
                report=validation_report,
                conn=conn,
            )

            # 保存 Reviewer 报告。
            reviewer_record = quality_repo.create_reviewer_record(
                candidate_id=candidate_id,
                candidate_version_id=version_id,
                report=reviewer_report,
                conn=conn,
            )

        # 只有正常退出 with，事务成功提交后，
        # 才能将两份报告标记为保存成功。
        validation_saved = True
        reviewer_saved = True

    except _CandidateVersionChangedError as exc:
        return {
            "success": False,
            "stage": "version_consistency",
            "candidate_id": candidate_id,
            "candidate_version_id": version_id,
            "version_no": current_version_no,
            "validation_report": validation_report_data,
            "reviewer_report": reviewer_report_data,
            "validation_saved": False,
            "reviewer_saved": False,
            "validation_record": None,
            "reviewer_record": None,
            "error": str(exc),
        }

    except Exception as exc:
        # 任一报告写入失败，get_connection 会回滚整个事务。
        # 因此两份报告均视为未保存。
        return {
            "success": False,
            "stage": "quality_persistence",
            "candidate_id": candidate_id,
            "candidate_version_id": version_id,
            "version_no": current_version_no,
            "validation_report": validation_report_data,
            "reviewer_report": reviewer_report_data,
            "validation_saved": False,
            "reviewer_saved": False,
            "validation_record": None,
            "reviewer_record": None,
            "error": str(exc),
        }

    # =========================================================
    # 8. 返回完整复检结果
    # =========================================================

    return {
        "success": validation_saved and reviewer_saved,
        "stage": "completed",
        "candidate_id": candidate_id,
        "candidate_version_id": version_id,
        "version_no": current_version_no,
        "validation_report": validation_report_data,
        "reviewer_report": reviewer_report_data,
        "validation_saved": validation_saved,
        "reviewer_saved": reviewer_saved,
        "validation_record": validation_record,
        "reviewer_record": reviewer_record,
        "error": None,
    }
