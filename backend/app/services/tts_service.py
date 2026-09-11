import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)

DEFAULT_VOICE = settings.tts_voice

# Voz edge-tts → voz gTTS ("com.google.tts:es-es-std" o por idioma)
GTTS_LANG_MAP = {
    "es": "es",
    "es-mx": "es-es",
    "es-es": "es-es",
    "es-ar": "es-es",
    "en": "en",
    "en-us": "en",
    "pt": "pt",
}


class TTSError(Exception):
    pass


async def _synthesize_edge(text: str, voice: str, out_path: str) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(out_path)


def _synthesize_gtts(text: str, voice: str, out_path: str) -> None:
    """Fallback por red: gTTS (Google Translate TTS) funciona desde datacenters."""
    from gtts import gTTS

    code = voice.split("-", 1)[0].lower() if voice else "es"
    lang = GTTS_LANG_MAP.get(code, code)
    tts = gTTS(text=text, lang=lang)
    tts.save(out_path)


def _run_async(coro):
    """Ejecuta una corutina desde contexto sync, incluso dentro de un loop vivo (Celery eager)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import threading

        result: dict = {}

        def runner():
            try:
                result["value"] = asyncio.run(coro)
            except Exception as e:
                result["error"] = e

        t = threading.Thread(target=runner)
        t.start()
        t.join()
        if "error" in result:
            raise result["error"]
        return result.get("value")
    return asyncio.run(coro)


def synthesize_speech(script: str, out_path: str, voice: str | None = None) -> str:
    """Genera voz en off (MP3) desde el guion. Intenta edge-tts (neural),
    y si falla (red/datacenter) hace fallback a gTTS."""
    chosen = voice or DEFAULT_VOICE
    script = script.strip()
    if not script:
        raise TTSError("Script vacío: no hay nada que sintetizar")

    attempted: list[str] = []

    if settings.tts_provider in ("edge-tts", "auto"):
        try:
            _run_async(_synthesize_edge(script, chosen, out_path))
            p = Path(out_path)
            if p.exists() and p.stat().st_size >= 1000:
                return out_path
            attempted.append("edge-tts (sin audio válido)")
        except Exception as e:
            attempted.append(f"edge-tts ({type(e).__name__}: {e})")
            logger.warning("edge-tts falló, usando gTTS: %s", e)

    if settings.tts_provider in ("gtts", "auto"):
        try:
            _synthesize_gtts(script, chosen, out_path)
            p = Path(out_path)
            if p.exists() and p.stat().st_size >= 1000:
                return out_path
            attempted.append("gTTS (sin audio válido)")
        except Exception as e:
            attempted.append(f"gTTS ({type(e).__name__}: {e})")

    raise TTSError("TTS sin proveedor disponible: " + "; ".join(attempted or ["ninguno"]))
