"""Shared Gemini client utilities."""

from __future__ import annotations

from typing import Optional

from app.config import settings

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


class GeminiClient:
    """Thin wrapper around Gemini text generation."""

    def __init__(self, model_name: str = settings.GEMINI_MODEL) -> None:
        self.model_name = model_name

    def generate_text(self, prompt: str, temperature: float = 0.2) -> str:
        """Generate text from Gemini for a given prompt."""

        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini API is not configured. Add GEMINI_API_KEY to .env.")
        if genai is None:
            raise RuntimeError("Gemini SDK is not installed. Run: pip install google-generativeai")

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=temperature),
        )

        if response and response.text:
            return response.text.strip()
        raise RuntimeError("Gemini returned an empty response.")


def get_gemini_client(model_name: Optional[str] = None) -> GeminiClient:
    """Return a Gemini client instance for a model name."""

    return GeminiClient(model_name=model_name or settings.GEMINI_MODEL)
