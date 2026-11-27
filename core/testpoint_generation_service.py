
from core.schemas import RequirementAnalysis
from core.generation_schemas import TestPointGenerationResult
from core.testpoint_generator import generate_testpoints
from core.testpoint_review_service import MANUAL_REVIEW_ENABLED

from database.repositories.requirement_repository import (
    get_requirement_analysis,
)
from database.repositories.generation_batch_repository import (
    create_generation_batch,
)
from database.repositories.test_point_repository import (
    create_test_points,
)


def run_testpoint_generation(
    project_id: str,
    requirement_analysis_id: str,
) -> dict:
    """
    GameTest AI 测试点生成业务编排服务。

    负责：
    1. 获取结构化需求分析
    2. 调用 AI 测试点生成器
    3. 创建测试点生成批次
    4. 持久化测试点
    5. 返回完整业务结果

    不负责：
    - AI 生成逻辑
    - Python 质量校验
    - AI Reviewer 逻辑
    - 人工审核
    """

    # 1. 获取需求分析记录
    requirement_record = get_requirement_analysis(
        requirement_analysis_id
    )

    if requirement_record is None:
        raise ValueError("需求分析记录不存在")

    # 2. 检查项目归属，避免错误项目调用 AI
    if requirement_record["project_id"] != project_id:
        raise ValueError("需求分析记录不属于当前项目")

    # 3. 转换为结构化需求模型
    requirement = RequirementAnalysis.model_validate(
        requirement_record["analysis_data"]
    )

    # 4. 调用现有测试点生成器
    generation_result = generate_testpoints(requirement)

    if not isinstance(generation_result, TestPointGenerationResult):
        raise TypeError("测试点生成器返回了无效结果")

    # 5. 创建测试点生成批次
    batch = create_generation_batch(
        project_id=project_id,
        requirement_analysis_id=requirement_analysis_id,
        validation_report=generation_result.validation_report,
        review_report=generation_result.review_report,
        final_status=generation_result.final_status,
    )

    batch_id = batch["id"]

    # 6. 持久化测试点
    generated_points = generation_result.testpoints.points

    if generated_points:
        created_points = create_test_points(
            batch_id=batch_id,
            points=generated_points,
            review_report=generation_result.review_report,
            manual_review_status=(
                "pending" if MANUAL_REVIEW_ENABLED else "approved"
            ),
        )
    else:
        created_points = []

    # 7. 返回统一业务结果
    return {
        "success": True,
        "batch_id": batch_id,
        "project_id": project_id,
        "requirement_analysis_id": requirement_analysis_id,
        "final_status": generation_result.final_status,
        "generated_count": len(generated_points),
        "saved_count": len(created_points),
        "validation_report": generation_result.validation_report,
        "review_report": generation_result.review_report,
        "created_points": created_points,
    }
