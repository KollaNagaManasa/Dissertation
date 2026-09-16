"""Vertex AI Gemini wrapper used by both the RAG generator and the non-RAG baseline."""

import re

from ragiac.config import Settings

_CODE_FENCE_RE = re.compile(r"^```(?:hcl|terraform)?\s*\n(.*?)\n```\s*$", re.S)


def _strip_code_fence(text: str) -> str:
    """Gemini wraps output in a ```hcl ... ``` fence despite being told not to add prose
    outside HCL comments -- a fence isn't prose, so the model doesn't treat the instruction as
    covering it. terraform_validator.py writes the raw text straight to main.tf, so an
    un-stripped fence breaks `terraform init` with a parse error."""
    match = _CODE_FENCE_RE.match(text.strip())
    return match.group(1) if match else text


class VertexLLM:
    def __init__(self, settings: Settings):
        import vertexai

        # Generation uses vertex_generation_location (default "global"), independent of the
        # asia-south1 region used for storage/embeddings/vector search — see config.py.
        vertexai.init(project=settings.google_cloud_project, location=settings.vertex_generation_location)
        self._settings = settings

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from vertexai.generative_models import GenerativeModel

        model = GenerativeModel(self._settings.vertex_generation_model, system_instruction=[system_prompt])
        response = model.generate_content(user_prompt)
        return _strip_code_fence(response.text)
