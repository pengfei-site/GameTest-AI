from database.repositories.generation_batch_repository import (
    list_generation_batches,
)
from database.repositories.test_point_repository import (
    list_test_points,
)

project_id = input("请输入项目 ID：").strip()

batches = list_generation_batches(project_id)

for batch in batches:
    print("\n" + "=" * 50)
    print("批次 ID：", batch["id"])
    print("需求分析 ID：", batch["requirement_analysis_id"])

    points = list_test_points(
        batch_id=batch["id"],
        include_deleted=True,
    )

    print("测试点总数：", len(points))

    for point in points:
        content = point["current_content"]

        print("-" * 40)
        print("测试点 ID：", point["id"])
        print("测试点编号：", point["point_id"])
        print("标题：", content.get("title", ""))
        print("人工审核状态：", point["manual_review_status"])
        print("逻辑删除：", point["is_deleted"])