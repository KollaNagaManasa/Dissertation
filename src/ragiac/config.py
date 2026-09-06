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
    vertex_generation_model: str = "gemini-2.0-flash"
    vertex_vector_index_id: str = ""
    vertex_vector_endpoint_id: str = ""
    vertex_vector_deployed_index_id: str = ""

    terraform_binary: str = "terraform"
    conftest_binary: str = "conftest"

    knowledge_base_dir: Path = Path("data/knowledge_base")
    policy_dir: Path = Path("data/policies")
    index_cache_dir: Path = Path("data/index")

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 5

    @property
    def is_gcp_mode(self) -> bool:
        return self.ragiac_mode.lower() == "gcp"


def get_settings() -> Settings:
    return Settings()
