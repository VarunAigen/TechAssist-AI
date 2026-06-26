"""Text chunker — splits documents into overlapping chunks for embedding."""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings


def chunk_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: The full document text to chunk.
        chunk_size: Max characters per chunk (default from settings).
        chunk_overlap: Character overlap between chunks (default from settings).

    Returns:
        List of text chunks.
    """
    if not text or not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)
    # Filter out very small chunks (less than 20 chars)
    return [c.strip() for c in chunks if len(c.strip()) >= 20]
