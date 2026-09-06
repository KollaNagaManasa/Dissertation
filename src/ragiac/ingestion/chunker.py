"""Recursive, paragraph-aware chunking for provider docs and Terraform snippets."""

from dataclasses import dataclass

from ragiac.ingestion.loader import Document


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    source: str
    text: str


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue

        if buffer:
            chunks.append(buffer)
        if len(paragraph) <= chunk_size:
            buffer = paragraph
        else:
            # Paragraph itself exceeds chunk_size: hard-split with overlap.
            start = 0
            while start < len(paragraph):
                end = start + chunk_size
                chunks.append(paragraph[start:end])
                start = end - overlap
            buffer = ""

    if buffer:
        chunks.append(buffer)

    return chunks


def chunk_documents(documents: list[Document], chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in documents:
        for i, text in enumerate(chunk_text(doc.text, chunk_size, overlap)):
            chunks.append(Chunk(chunk_id=f"{doc.doc_id}::{i}", doc_id=doc.doc_id, source=doc.source, text=text))
    return chunks
