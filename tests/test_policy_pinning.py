from pathlib import Path

from ragiac.evaluation.runner import ARMS
from ragiac.generation.policy_pinning import GENERAL_POLICY, PolicyPinnedRagGenerator, select_policies
from ragiac.ingestion.chunker import Chunk
from ragiac.vectorstore.base import ScoredChunk

KB = Path("data/knowledge_base")


def _scored(doc_id: str, text: str = "x") -> ScoredChunk:
    return ScoredChunk(chunk=Chunk(chunk_id=f"{doc_id}#0", doc_id=doc_id, source=doc_id, text=text), score=0.5)


class _Retriever:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query):
        return self.results


class _RecordingLLM:
    def __init__(self):
        self.prompts = None

    def generate(self, system_prompt, user_prompt):
        self.prompts = (system_prompt, user_prompt)
        return 'resource "google_storage_bucket" "b" {}'


def test_rag_policy_is_a_recognised_arm():
    assert "rag_policy" in ARMS


def test_select_policies_always_pins_the_general_policy():
    assert select_policies([]) == [GENERAL_POLICY]
    assert select_policies([_scored("provider_docs/pubsub_topic.md")]) == [GENERAL_POLICY]


def test_select_policies_maps_retrieved_provider_pages_to_resource_policies_once_each():
    retrieved = [
        _scored("provider_docs\\container_node_pool.md"),  # Windows-style doc_id, as stored in the real index
        _scored("provider_docs/storage_bucket.md"),
        _scored("provider_docs/container_cluster.md"),
    ]
    assert select_policies(retrieved) == [GENERAL_POLICY, "gke_cluster_policy.md", "gcs_bucket_policy.md"]


def test_generator_puts_policy_in_its_own_section_and_drops_pinned_pages_from_context():
    llm = _RecordingLLM()
    retrieved = [
        _scored("provider_docs/storage_bucket.md", "BUCKET PROVIDER DOC"),
        _scored("policy_by_resource\\gcs_bucket_policy.md", "RANKED POLICY CHUNK"),
    ]
    gen = PolicyPinnedRagGenerator(retriever=_Retriever(retrieved), llm=llm, knowledge_base_dir=KB)

    result = gen.generate_detailed("a versioned bucket")

    system, user = llm.prompts
    assert "mandatory" in system
    policy_section, _, rest = user.partition("Retrieved context:")
    assert "[Policy: org_best_practices.md]" in policy_section
    assert "[Policy: gcs_bucket_policy.md]" in policy_section
    assert "BUCKET PROVIDER DOC" in rest
    assert "RANKED POLICY CHUNK" not in user  # already pinned in full, not repeated as a ranked chunk
    assert result.pinned_policies == (GENERAL_POLICY, "gcs_bucket_policy.md")
    assert result.retrieved == retrieved  # retrieval is recorded as ranked, for the hit-rate metric
