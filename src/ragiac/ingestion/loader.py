"""Loads the IaC knowledge base (GCP/Terraform docs, best-practice templates).

In "gcp" mode, documents are pulled from a GCS bucket so the knowledge base can
be curated/updated without redeploying the assistant. In "local" mode, the same
interface reads from a local directory (data/knowledge_base) for offline dev.
"""

from dataclasses import dataclass
from pathlib import Path

from ragiac.config import Settings


@dataclass(frozen=True)
class Document:
    doc_id: str
    source: str
    text: str


def load_local_documents(directory: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".tf"}:
            text = path.read_text(encoding="utf-8")
            docs.append(Document(doc_id=str(path.relative_to(directory)), source=str(path), text=text))
    return docs


def load_gcs_documents(settings: Settings) -> list[Document]:
    """Pulls knowledge-base files from gs://{settings.gcs_bucket}/{gcs_knowledge_base_prefix}.

    Requires `google-cloud-storage` and application-default credentials
    (`gcloud auth application-default login`) with read access to the bucket.
    """
    from google.cloud import storage  # imported lazily so local mode has no GCP dependency

    if not settings.gcs_bucket:
        raise ValueError("GCS_BUCKET must be set to load documents in gcp mode")

    client = storage.Client(project=settings.google_cloud_project or None)
    bucket = client.bucket(settings.gcs_bucket)
    docs: list[Document] = []
    for blob in bucket.list_blobs(prefix=settings.gcs_knowledge_base_prefix):
        if blob.name.endswith("/"):
            continue
        text = blob.download_as_text()
        docs.append(Document(doc_id=blob.name, source=f"gs://{settings.gcs_bucket}/{blob.name}", text=text))
    return docs


def load_documents(settings: Settings) -> list[Document]:
    if settings.is_gcp_mode and settings.gcs_bucket:
        return load_gcs_documents(settings)
    return load_local_documents(settings.knowledge_base_dir)
