
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库文件目录
DATA_DIR = BASE_DIR / "data"

# SQLite 数据库文件
DB_PATH = DATA_DIR / "gametest_ai.db"


@contextmanager
def get_connection(*, write: bool = False):
    """
    获取 SQLite 数据库连接。

    参数：
        write:
            False：普通数据库连接，不触发自动备份。
            True：写入连接，执行写入前先创建自动备份。

    自动处理：
        - 写入前自动备份
        - 自动备份失败：阻断数据库连接和后续写入
        - 正常结束：提交事务
        - 发生异常：回滚事务
        - 最后：关闭数据库连接

    使用方式：

        # 普通查询
        with get_connection() as conn:
            conn.execute(...)

        # 数据变更
        with get_connection(write=True) as conn:
            conn.execute(...)
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 写入前执行自动备份
    if write:
        # 使用局部导入，避免 connection.py 与 backup_manager.py
        # 在模块加载时产生循环导入
        from database.backup.backup_manager import create_backup

        backup_result = create_backup("auto")

        if not backup_result.get("success"):
            raise RuntimeError(
                "数据库自动备份失败，已阻断本次数据变更。"
            )

    # 创建数据库连接
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
