import json
from urllib.parse import quote

import httpx

from app.core.config import get_settings
from app.services.llm_base import BaseLLMService

settings = get_settings()

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
TIMEOUT = 60

SYSTEM_POST = (
    "Eres un experto community manager. Creas posts originales para redes sociales en español. "
    "Respondes ÚNICAMENTE con JSON válido, sin markdown ni explicaciones, con este formato exacto: "
    '{"content": "texto del post", "hashtags": "#tag1 #tag2 #tag3"}'
)

SYSTEM_SCRIPT = (
    "Eres guionista de videos cortos virales (TikTok/Reels) en español. "
    "Escribes guiones hablados, con ritmo, frases cortas y un gancho al inicio. "
    "Respondes ÚNICAMENTE con el texto del guion, sin título, sin comillas, sin notas de dirección."
)

SYSTEM_VISUALS = (
    "Eres director de arte. Recibes un guion y propondrás prompts de imagen para sus fondos. "
    "Respondes ÚNICAMENTE con JSON válido: "
    '{"prompts": ["prompt 1", "prompt 2", ...]}'
    "Cada prompt describe una escena visual concreta, en inglés, apta para un generador de imágenes."
)


class GeminiLLMService(BaseLLMService):
    provider_name = "gemini"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or settings.gemini_model
        self.api_key = api_key or settings.gemini_api_key

    def _url(self) -> str:
        return f"{GEMINI_BASE}/{self.model}:generateContent"

    def _headers(self) -> dict:
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def _call(self, system: str, user: str, max_tokens: int = 1024) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json" if "JSON" in system else "text/plain",
            },
        }
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(self._url(), headers=self._headers(), json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError("Gemini no devolvió candidatos")
            parts = (candidates[0].get("content") or {}).get("parts") or []
            return "".join(p.get("text", "") for p in parts).strip()

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw[start:end + 1])
            raise

    async def generate_post(self, topic: str, platform: str, tone: str) -> tuple[str, str]:
        user = (
            f"Crea un post sobre: {topic}. "
            f"Plataforma: {platform}. Tono: {tone}. "
            f"Máximo 280 caracteres de contenido y 3 hashtags relevantes."
        )
        raw = self._call(SYSTEM_POST, user)
        data = self._parse_json(raw)
        content = str(data.get("content", "")).strip()
        hashtags = str(data.get("hashtags", "")).strip()
        if not content:
            raise RuntimeError("Gemini devolvió contenido vacío")
        return content, hashtags

    async def generate_script(self, prompt: str, max_words: int = 120) -> str:
        user = (
            f"Escribe el guion hablado para un video corto sobre: {prompt}. "
            f"Extensión máxima: {max_words} palabras. Termina con un cierre que invite a seguir la cuenta."
        )
        raw = self._call(SYSTEM_SCRIPT, user, max_tokens=800)
        if not raw:
            raise RuntimeError("Gemini devolvió guion vacío")
        words = raw.split()
        if len(words) > max_words:
            raw = " ".join(words[:max_words])
        return raw

    async def generate_visual_prompts(self, script: str, n: int = 5) -> list[str]:
        user = (
            f"Guion:\n{script[:1500]}\n\n"
            f"Devuelve exactamente {n} prompts de imagen."
        )
        raw = self._call(SYSTEM_VISUALS, user, max_tokens=800)
        data = self._parse_json(raw)
        prompts = [str(p).strip() for p in data.get("prompts", []) if str(p).strip()]
        if not prompts:
            raise RuntimeError("Gemini no devolvió prompts")
        return prompts[:n]
