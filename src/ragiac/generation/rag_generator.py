from dataclasses import dataclass

from ragiac.generation.prompts import build_rag_prompt
from ragiac.retrieval.retriever import Retriever


class LLM:
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass
class RagGenerator:
    retriever: Retriever
    llm: LLM

    def generate(self, requirement: str) -> str:
        context = self.retriever.assemble_context(requirement)
        system_prompt, user_prompt = build_rag_prompt(requirement, context)
        return self.llm.generate(system_prompt, user_prompt)
