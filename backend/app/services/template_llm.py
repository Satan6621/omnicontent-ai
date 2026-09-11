import random

from app.services.llm_base import BaseLLMService


POST_TEMPLATES = [
    "{topic}: esto es lo que nadie te cuenta.\n\nPunto 1 — empieza pequeño, mide todo.\nPunto 2 — la consistencia vence al talento.\nPunto 3 — comparte tu proceso, no solo el resultado.\n\n¿Cuál de los tres te falta hoy? 👇",
    "3 ideas sobre {topic} que cambiaron mi forma de trabajar:\n\n1️⃣ Menos herramientas, más sistema.\n2️⃣ El 80% del resultado sale del 20% del esfuerzo.\n3️⃣ Documentar > memorizar.\n\nGuarda este post para cuando lo necesites. 🔖",
    "¿{topic}? Aquí va una verdad incómoda:\n\nNo se trata de hacer más. Se trata de hacer lo correcto, más seguido.\n\nLa estrategia aburrida de siempre gana.\n\n¿Estás de acuerdo? 💬",
    "La conversación sobre {topic} está creciendo y no es casualidad.\n\nQuienes lo entienden hoy llevan ventaja mañana.\n\n👉 Empieza por lo básico, domina el proceso, escala después.\n\nComparte si te sirvió. 🔄",
    "{topic} en 30 segundos:\n\n• El problema: exceso de información, poca acción.\n• La causa: falta de sistema claro.\n• La solución: una decisión pequeña, repetida a diario.\n\nSencillo no significa fácil. Pero sí posible. 💪",
]

HASHTAG_POOL = {
    "generic": ["#productividad", "#crece", "#aprende", "#estrategia", "#exito"],
    "twitter": ["#hilo", "#aprende", "#crecimiento"],
    "mastodon": ["#consejo", "#comunidad"],
    "instagram": ["#reels", "#instagood", "#tips", "#motivacion", "#emprender"],
    "linkedin": ["#liderazgo", "#negocios", "#carrera"],
    "tiktok": ["#fyp", "#parati", "#tips"],
}

TONE_PREFIX = {
    "professional": "",
    "casual": "Escucha, esto es directo: ",
    "inspirational": "✨ ",
    "provocative": "Opinión impopular: ",
}


class TemplateLLMService(BaseLLMService):
    """Deterministic offline provider — zero-cost fallback, fully mockable."""

    provider_name = "templates"

    async def generate_post(self, topic: str, platform: str, tone: str) -> tuple[str, str]:
        clean = topic.strip().rstrip(".")
        body = random.choice(POST_TEMPLATES).format(topic=clean)
        prefix = TONE_PREFIX.get(tone, "")
        content = f"{prefix}{body}" if prefix else body

        pool = HASHTAG_POOL.get(platform, HASHTAG_POOL["generic"])
        hashtags = " ".join(random.sample(pool, k=min(3, len(pool))))
        return content, hashtags

    async def generate_script(self, prompt: str, max_words: int = 120) -> str:
        clean = prompt.strip().rstrip(".")
        opening = random.choice(
            [
                f"¿Sabes qué es lo más importante sobre {clean}?",
                f"Hoy quiero hablarte de {clean}.",
                f"Esto va a cambiar tu forma de ver {clean}.",
            ]
        )
        script = (
            f"{opening}\n\n"
            "Primero lo esencial: la mayoría falla porque empieza por lo complejo. "
            "Hazlo al revés. Domina lo básico hasta que sea automático.\n\n"
            "Segundo: mide. Lo que no mides, no mejora. Una sola métrica, una semana, "
            "y vas a ver patrones que nadie más ve.\n\n"
            "Y tercero: comparte lo que aprendes. Enseñar obliga a entender mejor. "
            "Además, construyes tu audiencia mientras ayudas.\n\n"
            f"Si esto te sirvió sobre {clean}, sígueme para más. Nos vemos en el próximo."
        )
        words = script.split()
        if len(words) > max_words:
            script = " ".join(words[:max_words])
        return script

    async def generate_visual_prompts(self, script: str, n: int = 5) -> list[str]:
        lines = [l.strip() for l in script.split("\n") if len(l.strip()) > 20][:n]
        while len(lines) < n:
            lines.append(f"abstract modern background, ambient light, cinematic, scene {len(lines) + 1}")
        return [
            f"{l[:200]}, cinematic photography, vertical 9:16, dramatic lighting, high detail"
            for l in lines
        ]
