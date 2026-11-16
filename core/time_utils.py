from datetime import datetime, timezone


def format_local_datetime(value):
    """
    将数据库 UTC 时间转换为系统本地时间。

    SQLite CURRENT_TIMESTAMP 返回的时间没有时区信息，
    因此统一按 UTC 处理。
    """

    if not value:
        return "暂无"

    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return value

    elif isinstance(value, datetime):
        dt = value

    else:
        return str(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local_dt = dt.astimezone()

    return local_dt.strftime("%Y-%m-%d %H:%M:%S")