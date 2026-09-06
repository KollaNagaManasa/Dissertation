"""Wires ingestion -> embeddings -> vector store -> retrieval -> generation -> validation,
selecting local (offline) or GCP-backed implementations based on Settings.ragiac_mode.
"""

from dataclasses import dataclass

from ragiac.config import Settings, get_settings
from ragiac.embeddings.base import Embedder
from ragiac.generation.baseline_generator import BaselineGenerator
from ragiac.generation.rag_generator import LLM, RagGenerator
from ragiac.ingestion.chunker import Chunk, chunk_documents
from ragiac.ingestion.loader import load_documents
from ragiac.retrieval.retriever import Retriever
from ragiac.validation.opa_validator import check_policies
from ragiac.validation.report import ValidationReport
from ragiac.validation.terraform_validator import validate_terraform
from ragiac.vectorstore.base import VectorStore


def build_embedder(settings: Settings) -> Embedder:
    if settings.is_gcp_mode:
        from ragiac.embeddings.vertex import VertexEmbedder

        return VertexEmbedder(settings)

    from ragiac.embeddings.local_tfidf import LocalTfidfEmbedder

    embedder = LocalTfidfEmbedder()
    embedder.load(settings.index_cache_dir / "local_tfidf.json")  # picks up a prior ingest(), if any
    return embedder


def build_vector_store(settings: Settings) -> VectorStore:
    if settings.is_gcp_mode:
        from ragiac.vectorstore.vertex_vector_search import VertexVectorSearchStore

        return VertexVectorSearchStore(settings)

    from ragiac.vectorstore.in_memory import InMemoryVectorStore

    return InMemoryVectorStore(cache_path=settings.index_cache_dir / "local_index.json")


def build_llm(settings: Settings) -> LLM:
    if settings.is_gcp_mode:
        from ragiac.generation.llm_vertex import VertexLLM

        return VertexLLM(settings)

    from ragiac.generation.stub_llm import StubLLM

    return StubLLM()


@dataclass
class Pipeline:
    settings: Settings
    embedder: Embedder
    vector_store: VectorStore
    retriever: Retriever
    rag_generator: RagGenerator
    baseline_generator: BaselineGenerator

    def ingest(self) -> int:
        documents = load_documents(self.settings)
        chunks: list[Chunk] = chunk_documents(documents, self.settings.chunk_size, self.settings.chunk_overlap)
        if not chunks:
            return 0

        if hasattr(self.embedder, "fit"):
            self.embedder.fit([c.text for c in chunks])  # LocalTfidfEmbedder needs a corpus fit pass
            if hasattr(self.embedder, "save"):
                self.embedder.save(self.settings.index_cache_dir / "local_tfidf.json")

        vectors = self.embedder.embed([c.text for c in chunks])
        self.vector_store.upsert(chunks, vectors)

        if hasattr(self.vector_store, "save"):
            self.vector_store.save()

        return len(chunks)

    def generate_rag(self, requirement: str) -> str:
        return self.rag_generator.generate(requirement)

    def generate_baseline(self, requirement: str) -> str:
        return self.baseline_generator.generate(requirement)

    def validate(self, hcl: str, run_plan: bool = True, check_opa: bool = True) -> ValidationReport:
        terraform_results = validate_terraform(hcl, self.settings, run_plan=run_plan)
        policy_result = check_policies(hcl, self.settings) if check_opa else None
        return ValidationReport(terraform_results=terraform_results, policy_result=policy_result)


def build_pipeline(settings: Settings | None = None) -> Pipeline:
    settings = settings or get_settings()
    embedder = build_embedder(settings)
    vector_store = build_vector_store(settings)

    if hasattr(vector_store, "load"):
        vector_store.load()  # picks up a previously-ingested local index, if present

    retriever = Retriever(embedder=embedder, vector_store=vector_store, top_k=settings.top_k)
    llm = build_llm(settings)

    return Pipeline(
        settings=settings,
        embedder=embedder,
        vector_store=vector_store,
        retriever=retriever,
        rag_generator=RagGenerator(retriever=retriever, llm=llm),
        baseline_generator=BaselineGenerator(llm=llm),
    )
