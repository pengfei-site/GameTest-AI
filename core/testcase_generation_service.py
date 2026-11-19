
from core.schemas import RequirementAnalysis, TestPoint
from core.case_schemas import TestCaseCandidateCollection
from core.review_schemas import TestCaseReviewResult

from core.testcase_generator import generate_testcases
from core.testcase_validator import validate_testcases
from core.testcase_reviewer import review_testcases

from database.repositories.requirement_repository import (
    get_requirement_analysis,
)

from database.repositories.generation_batch_repository import (
    get_generation_batch as get_test_point_generation_batch,
)

from database.repositories.test_point_repository import (
    list_test_points,
)

from database.repositories.test_case_generation_batch_repository import (
    create_generation_batch,
    update_generation_batch,
)

from database.repositories.test_case_generation_batch_point_repository import (
    create_batch_points,
    update_batch_point_collection_validation,
)

from database.repositories.test_case_candidate_repository import (
    create_candidate,
    list_candidate_versions,
)

from database.repositories.test_case_quality_repository import (
    create_validation_record,
    create_reviewer_record,
)


def run_testcase_generation(
    project_id: str,
    requirement_analysis_id: str,
    test_point_batch_id: str,
) -> dict:
    """
    STEP 10.7：测试用例生成业务编排。

    流程：
    1. 获取需求分析
    2. 检查需求分析项目归属
    3. 检查来源测试点批次归属
    4. 获取已人工审核通过的测试点
    5. 校验测试点结构
    6. 创建测试用例生成批次
    7. 保存测试点快照
    8. 逐个测试点调用 Generator
    9. 保存候选用例及 V1
    10. 对每条候选执行 Python Validator
    11. 对每条候选执行 AI Reviewer
    12. 保存候选级质量记录
    13. 持久化集合级 Validator 报告
    14. 更新批次状态及统计数据

    注意：
    - 不修改原始测试点。
    - 不修改需求分析记录。
    - 不自动执行人工审核。
    - 候选用例初始状态为 pending。
    - 单条候选失败不影响同一测试点的其他候选。
    - 集合级 Validator 报告持久化到测试点快照。
    - 单候选 Validator 报告仍保存到候选级质量记录。
    """

    # ==================================================
    # 1. 获取需求分析
    # ==================================================

    requirement_record = get_requirement_analysis(
        requirement_analysis_id
    )

    if requirement_record is None:
        raise ValueError("需求分析记录不存在")

    # ==================================================
    # 2. 检查需求分析项目归属
    # ==================================================

    if requirement_record["project_id"] != project_id:
        raise ValueError("需求分析记录不属于当前项目")

    requirement = RequirementAnalysis.model_validate(
        requirement_record["analysis_data"]
    )

    # ==================================================
    # 3. 检查来源测试点批次归属
    # ==================================================

    source_batch = get_test_point_generation_batch(
        test_point_batch_id
    )

    if source_batch is None:
        raise ValueError("来源测试点生成批次不存在")

    if source_batch["project_id"] != project_id:
        raise ValueError("来源测试点批次不属于当前项目")

    if source_batch["requirement_analysis_id"] != requirement_analysis_id:
        raise ValueError(
            "来源测试点批次与当前需求分析记录不匹配"
        )

    # ==================================================
    # 4. 获取人工审核通过的测试点
    # ==================================================

    approved_points = list_test_points(
        batch_id=test_point_batch_id,
        include_deleted=False,
        manual_review_status="approved",
    )

    if not approved_points:
        raise ValueError(
            "当前测试点批次没有可用于生成测试用例的已审核通过测试点"
        )

    # ==================================================
    # 5. 校验测试点结构
    # ==================================================

    normalized_points = []

    for point in approved_points:

        if not isinstance(point.get("current_content"), dict):
            raise ValueError(
                f"测试点 {point.get('point_id')} 当前内容格式错误"
            )

        test_point = TestPoint.model_validate(
            point["current_content"]
        )

        if test_point.point_id != point["point_id"]:
            raise ValueError(
                f"测试点 {point['point_id']} 与当前内容中的编号不一致"
            )

        normalized = dict(point)

        normalized["current_content"] = test_point.model_dump(
            mode="json"
        )

        normalized_points.append(normalized)

    # ==================================================
    # 6. 创建测试用例生成批次
    # ==================================================

    batch = create_generation_batch(
        project_id=project_id,
        requirement_analysis_id=requirement_analysis_id,
        module=requirement.module,
        generation_config={
            "generator": "generate_testcases",
            "validator": "validate_testcases",
            "reviewer": "review_testcases",
            "review_scope": "candidate_collection_per_test_point",
            "source_test_point_batch_id": test_point_batch_id,
        },
        total_points=len(normalized_points),
    )

    batch_id = batch["id"]

    # ==================================================
    # 7. 保存测试点快照
    # ==================================================

    try:

        batch_points = create_batch_points(
            batch_id=batch_id,
            test_points=normalized_points,
        )

    except Exception as exc:

        update_generation_batch(
            batch_id=batch_id,
            status="failed",
            error_message=f"测试点快照保存失败：{str(exc)}",
        )

        raise

    # ==================================================
    # 8. 初始化统计数据
    # ==================================================

    total_candidates = 0
    successful_points = 0
    failed_points = 0
    empty_points = 0

    point_results = []
    errors = []

    # ==================================================
    # 9. 逐个测试点处理
    # ==================================================

    for batch_point in batch_points:

        point_id = batch_point["point_id"]
        batch_point_id = batch_point["id"]

        point_result = {
            "batch_point_id": batch_point_id,
            "test_point_id": batch_point["test_point_id"],
            "point_id": point_id,
            "success": False,
            "candidate_count": 0,
            "candidate_ids": [],
            "candidate_results": [],
            "collection_validation_report": None,
            "error_message": "",
        }

        try:

            # ------------------------------------------
            # 9.1 恢复测试点快照
            # ------------------------------------------

            test_point = TestPoint.model_validate(
                batch_point["point_content"]
            )

            # ------------------------------------------
            # 9.2 调用 Generator
            # ------------------------------------------

            generation_result = generate_testcases(
                requirement=requirement,
                test_point=test_point,
            )

            if not generation_result.success:
                raise RuntimeError(
                    generation_result.error_message
                    or "AI 测试用例生成失败"
                )

            candidates = generation_result.candidates

            candidate_collection = TestCaseCandidateCollection(
                candidates=candidates
            )

            candidate_count = len(candidates)

            point_result["candidate_count"] = candidate_count

            # ------------------------------------------
            # 9.3 空候选处理
            # ------------------------------------------

            if candidate_count == 0:

                collection_report = validate_testcases(
                    candidate_collection
                )

                collection_report_data = (
                    collection_report.model_dump(mode="json")
                )

                # 持久化空候选集合的 Validator 报告
                update_batch_point_collection_validation(
                    batch_point_id=batch_point_id,
                    report=collection_report,
                )

                point_result["collection_validation_report"] = (
                    collection_report_data
                )

                empty_points += 1
                successful_points += 1
                point_result["success"] = True

                point_results.append(point_result)
                continue

            # ------------------------------------------
            # 9.4 集合级校验
            # ------------------------------------------

            collection_report = validate_testcases(
                candidate_collection
            )

            collection_report_data = (
                collection_report.model_dump(mode="json")
            )

            # 持久化非空候选集合的 Validator 报告
            update_batch_point_collection_validation(
                batch_point_id=batch_point_id,
                report=collection_report,
            )

            point_result["collection_validation_report"] = (
                collection_report_data
            )


            # ------------------------------------------
            # 9.5 逐条保存候选及执行 Python Validator
            # ------------------------------------------

            candidate_errors = []
            review_items = []

            for candidate_no, candidate_content in enumerate(
                candidates,
                start=1,
            ):

                candidate_result = {
                    "candidate_id": None,
                    "candidate_no": candidate_no,
                    "candidate_version_id": None,
                    "validation_report": None,
                    "review_report": None,
                    "success": False,
                    "error_message": "",
                }

                try:

                    # ----------------------------------
                    # 9.5.1 保存候选及 V1
                    # ----------------------------------

                    created_candidate = create_candidate(
                        batch_id=batch_id,
                        batch_point_id=batch_point_id,
                        candidate_no=candidate_no,
                        candidate=candidate_content,
                    )

                    candidate_id = created_candidate["id"]

                    candidate_result["candidate_id"] = candidate_id

                    point_result["candidate_ids"].append(
                        candidate_id
                    )

                    total_candidates += 1

                    # ----------------------------------
                    # 9.5.2 获取 V1
                    # ----------------------------------

                    versions = list_candidate_versions(
                        candidate_id
                    )

                    version = next(
                        (
                            item
                            for item in versions
                            if item["version_no"] == 1
                        ),
                        None,
                    )

                    if version is None:
                        raise RuntimeError(
                            f"候选用例 {candidate_id} 未找到 V1"
                        )

                    version_id = version["id"]

                    candidate_result["candidate_version_id"] = (
                        version_id
                    )

                    # ----------------------------------
                    # 9.5.3 单候选 Python Validator
                    # ----------------------------------

                    single_collection = TestCaseCandidateCollection(
                        candidates=[candidate_content]
                    )

                    validation_report = validate_testcases(
                        single_collection
                    )

                    candidate_result["validation_report"] = (
                        validation_report.model_dump(mode="json")
                    )

                    create_validation_record(
                        candidate_id=candidate_id,
                        candidate_version_id=version_id,
                        report=validation_report,
                    )

                    # ----------------------------------
                    # 9.5.4 收集待批量 Reviewer 的候选
                    # ----------------------------------

                    review_items.append({
                        "review_index": len(review_items) + 1,
                        "candidate_content": candidate_content,
                        "candidate_id": candidate_id,
                        "candidate_version_id": version_id,
                        "candidate_result": candidate_result,
                    })

                except Exception as candidate_exc:

                    candidate_error = (
                        f"测试点 {point_id} 的候选 "
                        f"{candidate_no} 处理失败：{str(candidate_exc)}"
                    )

                    candidate_result["error_message"] = (
                        candidate_error
                    )

                    candidate_errors.append(candidate_error)
                    errors.append(candidate_error)

                finally:

                    # 无论成功或失败，都保留候选处理结果
                    point_result["candidate_results"].append(
                        candidate_result
                    )

            # ------------------------------------------
            # 9.6 对当前测试点的候选集合执行一次 AI Reviewer
            # ------------------------------------------

            if review_items:

                review_collection = TestCaseCandidateCollection(
                    candidates=[
                        item["candidate_content"]
                        for item in review_items
                    ]
                )

                try:

                    batch_review_report = review_testcases(
                        requirement=requirement,
                        test_point=test_point,
                        candidates=review_collection,
                    )

                    # ----------------------------------
                    # 9.6.1 将批量报告拆分为单候选报告
                    # ----------------------------------

                    for item in review_items:

                        review_index = item["review_index"]

                        candidate_result = item["candidate_result"]

                        try:

                            candidate_issues = [
                                issue.model_copy(
                                    update={"candidate_index": 1}
                                )
                                for issue in batch_review_report.issues
                                if issue.candidate_index == review_index
                            ]

                            is_approved = (
                                review_index
                                in batch_review_report.approved_candidate_indices
                            )

                            is_review = (
                                review_index
                                in batch_review_report.review_candidate_indices
                            )

                            has_critical_issue = any(
                                issue.severity == "critical"
                                for issue in candidate_issues
                            )

                            # 单候选审核状态
                            if has_critical_issue:
                                candidate_status = "failed"

                            elif candidate_issues or is_review or not is_approved:
                                candidate_status = "needs_review"

                            else:
                                candidate_status = "passed"

                            # 单候选审核摘要
                            if candidate_status == "passed":
                                candidate_summary = (
                                    "该候选用例通过 AI Reviewer 审查，未发现问题。"
                                )

                            elif candidate_status == "failed":
                                candidate_summary = (
                                    "该候选用例存在严重问题，不能直接接受。"
                                )

                            else:
                                candidate_summary = (
                                    "该候选用例存在需要人工复核的问题。"
                                )

                            single_review_report = TestCaseReviewResult(
                                overall_status=candidate_status,
                                summary=candidate_summary,
                                issues=candidate_issues,
                                approved_candidate_indices=(
                                    [1]
                                    if candidate_status == "passed"
                                    else []
                                ),
                                review_candidate_indices=(
                                    []
                                    if candidate_status == "passed"
                                    else [1]
                                ),
                            )

                            # ----------------------------------
                            # 9.6.2 保存独立候选 Reviewer 记录
                            # ----------------------------------

                            create_reviewer_record(
                                candidate_id=item["candidate_id"],
                                candidate_version_id=item[
                                    "candidate_version_id"
                                ],
                                report=single_review_report,
                            )

                            candidate_result["review_report"] = (
                                single_review_report.model_dump(
                                    mode="json"
                                )
                            )

                            candidate_result["success"] = True

                        except Exception as candidate_exc:

                            candidate_error = (
                                f"测试点 {point_id} 的候选 "
                                f"{candidate_result['candidate_no']} "
                                f"保存 Reviewer 结果失败：{str(candidate_exc)}"
                            )

                            candidate_result["error_message"] = (
                                candidate_error
                            )

                            candidate_errors.append(candidate_error)
                            errors.append(candidate_error)

                except Exception as reviewer_exc:

                    # 批量 Reviewer 调用失败：
                    # 当前测试点所有待审核候选均标记失败

                    for item in review_items:

                        candidate_result = item["candidate_result"]

                        candidate_error = (
                            f"测试点 {point_id} 的候选 "
                            f"{candidate_result['candidate_no']} "
                            f"批量 Reviewer 失败：{str(reviewer_exc)}"
                        )

                        candidate_result["error_message"] = (
                            candidate_error
                        )

                        candidate_errors.append(candidate_error)
                        errors.append(candidate_error)

            # ------------------------------------------
            # 9.7 当前测试点处理结果
            # ------------------------------------------

            if candidate_errors:
                raise RuntimeError(
                    f"{len(candidate_errors)} 条候选用例处理失败"
                )

            point_result["success"] = True
            successful_points += 1

        except Exception as exc:

            failed_points += 1

            error_message = (
                f"测试点 {point_id} 处理失败：{str(exc)}"
            )

            point_result["error_message"] = error_message
            errors.append(error_message)

        point_results.append(point_result)

    # ==================================================
    # 10. 更新批次状态
    # ==================================================

    final_status = (
        "failed"
        if errors
        else "completed"
    )

    updated_batch = update_generation_batch(
        batch_id=batch_id,
        status=final_status,
        total_candidates=total_candidates,
        error_message="\n".join(errors),
    )

    # ==================================================
    # 11. 返回结果
    # ==================================================

    return {
        "success": len(errors) == 0,
        "batch_id": batch_id,
        "project_id": project_id,
        "requirement_analysis_id": requirement_analysis_id,
        "source_test_point_batch_id": test_point_batch_id,
        "status": updated_batch["status"],
        "total_points": len(normalized_points),
        "successful_points": successful_points,
        "failed_points": failed_points,
        "empty_points": empty_points,
        "total_candidates": total_candidates,
        "point_results": point_results,
        "errors": errors,
    }
