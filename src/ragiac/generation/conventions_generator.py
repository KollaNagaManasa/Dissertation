"""Control arm: the organisational conventions are placed in the prompt, with no retrieval.

Comparing this arm with RAG separates two things the RAG-vs-baseline comparison conflates: the
benefit of *retrieving* documentation, and the benefit of merely *knowing* the organisation's
conventions (which, for the baseline, exist nowhere in its input). It uses the RAG prompt with the
same instructions; only the source of the context differs.
"""

from dataclasses import dataclass
from pathlib import Path

from ragiac.generation.prompts import build_rag_prompt
from ragiac.generation.rag_generator import LLM


def load_conventions(knowledge_base_dir: Path) -> str:
    """Top-level knowledge-base documents only (the hand-written org conventions); the fetched
    provider documentation lives in a subdirectory and is deliberately excluded."""
    blocks = [
        f"[Source: {path.name}]\n{path.read_text(encoding='utf-8').strip()}"
        for path in sorted(knowledge_base_dir.glob("*.md"))
    ]
    return "\n\n---\n\n".join(blocks)


@dataclass
class ConventionsGenerator:
    llm: LLM
    conventions_text: str

    def generate(self, requirement: str) -> str:
        system_prompt, user_prompt = build_rag_prompt(requirement, self.conventions_text)
        return self.llm.generate(system_prompt, user_prompt)
