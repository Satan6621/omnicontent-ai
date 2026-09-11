"""Servicio de generación de scripts (F5 draft mode)."""
import asyncio

from app.services import get_llm_service
from app.services.template_llm import TemplateLLMService


def _run_async(coro) -> object:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    if loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as ex:
            return ex.submit(lambda: asyncio.run(coro)).result(timeout=120)
    return asyncio.run(coro)


async def generate_script(prompt: str, max_words: int = 120) -> str:
    """Genera un script para el prompt usando el LLM principal con fallback."""
    llm = get_llm_service()
    try:
        return await llm.generate_script(prompt, max_words=max_words)
    except Exception:
        fallback = TemplateLLMService()
        return await fallback.generate_script(prompt, max_words=max_words)