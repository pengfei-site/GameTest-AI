
from database.repositories.generation_batch_repository import (
    list_generation_batches,
)
from database.repositories.test_point_repository import (
    list_test_points,
)

print("=" * 55)
print("STEP 10.3.4 真实 AI 生成数据源检查")
print("=" * 55)

# 查询项目
project_id = input("请输入项目 ID：").strip()

if not project_id:
    raise ValueError("项目 ID 不能为空")

# 查询项目下的生成批次
batches = list_generation_batches(project_id)

if not batches:
    print("没有找到测试点生成批次")
    raise SystemExit(0)

print(f"\n找到 {len(batches)} 个生成批次")

available_points = []

for batch in batches:
    batch_id = batch["id"]

    points = list_test_points(
        batch_id=batch_id,
        include_deleted=False,
        manual_review_status="approved",
    )

    for point in points:
        available_points.append({
            "batch": batch,
            "point": point,
        })

print(f"符合准入条件的测试点：{len(available_points)} 条")

if not available_points:
    print("没有已审核通过且未删除的测试点")
    raise SystemExit(0)

print("\n可用于真实 AI 验证的测试点：")

for index, item in enumerate(available_points, start=1):
    batch = item["batch"]
    point = item["point"]

    content = point["current_content"]

    print(f"\n[{index}]")
    print(f"批次 ID：{batch['id']}")
    print(f"需求分析 ID：{batch['requirement_analysis_id']}")
    print(f"测试点数据库 ID：{point['id']}")
    print(f"测试点编号：{point['point_id']}")
    print(f"测试点标题：{content.get('title', '')}")
    print(f"审核状态：{point['manual_review_status']}")

print("\n数据源检查完成，没有执行 AI 调用。")
