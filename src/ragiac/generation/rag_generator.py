from dataclasses import dataclass

from ragiac.generation.prompts import build_rag_prompt
from ragiac.retrieval.retriever import Retriever, format_context
from ragiac.vectorstore.base import ScoredChunk


class LLM:
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass(frozen=True)
class Generation:
    hcl: str
    retrieved: list[ScoredChunk]


@dataclass
class RagGenerator:
    retriever: Retriever
    llm: LLM

    def generate_detailed(self, requirement: str) -> Generation:
        retrieved = self.retriever.retrieve(requirement)
        system_prompt, user_prompt = build_rag_prompt(requirement, format_context(retrieved))
        return Generation(hcl=self.llm.generate(system_prompt, user_prompt), retrieved=retrieved)

    def generate(self, requirement: str) -> str:
        return self.generate_detailed(requirement).hcl
