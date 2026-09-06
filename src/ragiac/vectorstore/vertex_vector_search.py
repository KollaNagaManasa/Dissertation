"""Vertex AI Vector Search (Matching Engine) backed vector store.

Assumes an index and a deployed index endpoint have already been provisioned
separately (e.g. via Terraform's `google_vertex_ai_index` /
`google_vertex_ai_index_endpoint` resources — fittingly, the same kind of IaC
this assistant generates). This wrapper only handles upserting datapoints and
querying the deployed endpoint at runtime.
"""

from ragiac.config import Settings
from ragiac.ingestion.chunker import Chunk
from ragiac.vectorstore.base import ScoredChunk


class VertexVectorSearchStore:
    def __init__(self, settings: Settings):
        if not (settings.vertex_vector_index_id and settings.vertex_vector_endpoint_id):
            raise ValueError(
                "VERTEX_VECTOR_INDEX_ID and VERTEX_VECTOR_ENDPOINT_ID must be set to use "
                "VertexVectorSearchStore. Provision these via Terraform before switching "
                "RAGIAC_MODE=gcp."
            )

        import vertexai
        from google.cloud import aiplatform

        vertexai.init(project=settings.google_cloud_project, location=settings.google_cloud_region)
        self._settings = settings
        self._index = aiplatform.MatchingEngineIndex(settings.vertex_vector_index_id)
        self._endpoint = aiplatform.MatchingEngineIndexEndpoint(settings.vertex_vector_endpoint_id)
        self._chunk_by_id: dict[str, Chunk] = {}

    def upsert(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        datapoints = [
            {"datapoint_id": chunk.chunk_id, "feature_vector": vector}
            for chunk, vector in zip(chunks, vectors)
        ]
        self._index.upsert_datapoints(datapoints=datapoints)
        for chunk in chunks:
            self._chunk_by_id[chunk.chunk_id] = chunk

    def search(self, query_vector: list[float], top_k: int) -> list[ScoredChunk]:
        response = self._endpoint.find_neighbors(
            deployed_index_id=self._settings.vertex_vector_deployed_index_id,
            queries=[query_vector],
            num_neighbors=top_k,
        )
        results: list[ScoredChunk] = []
        for neighbor in response[0]:
            chunk = self._chunk_by_id.get(neighbor.id)
            if chunk is not None:
                results.append(ScoredChunk(chunk=chunk, score=neighbor.distance))
        return results
