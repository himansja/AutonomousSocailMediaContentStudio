"""
read_file_tool — reads text content from an uploaded file.

Supports .txt, .md, .rst, .csv, and .pdf files.
Used by the plan_node to extract source material from a user-uploaded blog post
or document before building the content strategy.
"""
from pathlib import Path

from langchain_core.tools import tool


_TEXT_EXTENSIONS = {".txt", ".md", ".rst", ".csv"}


@tool
def read_uploaded_file(file_path: str, max_chars: int = 8000) -> str:
    """
    Read the text content of an uploaded file.

    Supports .txt, .md, .rst, .csv, and .pdf files.

    Args:
        file_path: Absolute or relative path to the uploaded file.
        max_chars: Maximum characters to return (default 8000).

    Returns the extracted text content of the file, or an error message.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        return f"File not found: {file_path}"

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            text = "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
            return text[:max_chars]
        except ImportError:
            return (
                "PDF support requires pypdf. "
                "Install it with: pip install pypdf"
            )
        except Exception as exc:
            return f"Error reading PDF: {exc}"

    if suffix in _TEXT_EXTENSIONS:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]
        except Exception as exc:
            return f"Error reading file: {exc}"

    return (
        f"Unsupported file type: {suffix}. "
        "Supported types: .txt, .md, .rst, .csv, .pdf"
    )
