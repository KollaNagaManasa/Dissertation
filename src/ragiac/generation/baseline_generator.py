"""Non-RAG baseline: same LLM, no retrieval — used as the comparison point in benchmarking."""

from dataclasses import dataclass

from ragiac.generation.prompts import build_baseline_prompt
from ragiac.generation.rag_generator import LLM


@dataclass
class BaselineGenerator:
    llm: LLM

    def generate(self, requirement: str) -> str:
        system_prompt, user_prompt = build_baseline_prompt(requirement)
        return self.llm.generate(system_prompt, user_prompt)
