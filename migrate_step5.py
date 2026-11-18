
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "pages"
LEGACY = ROOT / "legacy_pages"
BACKUP = ROOT / "migration_backup_step5"

FILES = [
    {
        "source": PAGES / "07_AI测试用例生成.py",
        "target": PAGES / "11_AI测试用例生成.py",
        "title": "AI 测试用例生成",
        "description": (
            "根据结构化需求分析和已审核通过的测试点，"
            "调用 AI 自动生成测试用例候选集。"
        ),
        "breadcrumb": ["工作空间", "AI 测试中心", "AI 测试用例生成"],
    },
    {
        "source": PAGES / "08_测试用例管理.py",
        "target": PAGES / "12_测试用例管理.py",
        "title": "测试用例管理",
        "description": (
            "管理 AI 生成的测试用例候选，执行质量复检、"
            "AI Reviewer 人工确认、人工编辑、审核和 Excel 导出。"
        ),
        "breadcrumb": ["工作空间", "AI 测试中心", "测试用例管理"],
    },
]


def replace_page_header(content, title, description, breadcrumb):
    # 添加统一页头导入
    if "from components.header import render_header" not in content:
        content = content.replace(
            "import streamlit as st",
            "import streamlit as st\n"
            "from components.header import render_header",
            1,
        )

    # 删除页面级 set_page_config
    content, count = re.subn(
        r"\nst\.set_page_config\(\s*"
        r"page_title=.*?\n"
        r"layout=.*?\n"
        r"\)\s*\n",
        "\n",
        content,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        print(f"  提示：未找到页面级 set_page_config：{title}")

    # 替换 main() 内原有标题和说明
    if title == "AI 测试用例生成":
        pattern = (
            r'    st\.title\("🧪 AI 测试用例生成"\)\s*'
            r'    st\.caption\(\s*.*?\s*    \)\s*'
        )
    else:
        pattern = (
            r'    st\.title\("🧪 测试用例管理工作台"\)\s*'
            r'    st\.caption\(\s*.*?\s*    \)\s*'
        )

    breadcrumb_text = repr(breadcrumb)

    replacement = (
        f"    render_header(\n"
        f"        title={title!r},\n"
        f"        description={description!r},\n"
        f"        breadcrumb={breadcrumb_text},\n"
        f"    )\n"
    )

    content, count = re.subn(
        pattern,
        lambda _: replacement,
        content,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        raise RuntimeError(
            f"未能替换页面标题，请检查原文件：{title}"
        )

    return content


def main():
    print("=" * 55)
    print("GameTest AI - STEP 5 页面迁移")
    print("=" * 55)

    if not (ROOT / "components" / "header.py").exists():
        raise FileNotFoundError("找不到 components/header.py")

    if not (ROOT / "components" / "navigation.py").exists():
        raise FileNotFoundError("找不到 components/navigation.py")

    BACKUP.mkdir(exist_ok=True)
    LEGACY.mkdir(exist_ok=True)

    # 1. 创建两个新页面
    for item in FILES:
        source = item["source"]
        target = item["target"]

        if not source.exists():
            raise FileNotFoundError(f"找不到原页面：{source}")

        if target.exists():
            raise FileExistsError(
                f"目标页面已经存在，为避免覆盖已停止：{target}"
            )

        original = source.read_text(encoding="utf-8")

        # 备份原始代码
        backup_path = BACKUP / source.name
        shutil.copy2(source, backup_path)

        updated = replace_page_header(
            original,
            item["title"],
            item["description"],
            item["breadcrumb"],
        )

        target.write_text(updated, encoding="utf-8")

        print(f"[成功] 创建：{target.name}")

    # 2. 更新统一导航文件中的页面路径
    navigation_path = ROOT / "components" / "navigation.py"
    navigation_backup = BACKUP / "navigation.py"

    shutil.copy2(navigation_path, navigation_backup)

    navigation = navigation_path.read_text(encoding="utf-8")

    navigation = navigation.replace(
        "07_AI测试用例生成.py",
        "11_AI测试用例生成.py",
    )

    navigation = navigation.replace(
        "08_测试用例管理.py",
        "12_测试用例管理.py",
    )

    navigation_path.write_text(
        navigation,
        encoding="utf-8",
    )

    print("[成功] 更新 components/navigation.py")

    # 3. 移动旧页面到 legacy_pages，保留原文件
    for item in FILES:
        source = item["source"]
        legacy_target = LEGACY / source.name

        if legacy_target.exists():
            raise FileExistsError(
                f"旧页面归档目标已存在：{legacy_target}"
            )

        shutil.move(str(source), str(legacy_target))
        print(f"[归档] {source.name} -> legacy_pages/")

    print()
    print("迁移完成。")
    print(f"原始文件备份位置：{BACKUP}")
    print("请检查导航 URL 是否唯一，再进行统一验收。")


if __name__ == "__main__":
    main()
