"""Document parser — handles PDF, DOCX, MD, and TXT files."""

import os
from pathlib import Path


def parse_document(file_path: str) -> str:
    """Parse a document file and return its text content.

    Supports: .pdf, .docx, .md, .txt
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext == ".docx":
        return _parse_docx(file_path)
    elif ext in (".md", ".txt"):
        return _parse_text(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: .pdf, .docx, .md, .txt")


def _parse_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text.strip())
    return "\n\n".join(text_parts)


def _parse_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(file_path)
    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())
    return "\n\n".join(text_parts)


def _parse_text(file_path: str) -> str:
    """Read a text or markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def get_file_type(filename: str) -> str:
    """Get the file type from filename."""
    return Path(filename).suffix.lower().lstrip(".")
