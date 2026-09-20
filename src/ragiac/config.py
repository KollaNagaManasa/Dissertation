"""Central settings, loaded from environment variables / .env.

RAGIAC_MODE selects which embedder, vector store and LLM implementations
pipeline.py wires together — "local" needs no GCP credentials, "gcp" targets
Vertex AI + Vertex AI Vector Search for the real dissertation experiments.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ragiac_mode: str = "local"  # "local" | "gcp"

    google_cloud_project: str = ""
    # asia-south1 (Mumbai) is the nearest live GCP region to Hyderabad (~600km, vs. ~1350km
    # for asia-south2/Delhi) at the same India pricing tier — used for all data-at-rest
    # (GCS, Vector Search index) and as the default compute/embedding location.
    google_cloud_region: str = "asia-south1"
    # Gemini generation calls use the global endpoint by default: newer Gemini models are
    # sometimes global-only before they roll out to regional endpoints, so pinning generation
    # to asia-south1 can silently lose access to the latest model. Data residency still holds
    # for storage/vector search, which stay pinned to google_cloud_region above.
    vertex_generation_location: str = "global"
    gcs_bucket: str = ""
    gcs_knowledge_base_prefix: str = "knowledge_base/"

    vertex_embedding_model: str = "text-embedding-005"
    # gemini-2.0-flash has aged out of Vertex AI's Model Garden (404s). gemini-2.5-flash still
    # works but is slated to shut down 2026-10-20, inside this dissertation's own timeline, so
    # default to the current GA flash model instead — verify against
    # https://docs.cloud.google.com/vertex-ai/generative-ai/docs/learn/locations before relying
    # on this value, since Gemini model availability shifts over the project's lifetime.
    vertex_generation_model: str = "gemini-3.8-flash"
    vertex_vector_index_id: str = ""
    vertex_vector_endpoint_id: str = ""
    vertex_vector_deployed_index_id: str = ""

    terraform_binary: str = "terraform"
    conftest_binary: str = "conftest"

    knowledge_base_dir: Path = Path("data/knowledge_base")
    policy_dir: Path = Path("data/policies")
    index_cache_dir: Path = Path("data/index")

    results_dir: Path = Path("results")
    cache_dir: Path = Path("data/cache")  # embedding + terraform-provider caches; safe to keep when resetting data/index
    tf_plugin_cache_dir: Path = Path("data/cache/tf_plugin_cache")

    # Provider-doc sections (argument references, examples) are long, and fenced HCL examples
    # are kept whole by the markdown chunker, so chunks run larger than plain-prose defaults.
    chunk_size: int = 1500
    chunk_overlap: int = 150
    top_k: int = 8
    max_chunks_per_doc: int = 3  # 0 disables the per-document cap (retrieval ablation)

    # Sampling temperature for generation. pass@k needs stochastic sampling (temperature > 0);
    # record this alongside every benchmark run.
    generation_temperature: float = 0.2
    embedding_batch_size: int = 30
    api_max_retries: int = 12

    @property
    def is_gcp_mode(self) -> bool:
        return self.ragiac_mode.lower() == "gcp"


def get_settings() -> Settings:
    return Settings()
