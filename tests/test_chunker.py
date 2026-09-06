from ragiac.ingestion.chunker import Chunk, chunk_documents, chunk_text
from ragiac.ingestion.loader import Document


def test_chunk_text_keeps_short_text_as_one_chunk():
    text = "short paragraph"
    chunks = chunk_text(text, chunk_size=800, overlap=120)
    assert chunks == ["short paragraph"]


def test_chunk_text_splits_long_paragraph_with_overlap():
    text = "a" * 2000
    chunks = chunk_text(text, chunk_size=800, overlap=120)
    assert len(chunks) > 1
    # consecutive chunks overlap
    assert chunks[0][-120:] == chunks[1][:120]


def test_chunk_text_groups_paragraphs_up_to_chunk_size():
    paragraphs = ["para one.", "para two.", "para three."]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, chunk_size=1000, overlap=10)
    assert len(chunks) == 1
    assert all(p in chunks[0] for p in paragraphs)


def test_chunk_documents_produces_stable_ids():
    docs = [Document(doc_id="a.md", source="a.md", text="hello world")]
    chunks = chunk_documents(docs, chunk_size=800, overlap=120)
    assert chunks == [Chunk(chunk_id="a.md::0", doc_id="a.md", source="a.md", text="hello world")]
