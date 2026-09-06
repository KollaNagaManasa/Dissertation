"""Vertex AI Gemini wrapper used by both the RAG generator and the non-RAG baseline."""

from ragiac.config import Settings


class VertexLLM:
    def __init__(self, settings: Settings):
        import vertexai

        vertexai.init(project=settings.google_cloud_project, location=settings.google_cloud_region)
        self._settings = settings

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from vertexai.generative_models import GenerativeModel

        model = GenerativeModel(self._settings.vertex_generation_model, system_instruction=[system_prompt])
        response = model.generate_content(user_prompt)
        return response.text
