from ragiac.ingestion.chunker import chunk_documents, chunk_markdown, strip_front_matter
from ragiac.ingestion.loader import Document

DOC = """---
subcategory: "Cloud Storage"
---

# google_storage_bucket

Creates a bucket.

## Example Usage

```hcl
resource "google_storage_bucket" "a" {
  name = "x"

  location = "EU"
}
```

## Argument Reference

* `name` - (Required) The bucket name.

* `location` - (Required) Where to create it.
"""


def test_strip_front_matter():
    assert strip_front_matter(DOC).lstrip().startswith("# google_storage_bucket")


def test_fenced_block_with_blank_line_is_not_split():
    chunks = chunk_markdown(DOC, chunk_size=400, overlap=20)
    example = [c for c in chunks if 'resource "google_storage_bucket"' in c]
    assert len(example) == 1
    assert 'location = "EU"' in example[0]  # the part after the blank line inside the fence


def test_chunks_carry_heading_path():
    chunks = chunk_markdown(DOC, chunk_size=400, overlap=20)
    assert any(c.startswith("[google_storage_bucket > Example Usage]") for c in chunks)
    assert any(c.startswith("[google_storage_bucket > Argument Reference]") for c in chunks)


def test_oversized_fence_is_split_into_well_formed_fences():
    body = "\n".join(f'  attr_{i} = "value_{i}"' for i in range(200))
    doc = f"# r\n\n```hcl\nresource \"x\" \"y\" {{\n{body}\n}}\n```\n"
    chunks = chunk_markdown(doc, chunk_size=600, overlap=20)
    assert len(chunks) > 1
    assert all(c.count("```") % 2 == 0 for c in chunks)
    assert all(len(c) <= 700 for c in chunks)


def test_no_heading_means_no_prefix():
    docs = [Document(doc_id="a.md", source="a.md", text="hello world")]
    assert chunk_documents(docs, 800, 120)[0].text == "hello world"


def test_non_markdown_uses_plain_splitter():
    docs = [Document(doc_id="a.tf", source="a.tf", text="# not a heading\n\nresource {}")]
    assert chunk_documents(docs, 800, 120)[0].text.startswith("# not a heading")
