import sys

from pathlib import Path
from datetime import datetime

# 将项目根目录加入 Python 模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.repositories.project_repository import list_projects
from database.repositories.generation_batch_repository import (
    list_generation_batches,
)
from database.repositories.test_point_repository import (
    create_test_points,
    reject_test_point,
    soft_delete_test_point,
    get_test_point_review_statistics,
    list_test_points,
)


def choose_item(items, title, formatter):
    print(f"\n{title}")

    for index, item in enumerate(items, start=1):
        print(f"{index}. {formatter(item)}")

    while True:
        value = input("请输入序号：").strip()

        try:
            index = int(value) - 1

            if 0 <= index < len(items):
                return items[index]

        except ValueError:
            pass

        print("输入无效，请重新选择。")


def main():

    projects = list_projects()

    if not projects:
        print("当前没有可用项目。")
        return

    project = choose_item(
        projects,
        "选择测试项目",
        lambda item: (
            item.get("project_name")
            or item.get("name")
            or item.get("id")
        ),
    )

    batches = list_generation_batches(project["id"])

    if not batches:
        print("该项目没有测试点生成批次。")
        return

    batch = choose_item(
        batches,
        "选择测试点生成批次",
        lambda item: (
            f"{item.get('generated_at')} | "
            f"{item.get('final_status')} | "
            f"{item.get('id')}"
        ),
    )

    batch_id = batch["id"]

    existing_points = list_test_points(
        batch_id,
        include_deleted=True,
    )

    existing_ids = {
        point["point_id"]
        for point in existing_points
    }

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    rejected_point_id = f"FIX-TP-R-{timestamp}"
    deleted_point_id = f"FIX-TP-D-{timestamp}"

    if (
        rejected_point_id in existing_ids
        or deleted_point_id in existing_ids
    ):
        raise RuntimeError("测试点编号重复，请重新执行。")

    before = get_test_point_review_statistics(batch_id)

    print("\n准备创建以下专项测试数据：")
    print("驳回测试点：", rejected_point_id)
    print("删除测试点：", deleted_point_id)
    print("所属批次：", batch_id)
    print("创建前统计：", before)

    confirmation = input(
        "\n确认创建？请输入 YES："
    ).strip()

    if confirmation != "YES":
        print("已取消，没有创建测试数据。")
        return

    created = create_test_points(
        batch_id=batch_id,
        points=[
            {
                "point_id": rejected_point_id,
                "title": "FIX专项测试：人工驳回",
                "description": "用于验证 rejected 筛选和驳回原因展示。",
            },
            {
                "point_id": deleted_point_id,
                "title": "FIX专项测试：逻辑删除",
                "description": "用于验证已删除测试点的显示和隐藏。",
            },
        ],
    )

    point_map = {
        point["point_id"]: point
        for point in created
    }

    reject_test_point(
        point_map[rejected_point_id]["id"],
        "FIX专项测试：验证人工驳回筛选。",
    )

    soft_delete_test_point(
        point_map[deleted_point_id]["id"]
    )

    after = get_test_point_review_statistics(batch_id)

    default_points = list_test_points(batch_id)

    all_points = list_test_points(
        batch_id,
        include_deleted=True,
    )

    print("\n专项测试数据创建成功。")

    print("驳回测试点 ID：", point_map[rejected_point_id]["id"])
    print("删除测试点 ID：", point_map[deleted_point_id]["id"])

    print("\n创建前统计：", before)
    print("创建后统计：", after)

    print("\n默认列表数量：", len(default_points))
    print("包含删除记录的列表数量：", len(all_points))

    rejected_points = list_test_points(
        batch_id,
        manual_review_status="rejected",
    )

    print("驳回筛选结果数量：", len(rejected_points))

    print("\n数据准备结束。")


if __name__ == "__main__":
    main()
