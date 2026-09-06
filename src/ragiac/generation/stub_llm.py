"""Deterministic stand-in LLM for RAGIAC_MODE=local.

This does NOT generate real Terraform — it exists purely so the full
ingestion -> retrieval -> generation -> validation pipeline can be exercised
and unit-tested end-to-end without Vertex AI credentials. Swap RAGIAC_MODE=gcp
(see pipeline.build_llm) for actual generation quality.
"""


class StubLLM:
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "# STUB OUTPUT (RAGIAC_MODE=local) -- not real generation.\n"
            "# Switch RAGIAC_MODE=gcp to generate with Vertex AI Gemini.\n"
            f"# system_prompt chars: {len(system_prompt)}\n"
            f"# user_prompt chars: {len(user_prompt)}\n"
        )
