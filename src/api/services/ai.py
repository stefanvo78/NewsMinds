"""
AI Service - OpenAI/ChatGPT integration for article analysis.
"""

from openai import AsyncOpenAI

from src.api.core.config import settings


class AIService:
    """Service for AI-powered article analysis using OpenAI."""

    def __init__(self) -> None:
        if settings.OPENAI_API_KEY:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            self._client = None

    @property
    def is_available(self) -> bool:
        """Check if AI service is configured."""
        return self._client is not None

    async def summarize_article(self, title: str, content: str) -> str:
        """
        Generate a summary of an article using ChatGPT.

        Args:
            title: Article title
            content: Article content

        Returns:
            A 2-3 sentence summary

        Raises:
            RuntimeError: If AI service is not configured
        """
        if not self.is_available:
            raise RuntimeError("AI service not configured. Set OPENAI_API_KEY.")

        response = await self._client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": f"""Summarize this news article in 2-3 sentences. 
Be concise and capture the key points.

Title: {title}

Content: {content}"""
                }
            ],
        )

        return response.choices[0].message.content


# Create a singleton instance
ai_service = AIService()
