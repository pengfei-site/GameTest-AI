
from core.case_schemas import TestCaseCandidate, TestCaseCandidateCollection
from core.schemas import RequirementAnalysis, TestPoint
from core.testcase_reviewer import review_testcases

from database.repositories import (
    test_case_candidate_repository as candidate_repo,
    test_case_generation_batch_point_repository as batch_point_repo,
    test_case_generation_batch_repository as batch_repo,
    test_case_quality_repository as quality_repo,
)
from database.repositories.requirement_repository import (
    get_requirement_analysis,
)


def recheck_testcase_with_reviewer(candidate_id: str) -> dict:
    """
    对测试用例候选的当前版本单独执行 AI Reviewer 复核。

    业务规则：
    1. 只检查候选当前版本。
    2. 候选当前正文必须与当前版本正文一致。
    3. 必须能够完整追溯来源测试点快照、生成批次和需求分析。
    4. 只执行 AI Reviewer，不执行 Python Validator。
    5. Reviewer 报告必须关联当前 candidate_version_id。
    6. 不修改候选正文、版本号和人工审核状态。
    7. 不覆盖历史 Reviewer 记录，每次执行均新增记录。

    返回：
        dict，包含执行状态、版本信息、审查报告及持久化状态。

    注意：
        上下文数据缺失或不一致时抛出 ValueError。
        AI Reviewer 执行失败时返回 stage="reviewer_execution"。
        报告保存失败时返回 stage="reviewer_persistence"。
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
    # 2. 恢复并校验当前版本候选正文
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

    if (
        current_candidate.model_dump(mode="json")
        != candidate_current_model.model_dump(mode="json")
    ):
        raise ValueError(
            "候选当前正文与当前版本正文不一致，拒绝执行 AI Reviewer 复核"
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
    # 6. 组装当前版本候选集合
    # =========================================================

    candidate_collection = TestCaseCandidateCollection(
        candidates=[current_candidate]
    )

    # =========================================================
    # 7. 单独执行 AI Reviewer
    # =========================================================

    try:
        reviewer_report = review_testcases(
            requirement,
            test_point,
            candidate_collection,
        )

    except Exception as exc:
        return {
            "success": False,
            "stage": "reviewer_execution",
            "candidate_id": candidate_id,
            "candidate_version_id": version_id,
            "version_no": current_version_no,
            "reviewer_report": None,
            "reviewer_saved": False,
            "reviewer_record": None,
            "error": str(exc),
        }

    # =========================================================
    # 8. 保存 AI Reviewer 报告
    # =========================================================

    try:
        reviewer_record = quality_repo.create_reviewer_record(
            candidate_id=candidate_id,
            candidate_version_id=version_id,
            report=reviewer_report,
        )

    except Exception as exc:
        return {
            "success": False,
            "stage": "reviewer_persistence",
            "candidate_id": candidate_id,
            "candidate_version_id": version_id,
            "version_no": current_version_no,
            "reviewer_report": reviewer_report.model_dump(
                mode="json"
            ),
            "reviewer_saved": False,
            "reviewer_record": None,
            "error": str(exc),
        }

    # =========================================================
    # 9. 返回独立 Reviewer 复核结果
    # =========================================================

    return {
        "success": True,
        "stage": "completed",
        "candidate_id": candidate_id,
        "candidate_version_id": version_id,
        "version_no": current_version_no,
        "reviewer_report": reviewer_report.model_dump(
            mode="json"
        ),
        "reviewer_saved": True,
        "reviewer_record": reviewer_record,
        "error": None,
    }
