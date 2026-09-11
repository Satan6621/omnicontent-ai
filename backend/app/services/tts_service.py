import asyncio
from pathlib import Path

import edge_tts

from app.core.config import get_settings

settings = get_settings()

DEFAULT_VOICE = settings.tts_voice


class TTSError(Exception):
    pass


async def _synthesize(text: str, voice: str, out_path: str) -> None:
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(out_path)


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
    """Genera voz en off (MP3) desde el guion usando edge-tts (neural, gratuito)."""
    chosen = voice or DEFAULT_VOICE
    script = script.strip()
    if not script:
        raise TTSError("Script vacío: no hay nada que sintetizar")
    try:
        _run_async(_synthesize(script, chosen, out_path))
    except Exception as e:
        raise TTSError(f"edge-tts falló: {e}") from e

    p = Path(out_path)
    if not p.exists() or p.stat().st_size < 1000:
        raise TTSError("edge-tts no produjo audio válido")
    return out_path
