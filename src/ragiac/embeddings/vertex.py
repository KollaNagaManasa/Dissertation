"""Vertex AI embeddings (text-embedding-005 by default).

Requires `google-cloud-aiplatform` and a GCP project with the Vertex AI API
enabled; authenticate with `gcloud auth application-default login`.
"""

from ragiac.config import Settings


class VertexEmbedder:
    dimension = 768  # text-embedding-005 output size

    def __init__(self, settings: Settings):
        from vertexai.language_models import TextEmbeddingModel
        import vertexai

        vertexai.init(project=settings.google_cloud_project, location=settings.google_cloud_region)
        self._model = TextEmbeddingModel.from_pretrained(settings.vertex_embedding_model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.get_embeddings(texts)
        return [e.values for e in embeddings]
