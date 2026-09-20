"""Chunking for provider docs and Terraform snippets.

`chunk_text` is the plain paragraph-aware splitter. `chunk_markdown` additionally respects
document structure: fenced code blocks (HCL examples) are never split at blank lines, and each
chunk is prefixed with its heading path (e.g. "[google_storage_bucket > Argument Reference]")
so a chunk from the middle of a long argument list still says which resource it describes.
"""

import re
from dataclasses import dataclass

from ragiac.ingestion.loader import Document

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_MAX_HEADING_DEPTH = 3


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


def strip_front_matter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1 :])
    return text


def _split_sections(text: str) -> list[tuple[list[str], list[str]]]:
    """Returns [(heading_path, blocks)]; a block is a paragraph or one whole fenced code block."""
    sections: list[tuple[list[str], list[str]]] = []
    path: list[str] = []
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False

    def flush_paragraph() -> None:
        if current:
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current.clear()

    def close_section() -> None:
        flush_paragraph()
        if blocks:
            sections.append((list(path), list(blocks)))
        blocks.clear()

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if not in_fence:
                flush_paragraph()
                in_fence = True
                current.append(line)
            else:
                current.append(line)
                in_fence = False
                blocks.append("\n".join(current))
                current.clear()
            continue

        if in_fence:
            current.append(line)
            continue

        heading = _HEADING_RE.match(line)
        if heading:
            close_section()
            level = len(heading.group(1))
            path = path[: level - 1] + [heading.group(2)]
            continue

        if not line.strip():
            flush_paragraph()
        else:
            current.append(line)

    if in_fence:  # unterminated fence: keep what we have rather than dropping it
        blocks.append("\n".join(current))
        current.clear()
    close_section()
    return sections


def _split_oversized_block(block: str, limit: int, overlap: int) -> list[str]:
    if block.startswith("```"):
        lines = block.splitlines()
        opener = lines[0]
        body = lines[1:-1] if len(lines) > 1 and lines[-1].strip().startswith("```") else lines[1:]
        pieces: list[str] = []
        current: list[str] = []
        size = 0
        for line in body:
            if current and size + len(line) + 1 > limit - 10:
                pieces.append("\n".join([opener, *current, "```"]))
                current, size = [], 0
            current.append(line)
            size += len(line) + 1
        if current:
            pieces.append("\n".join([opener, *current, "```"]))
        return pieces
    return chunk_text(block, limit, min(overlap, limit - 1))


def chunk_markdown(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: list[str] = []
    for path, blocks in _split_sections(strip_front_matter(text)):
        prefix = f"[{' > '.join(path[:_MAX_HEADING_DEPTH])}]\n" if path else ""
        limit = max(chunk_size - len(prefix), chunk_size // 2)

        packed: list[str] = []
        buffer = ""
        for block in blocks:
            pieces = [block] if len(block) <= limit else _split_oversized_block(block, limit, overlap)
            for piece in pieces:
                candidate = f"{buffer}\n\n{piece}" if buffer else piece
                if len(candidate) <= limit:
                    buffer = candidate
                else:
                    if buffer:
                        packed.append(buffer)
                    buffer = piece
        if buffer:
            packed.append(buffer)

        chunks.extend(f"{prefix}{p}" for p in packed)
    return chunks


def chunk_documents(documents: list[Document], chunk_size: int, overlap: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in documents:
        splitter = chunk_markdown if doc.doc_id.lower().endswith(".md") else chunk_text
        for i, text in enumerate(splitter(doc.text, chunk_size, overlap)):
            chunks.append(Chunk(chunk_id=f"{doc.doc_id}::{i}", doc_id=doc.doc_id, source=doc.source, text=text))
    return chunks
