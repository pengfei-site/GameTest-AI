
from pathlib import Path

from core.testcase_export_service import (
    export_approved_testcases,
)


BATCH_ID = "859f58c4-a442-4be4-94dd-f39b39b10d07"

OUTPUT_PATH = (
    Path("exports")
    / "GameTest_AI_测试用例导出.xlsx"
)


def main():
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 60)
    print("GameTest AI 真实 Excel 导出")
    print("=" * 60)

    result = export_approved_testcases(
        batch_id=BATCH_ID,
        output_path=str(OUTPUT_PATH),
    )

    print("\n导出结果：")
    print(result)

    print("\n文件路径：")
    print(OUTPUT_PATH.resolve())

    print("=" * 60)


if __name__ == "__main__":
    main()
