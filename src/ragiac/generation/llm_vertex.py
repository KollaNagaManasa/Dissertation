"""Vertex AI Gemini wrapper used by both the RAG generator and the non-RAG baseline."""

import re

from ragiac.config import Settings

_CODE_FENCE_RE = re.compile(r"^```(?:hcl|terraform)?\s*\n(.*?)\n```\s*$", re.S)
_FENCED_BLOCK_RE = re.compile(r"```(?:hcl|terraform|tf)?[ \t]*\n(.*?)\n[ \t]*```", re.S)


def _strip_code_fence(text: str) -> str:
    """Gemini wraps output in a ```hcl ... ``` fence despite being told not to add prose
    outside HCL comments -- a fence isn't prose, so the model doesn't treat the instruction as
    covering it. terraform_validator.py writes the raw text straight to main.tf, so an
    un-stripped fence breaks `terraform init` with a parse error."""
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


def _extract_hcl(text: str) -> str:
    """Pull the Terraform out of a model reply that may wrap it in a fence and/or add prose
    around it. Uses the largest fenced block if there is one; otherwise the text as is (minus a
    dangling opening fence, which appears when output is cut off before the closing one)."""
    blocks = _FENCED_BLOCK_RE.findall(text)
    if blocks:
        return max(blocks, key=len)
    stripped = text.lstrip()
    if stripped.startswith("```"):
        return stripped.split("\n", 1)[1] if "\n" in stripped else ""
    return text


def _part_text(part) -> str:
    try:
        return part.text or ""
    except (ValueError, AttributeError):  # non-text parts (function calls etc.) raise on .text
        return ""


def _response_text(response) -> str:
    """`response.text` raises ValueError when Gemini returns several content parts (which the
    newer models do, e.g. when they emit reasoning parts). Join the visible text parts instead."""
    try:
        return response.text
    except ValueError:
        parts = response.candidates[0].content.parts if response.candidates else []
        return "\n".join(_part_text(p) for p in parts if not getattr(p, "thought", False) and _part_text(p))


class VertexLLM:
    def __init__(self, settings: Settings):
        import vertexai

        # Generation uses vertex_generation_location (default "global"), independent of the
        # asia-south1 region used for storage/embeddings/vector search — see config.py.
        vertexai.init(project=settings.google_cloud_project, location=settings.vertex_generation_location)
        self._settings = settings

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from vertexai.generative_models import GenerationConfig, GenerativeModel

        from ragiac.retry import call_with_backoff, vertex_retryable_errors

        model = GenerativeModel(self._settings.vertex_generation_model, system_instruction=[system_prompt])
        config = GenerationConfig(temperature=self._settings.generation_temperature)
        response = call_with_backoff(
            lambda: model.generate_content(user_prompt, generation_config=config),
            retryable=vertex_retryable_errors(),
            max_retries=self._settings.api_max_retries,
        )
        return _extract_hcl(_response_text(response))
