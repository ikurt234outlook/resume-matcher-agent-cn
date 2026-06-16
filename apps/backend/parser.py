"""
文档解析：从 PDF / DOCX 提取纯文本。
逻辑照搬自旧版 resume_service.py，仅去掉类封装。
"""
import io
import zipfile
import xml.etree.ElementTree as ET

from pdfminer.high_level import extract_text

# DOCX 段落命名空间
_WML_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_pdf(file_bytes: bytes) -> str:
    """用 pdfminer 提取 PDF 文本。"""
    return extract_text(io.BytesIO(file_bytes))


def extract_docx(file_bytes: bytes) -> str:
    """
    手写 zip+xml 解析 DOCX（仅依赖标准库，不装 python-docx）。
    按文档序输出，遇 <w:tab> 插入 \\t、<w:br> 插入 \\n、<w:p> 末尾换行。
    这样双列布局的简历（个人信息｜联系方式）不会被压成一团。
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as docx:
            document_xml = docx.read("word/document.xml")
    except KeyError as e:
        raise ValueError("Invalid DOCX file: missing word/document.xml") from e
    except zipfile.BadZipFile as e:
        raise ValueError("Invalid DOCX file") from e

    root = ET.fromstring(document_xml)
    out: list[str] = []
    # 文档序遍历；遇到段落结束再加 \n
    for elem in root.iter():
        tag = elem.tag
        if tag == f"{_WML_NS}t" and elem.text:
            out.append(elem.text)
        elif tag == f"{_WML_NS}tab":
            out.append("\t")
        elif tag == f"{_WML_NS}br":
            out.append("\n")
        elif tag == f"{_WML_NS}p" and out and not out[-1].endswith("\n"):
            out.append("\n")
    return "".join(out)


def extract_text_from_file(file_bytes: bytes, content_type: str) -> str:
    """
    根据 MIME 类型提取文本。

    content_type: application/pdf 或
                  application/vnd.openxmlformats-officedocument.wordprocessingml.document
    """
    if content_type == "application/pdf":
        text = extract_pdf(file_bytes)
    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = extract_docx(file_bytes)
    else:
        raise ValueError("Unsupported file type")

    text = text.strip()
    if not text:
        raise ValueError("No text could be extracted from the uploaded file")
    return text
