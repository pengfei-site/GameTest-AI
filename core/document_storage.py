from pathlib import Path
from uuid import uuid4
import re

from database.connection import BASE_DIR


DOCUMENT_STORAGE_DIR = BASE_DIR / "data" / "documents"


def save_original_document(project_id: str, document_id: str, file_name: str, file_bytes: bytes) -> str:
    """按项目和版本保存原始上传文件，返回相对项目根目录的路径。"""
    suffix = Path(file_name).suffix.lower()
    if not suffix or suffix not in {".docx", ".pdf", ".md", ".txt"}:
        raise ValueError("不支持保存该文件类型")
    if not file_bytes:
        raise ValueError("原始文档内容为空")

    target_dir = DOCUMENT_STORAGE_DIR / str(project_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    original_name = Path(file_name).name
    safe_name = re.sub(r"[^\\w.()\\-]+", "_", original_name).strip("._") or f"document{suffix}"
    target_path = target_dir / f"{document_id}_{safe_name}"
    temp_path = target_path.with_suffix(target_path.suffix + f".{uuid4().hex}.tmp")
    try:
        temp_path.write_bytes(file_bytes)
        temp_path.replace(target_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return target_path.relative_to(BASE_DIR).as_posix()


def read_original_document(file_path: str) -> bytes | None:
    """读取数据库记录关联的原始文件；拒绝越界路径。"""
    if not file_path:
        return None
    root = BASE_DIR.resolve()
    target = (BASE_DIR / file_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("原始文档路径无效")
    if not target.is_file():
        return None
    return target.read_bytes()


def get_original_document_path(file_path: str) -> Path | None:
    """获取可供下载的原始文件路径。"""
    if not file_path:
        return None
    root = BASE_DIR.resolve()
    target = (BASE_DIR / file_path).resolve()
    if target != root and root not in target.parents:
        raise ValueError("原始文档路径无效")
    return target if target.is_file() else None
