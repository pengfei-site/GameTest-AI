
from io import BytesIO
from pathlib import Path

import pymupdf

from docx import Document


def _decode_text(file_bytes: bytes) -> str:
    """统一处理文本文件编码。"""

    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError("文件编码无法识别，目前支持 UTF-8 和 GB18030")


def _build_result(
    content: str,
    file_type: str,
    page_count: int | None = None,
) -> dict:
    """统一构建解析结果。"""

    content = content.strip()

    if not content:
        raise ValueError("文档中没有提取到有效文本")

    return {
        "content": content,
        "file_type": file_type,
        "page_count": page_count,
        "char_count": len(content),
    }


def parse_document(file_name: str, file_bytes: bytes) -> dict:
    """
    解析游戏策划文档。

    支持：DOCX、PDF、MD、TXT
    """

    suffix = Path(file_name).suffix.lower()

    if not file_bytes:
        raise ValueError("上传的文件内容为空")

    if suffix == ".docx":
        return parse_docx(file_bytes)

    elif suffix == ".pdf":
        return parse_pdf(file_bytes)

    elif suffix == ".md":
        return parse_markdown(file_bytes)

    elif suffix == ".txt":
        return parse_txt(file_bytes)

    else:
        raise ValueError(f"暂不支持该文件类型：{suffix}")


def parse_docx(file_bytes: bytes) -> dict:
    """解析 Word 文档。"""

    try:
        doc = Document(BytesIO(file_bytes))
    except Exception as e:
        raise ValueError(f"Word 文档解析失败，文件可能已损坏：{e}") from e

    content = []

    # 提取段落
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            content.append(text)

    # 提取表格
    for table in doc.tables:
        for row in table.rows:
            cells = [
                cell.text.strip().replace("\n", " / ")
                for cell in row.cells
            ]
            content.append(" | ".join(cells))

    text = "\n".join(content)

    return _build_result(text, "DOCX")


def parse_pdf(file_bytes: bytes) -> dict:
    """解析 PDF 文档。"""

    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"PDF 文件无法打开，可能已损坏：{e}") from e

    try:
        if doc.needs_pass:
            raise ValueError("PDF 文件已加密，暂不支持解析")

        content = []

        for page in doc:
            text = page.get_text("text").strip()
            if text:
                content.append(text)

        page_count = len(doc)

    except ValueError:
        raise

    except Exception as e:
        raise ValueError(f"PDF 文本提取失败：{e}") from e

    finally:
        doc.close()

    text = "\n\n".join(content)

    if not text.strip():
        raise ValueError(
            "PDF 未提取到文本，可能是扫描版 PDF，暂不支持 OCR"
        )

    return _build_result(text, "PDF", page_count)


def parse_markdown(file_bytes: bytes) -> dict:
    """解析 Markdown 文档。"""

    text = _decode_text(file_bytes)

    return _build_result(text, "MD")


def parse_txt(file_bytes: bytes) -> dict:
    """解析 TXT 文本文件。"""

    text = _decode_text(file_bytes)

    return _build_result(text, "TXT")
