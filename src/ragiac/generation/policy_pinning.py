"""`rag_policy` arm: RAG with organisational policy pinned into the prompt instead of ranked.

Retrieval ranks documents by similarity to the requirement, and a requirement describes a resource,
not the policies that apply to it, so cross-cutting policy loses to resource-specific provider
documentation (main-01: the conventions document reached only 12% of RAG prompts; indexing a
policy page per resource type raised that to 36.4% and still left Kubernetes compliance flat).
This arm stops relying on ranking for policy. It retrieves as usual, then looks at which provider
pages were retrieved, pins the matching per-resource policy page(s) plus the organisation-wide page
into a separate section the prompt marks as mandatory, and drops those pages from the ranked context
so they are not shown twice.
"""

from dataclasses import dataclass
from pathlib import Path, PurePath

from ragiac.generation.prompts import build_rag_policy_prompt
from ragiac.generation.rag_generator import LLM, Generation
from ragiac.retrieval.retriever import Retriever, format_context
from ragiac.vectorstore.base import ScoredChunk

GENERAL_POLICY = "org_best_practices.md"

# provider-doc page stem -> per-resource policy page (under knowledge_base/policy_by_resource/)
POLICY_FOR_PROVIDER_PAGE = {
    "storage_bucket": "gcs_bucket_policy.md",
    "storage_bucket_iam": "gcs_bucket_policy.md",
    "storage_bucket_object": "gcs_bucket_policy.md",
    "sql_database_instance": "cloud_sql_policy.md",
    "sql_database": "cloud_sql_policy.md",
    "sql_user": "cloud_sql_policy.md",
    "container_cluster": "gke_cluster_policy.md",
    "container_node_pool": "gke_cluster_policy.md",
}


def _stem(doc_id: str) -> str:
    return PurePath(doc_id.replace("\\", "/")).stem


def select_policies(retrieved: list[ScoredChunk]) -> list[str]:
    """Policy page names to pin for these retrieved chunks: the organisation-wide page always, then
    the per-resource page for each covered provider page that was retrieved, in retrieval order."""
    selected = [GENERAL_POLICY]
    for r in retrieved:
        page = POLICY_FOR_PROVIDER_PAGE.get(_stem(r.chunk.doc_id))
        if page and page not in selected:
            selected.append(page)
    return selected


@dataclass
class PolicyPinnedRagGenerator:
    retriever: Retriever
    llm: LLM
    knowledge_base_dir: Path

    def _policy_text(self, name: str) -> str:
        path = self.knowledge_base_dir / name
        if not path.exists():
            path = self.knowledge_base_dir / "policy_by_resource" / name
        return f"[Policy: {name}]\n{path.read_text(encoding='utf-8').strip()}"

    def generate_detailed(self, requirement: str) -> Generation:
        retrieved = self.retriever.retrieve(requirement)
        names = select_policies(retrieved)
        context = [r for r in retrieved if PurePath(r.chunk.doc_id.replace("\\", "/")).name not in names]
        policy = "\n\n---\n\n".join(self._policy_text(n) for n in names)
        system_prompt, user_prompt = build_rag_policy_prompt(requirement, format_context(context), policy)
        return Generation(
            hcl=self.llm.generate(system_prompt, user_prompt), retrieved=retrieved, pinned_policies=tuple(names)
        )

    def generate(self, requirement: str) -> str:
        return self.generate_detailed(requirement).hcl
