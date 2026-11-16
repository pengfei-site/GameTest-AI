
"""测试点人工编辑服务"""

from core.schemas import TestPointEditableContent
from database.repositories.test_point_repository import (
    edit_test_point as repository_edit_test_point,
)


def edit_test_point(
    test_point_id: str,
    updated_content: TestPointEditableContent,
) -> dict:
    """
    人工编辑测试点。

    业务规则：
    1. 只接受 TestPointEditableContent 类型。
    2. 编辑字段由 Pydantic 模型限定。
    3. 具体的数据更新和历史记录由 Repository 负责。
    4. 编辑成功后，人工审核状态重置为 pending。
    5. Repository 异常向上抛出，不伪装成成功。
    """

    if not isinstance(test_point_id, str) or not test_point_id.strip():
        raise ValueError("test_point_id 不能为空")

    if not isinstance(updated_content, TestPointEditableContent):
        raise TypeError(
            "updated_content 必须是 TestPointEditableContent 类型"
        )

    test_point_id = test_point_id.strip()

    # Repository 负责：
    # - 检查测试点是否存在
    # - 检查测试点是否已删除
    # - 校验编辑内容
    # - 更新当前内容
    # - 重置人工审核状态
    # - 保存完整编辑历史
    # - 保证更新和历史记录处于同一事务
    repository_edit_test_point(
        test_point_id,
        updated_content,
    )

    return {
        "success": True,
        "test_point_id": test_point_id,
        "manual_review_status": "pending",
        "message": "测试点编辑成功，已保存修改历史",
    }
