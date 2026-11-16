
import json

from core.testcase_generation_service import (
    run_testcase_generation,
)


PROJECT_ID = "25537ae1-17ae-4184-8225-056f6621b2bc"

REQUIREMENT_ANALYSIS_ID = (
    "bad91c43-2b2d-4da0-b036-95bf9d26fb43"
)

TEST_POINT_BATCH_ID = (
    "609483f6-2498-4e18-ab97-734140626b27"
)


def main():

    print("=" * 60)
    print("GameTest AI 真实测试用例生成")
    print("=" * 60)

    print("项目 ID:", PROJECT_ID)
    print("需求分析 ID:", REQUIREMENT_ANALYSIS_ID)
    print("原测试点批次 ID:", TEST_POINT_BATCH_ID)

    print("\n即将调用真实 AI 生成服务。")

    result = run_testcase_generation(
        project_id=PROJECT_ID,
        requirement_analysis_id=REQUIREMENT_ANALYSIS_ID,
        test_point_batch_id=TEST_POINT_BATCH_ID,
    )

    print("\n" + "=" * 60)
    print("真实测试用例生成结果")
    print("=" * 60)

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        default=str,
    ))

    print("\n" + "=" * 60)

    if result["success"]:
        print("生成批次创建成功")
        print("生成批次 ID:", result["batch_id"])
        print("来源测试点数量:", result["total_points"])
        print("成功处理测试点:", result["successful_points"])
        print("候选用例数量:", result["total_candidates"])
        print("批次状态:", result["status"])
    else:
        print("生成过程中存在错误")
        print("批次 ID:", result["batch_id"])
        print("错误信息:")

        for error in result["errors"]:
            print("-", error)

    print("=" * 60)


if __name__ == "__main__":
    main()
