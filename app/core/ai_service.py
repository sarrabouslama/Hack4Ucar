"""Service for interacting with Google Gemini AI."""

import google.generativeai as genai
from app.config import settings

class AIService:
    """Manager for Gemini AI operations."""

    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def generate_text(self, prompt: str) -> str:
        """Generate text from a prompt."""
        if not settings.GEMINI_API_KEY:
            return "AI Service not configured (missing API Key)."
        
        response = await self.model.generate_content_async(prompt)
        return response.text

    async def generate_json(self, prompt: str) -> str:
        """Generate structured JSON from a prompt."""
        if not settings.GEMINI_API_KEY:
            return "{}"
            
        try:
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            return response.text
        except Exception as e:
            print(f"Error generating JSON: {e}")
            return "{}"

    async def get_embeddings(self, text: str) -> list[float]:
        """Generate embeddings for a given text."""
        if not settings.GEMINI_API_KEY:
            # Fallback for demo if no key
            import random
            return [random.uniform(-1, 1) for _ in range(768)]
        
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']

ai_service = AIService()
