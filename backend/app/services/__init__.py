from app.core.config import get_settings
from app.services.gemini_llm import GeminiLLMService
from app.services.llm_base import BaseLLMService, LLMServiceError
from app.services.template_llm import TemplateLLMService

__all__ = ["BaseLLMService", "LLMServiceError", "TemplateLLMService", "get_llm_service"]


def get_llm_service() -> BaseLLMService:
    """Factory: proveedor configurado → fallback templates.

    Orden: llm_provider explícito → Gemini si hay key → templates.
    """
    settings = get_settings()

    provider = (settings.llm_provider or "").strip().lower()
    if provider == "gemini" and settings.gemini_api_key:
        return GeminiLLMService()
    if provider in ("openai", "anthropic") and not settings.openai_api_key and not settings.anthropic_api_key:
        pass

    if not provider or provider in ("auto", "templates"):
        if settings.gemini_api_key:
            return GeminiLLMService()
        return TemplateLLMService()

    return TemplateLLMService()
