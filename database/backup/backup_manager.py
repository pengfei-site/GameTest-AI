import sqlite3
import re
import uuid
import os

from pathlib import Path
from database.connection import DB_PATH


def check_database_integrity(db_path: str | Path = DB_PATH) -> dict:
    """
    检查 SQLite 数据库完整性。

    返回：
    {
        "passed": bool,
        "messages": list[str]
    }
    """
    db_path = Path(db_path)

    if not db_path.exists():
        return {
            "passed": False,
            "messages": [f"数据库文件不存在：{db_path}"]
        }

    try:
        conn = sqlite3.connect(str(db_path))

        try:
            result = conn.execute(
                "PRAGMA integrity_check"
            ).fetchall()

            messages = [row[0] for row in result]

            passed = (
                len(messages) == 1
                and messages[0] == "ok"
            )

            return {
                "passed": passed,
                "messages": messages
            }

        finally:
            conn.close()

    except sqlite3.Error as exc:
        return {
            "passed": False,
            "messages": [f"数据库检查失败：{exc}"]
        }


from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[2]
BACKUP_DIR = BASE_DIR / "backups"

VALID_BACKUP_TYPES = ("auto", "manual")


def create_backup(backup_type: str = "manual") -> dict:
    """
    创建 SQLite 数据库备份。

    auto：自动备份，后续只保留最近10份。
    manual：手动备份，不自动清理。
    """

    if backup_type not in VALID_BACKUP_TYPES:
        raise ValueError(
            "backup_type 只能是 auto 或 manual"
        )

    source_path = Path(DB_PATH)

    if not source_path.exists():
        raise FileNotFoundError(
            f"原数据库不存在：{source_path}"
        )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_name = f"{backup_type}_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_name

    source_conn = None
    backup_conn = None

    try:
        source_conn = sqlite3.connect(str(source_path))
        backup_conn = sqlite3.connect(str(backup_path))

        source_conn.backup(backup_conn)

        backup_conn.close()
        backup_conn = None

        source_conn.close()
        source_conn = None

        integrity = check_database_integrity(backup_path)

        if not integrity["passed"]:
            raise RuntimeError(
                f"备份完整性检查失败：{integrity['messages']}"
            )

        if backup_type == "auto":
            cleanup_auto_backups()

        return {
            "success": True,
            "backup_name": backup_name,
            "backup_path": str(backup_path),
            "backup_type": backup_type,
            "integrity": integrity
        }

    except Exception:
        if backup_conn is not None:
            backup_conn.close()

        if source_conn is not None:
            source_conn.close()

        if backup_path.exists():
            backup_path.unlink()

        raise


