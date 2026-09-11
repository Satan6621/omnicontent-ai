class LLMServiceError(Exception):
    pass


class BaseLLMService:
    """Abstract LLM interface — swappable providers (OpenAI, Anthropic, templates)."""

    provider_name: str = "abstract"

    async def generate_post(self, topic: str, platform: str, tone: str) -> tuple[str, str]:
        """Returns (content, hashtags)."""
        raise NotImplementedError

    async def generate_script(self, prompt: str, max_words: int = 120) -> str:
        raise NotImplementedError

    async def generate_visual_prompts(self, script: str, n: int = 5) -> list[str]:
        raise NotImplementedError