def cleanup_auto_backups(keep: int = 10) -> int:
    """
    自动备份仅保留最近 keep 份。
    手动备份不参与清理。
    """

    if keep < 1:
        raise ValueError("keep 必须大于等于1")

    if not BACKUP_DIR.exists():
        return 0

    auto_backups = sorted(
        BACKUP_DIR.glob("auto_*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True
    )

    deleted_count = 0

    for old_backup in auto_backups[keep:]:
        old_backup.unlink()
        deleted_count += 1

    return deleted_count


def list_backups() -> list[dict]:
    """
    获取所有有效备份，按创建时间倒序排列。
    """

    if not BACKUP_DIR.exists():
        return []

    backups = []

    for path in BACKUP_DIR.iterdir():
        if not path.is_file():
            continue

        if not re.fullmatch(
            r"(auto|manual)_\d{8}_\d{6}_\d+\.db",
            path.name
        ):
            continue

        stat = path.stat()

        backups.append({
            "backup_name": path.name,
            "backup_type": path.name.split("_", 1)[0],
            "backup_path": str(path),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(
                stat.st_mtime
            ).strftime("%Y-%m-%d %H:%M:%S"),
        })

    backups.sort(
        key=lambda item: item["created_at"],
        reverse=True
    )

    return backups


def delete_backup(backup_name: str) -> dict:
    """
    删除指定备份。

    安全规则：
    1. 只能传入备份文件名，不能传入路径。
    2. 只能删除 auto 或 manual 类型的有效备份。
    3. 禁止删除备份目录之外的文件。
    4. 文件不存在时返回明确错误。
    """

    if not isinstance(backup_name, str) or not backup_name:
        raise ValueError("备份文件名不能为空")

    if Path(backup_name).name != backup_name:
        raise ValueError("只能传入备份文件名，不能传入路径")

    if not re.fullmatch(
        r"(auto|manual)_\d{8}_\d{6}_\d+\.db",
        backup_name
    ):
        raise ValueError("备份文件名格式不合法")

    backup_path = (BACKUP_DIR / backup_name).resolve()
    backup_root = BACKUP_DIR.resolve()

    if backup_path.parent != backup_root:
        raise ValueError("禁止删除备份目录之外的文件")

    if not backup_path.is_file():
        raise FileNotFoundError(
            f"备份文件不存在：{backup_name}"
        )

    backup_path.unlink()

    return {
        "success": True,
        "backup_name": backup_name,
        "message": "备份文件删除成功"
    }


def prepare_restore(backup_name: str) -> dict:
    """
    校验备份文件，并生成经过完整性检查的临时恢复数据库。

    本函数不会修改正式数据库。
    """

    if not isinstance(backup_name, str) or not backup_name:
        raise ValueError("备份文件名不能为空")

    if Path(backup_name).name != backup_name:
        raise ValueError("只能传入备份文件名，不能传入路径")

    if not re.fullmatch(
        r"(auto|manual)_\d{8}_\d{6}_\d+\.db",
        backup_name
    ):
        raise ValueError("备份文件名格式不合法")

    backup_root = BACKUP_DIR.resolve()
    backup_path = (BACKUP_DIR / backup_name).resolve()

    if backup_path.parent != backup_root:
        raise ValueError("禁止访问备份目录之外的文件")

    if not backup_path.is_file():
        raise FileNotFoundError(
            f"备份文件不存在：{backup_name}"
        )

    # 第一次检查：确认源备份数据库完整
    source_integrity = check_database_integrity(backup_path)

    if not source_integrity["passed"]:
        raise RuntimeError(
            f"备份文件完整性检查失败：{source_integrity['messages']}"
        )

    # 临时文件放在正式数据库同一目录，便于后续安全替换
    db_path = Path(DB_PATH)
    temp_name = (
        f"{db_path.stem}_restore_{uuid.uuid4().hex}.db"
    )
    temp_path = db_path.parent / temp_name

    source_conn = None
    temp_conn = None

    try:
        source_conn = sqlite3.connect(str(backup_path))
        temp_conn = sqlite3.connect(str(temp_path))

        # 使用 SQLite Backup API 复制数据库
        source_conn.backup(temp_conn)

        temp_conn.close()
        temp_conn = None

        source_conn.close()
        source_conn = None

        # 第二次检查：确认临时恢复文件完整
        temp_integrity = check_database_integrity(temp_path)

        if not temp_integrity["passed"]:
            raise RuntimeError(
                f"临时恢复文件完整性检查失败：{temp_integrity['messages']}"
            )

        return {
            "success": True,
            "backup_name": backup_name,
            "temp_path": str(temp_path),
            "source_integrity": source_integrity,
            "temp_integrity": temp_integrity,
            "message": "临时恢复文件创建成功，正式数据库未修改"
        }

    except Exception:
        if temp_conn is not None:
            temp_conn.close()

        if source_conn is not None:
            source_conn.close()

        if temp_path.exists():
            temp_path.unlink()

        raise



def restore_backup(backup_name: str) -> dict:
    """
    安全恢复数据库。

    流程：
    1. 准备并校验临时恢复文件。
    2. 自动备份当前正式数据库。
    3. 从自动备份生成独立回滚文件。
    4. 检查 WAL 状态。
    5. 替换正式数据库。
    6. 检查恢复结果。
    7. 失败时使用回滚文件恢复原数据库。

    如果回滚失败，保留回滚临时文件，供人工恢复。
    """

    db_path = Path(DB_PATH)
    restore_temp_path = None
    rollback_temp_path = None
    preserve_rollback_temp = False

    # 第一步：生成并检查临时恢复文件
    prepared = prepare_restore(backup_name)

    if not prepared.get("success"):
        raise RuntimeError(
            f"恢复准备失败：{prepared.get('message', '未知原因')}"
        )

    restore_temp_path = Path(prepared["temp_path"])

    try:
        # 第二步：备份当前正式数据库
        rollback_backup = create_backup("auto")

        if not rollback_backup.get("success"):
            raise RuntimeError("恢复前自动备份失败，已终止恢复")

        rollback_backup_path = Path(
            rollback_backup["backup_path"]
        )

        # 第三步：从自动备份生成独立回滚文件
        rollback_temp_path = (
            db_path.parent
            / f"{db_path.stem}_rollback_{uuid.uuid4().hex}.db"
        )

        source_conn = None
        rollback_conn = None

        try:
            source_conn = sqlite3.connect(
                str(rollback_backup_path)
            )
            rollback_conn = sqlite3.connect(
                str(rollback_temp_path)
            )

            source_conn.backup(rollback_conn)

        finally:
            if rollback_conn is not None:
                rollback_conn.close()

            if source_conn is not None:
                source_conn.close()

        rollback_integrity = check_database_integrity(
            rollback_temp_path
        )

        if not rollback_integrity["passed"]:
            raise RuntimeError(
                "回滚文件完整性检查失败，已终止恢复"
            )

        # 第四步：检查正式数据库 WAL 状态
        checkpoint_conn = sqlite3.connect(str(db_path))

        try:
            checkpoint_result = checkpoint_conn.execute(
                "PRAGMA wal_checkpoint(TRUNCATE)"
            ).fetchone()

            if checkpoint_result and checkpoint_result[0] != 0:
                raise RuntimeError(
                    "数据库 WAL 检查点执行失败，可能存在其他连接"
                )

        finally:
            checkpoint_conn.close()

        wal_path = Path(str(db_path) + "-wal")
        shm_path = Path(str(db_path) + "-shm")

        if wal_path.exists() or shm_path.exists():
            raise RuntimeError(
                "数据库仍存在 WAL/SHM 文件，请关闭其他数据库连接后重试"
            )

        # 第五步：替换正式数据库
        os.replace(restore_temp_path, db_path)
        restore_temp_path = None

        # 第六步：检查恢复后的正式数据库
        restored_integrity = check_database_integrity(db_path)

        if not restored_integrity["passed"]:

            # 第七步：尝试回滚
            try:
                os.replace(rollback_temp_path, db_path)
                rollback_temp_path = None

                rollback_check = check_database_integrity(db_path)

                if not rollback_check["passed"]:
                    raise RuntimeError(
                        "回滚后的数据库完整性检查失败"
                    )

            except Exception as rollback_error:

                # 回滚失败时，保留回滚临时文件
                if rollback_temp_path and rollback_temp_path.exists():
                    preserve_rollback_temp = True
                    raise RuntimeError(
                        "数据库恢复失败，且自动回滚失败。"
                        f"请保留回滚文件并进行人工恢复："
                        f"{rollback_temp_path}。"
                        f"具体错误：{rollback_error}"
                    )

                raise RuntimeError(
                    "数据库恢复后的完整性检查失败，"
                    f"自动回滚也未能完成：{rollback_error}"
                )

            raise RuntimeError(
                "恢复后的数据库完整性检查失败，"
                "已成功回滚到恢复前的数据库"
            )

        return {
            "success": True,
            "backup_name": backup_name,
            "rollback_backup_name": rollback_backup["backup_name"],
            "integrity": restored_integrity,
            "message": "数据库恢复成功"
        }

    finally:
        # 清理未使用的恢复临时文件
        if restore_temp_path and restore_temp_path.exists():
            restore_temp_path.unlink()

        # 回滚失败时，绝不删除回滚临时文件
        if (
            not preserve_rollback_temp
            and rollback_temp_path
            and rollback_temp_path.exists()
        ):
            rollback_temp_path.unlink()


