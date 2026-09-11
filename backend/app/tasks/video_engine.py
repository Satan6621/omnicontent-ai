import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import JobStatus, VideoJob
from app.services import get_llm_service
from app.services.template_llm import TemplateLLMService
from app.services.tts_service import TTSError, synthesize_speech
from app.services.image_service import fetch_background_image
from app.services.subtitle_service import write_ass_file
from app.services.music_service import MusicGenError, generate_background_music
from app.services.ffmpeg_service import FFmpegError, probe_duration_seconds, render_vertical_video

settings = get_settings()
llm = get_llm_service()

MEDIA_ROOT = Path(settings.media_root)


class JobUpdate:
    """Actualiza estado/progreso de un VideoJob dentro de una sesión dada."""

    def __init__(self, job: VideoJob, db: Session):
        self.job = job
        self.db = db

    def step(self, progress: int, detail: str, status: JobStatus | None = None) -> None:
        self.job.progress = max(0, min(100, progress))
        self.job.status_detail = detail
        if status is not None:
            self.job.status = status
        self.db.commit()


def _split_script_segments(script: str, max_segments: int = 6) -> list[dict]:
    """Divide el guion en segmentos por párrafos/oraciones largas para subtítulos."""
    paragraphs = [p.strip() for p in script.split("\n") if p.strip()]
    chunks: list[str] = []
    for p in paragraphs:
        p = re.sub(r"\s+", " ", p)
        sentences = re.split(r"(?<=[.!?…])\s+", p)
        buf = ""
        for s in sentences:
            if len(buf) + len(s) < 180:
                buf = f"{buf} {s}".strip()
            else:
                if buf:
                    chunks.append(buf)
                buf = s
        if buf:
            chunks.append(buf)

    if not chunks:
        chunks = [script.strip() or "Contenido generado por OmniContent AI"]

    if len(chunks) > max_segments:
        merged: list[str] = []
        per = len(chunks) // max_segments
        for i in range(0, len(chunks), per):
            merged.append(" ".join(chunks[i:i + per]))
        chunks = merged[:max_segments]

    return [{"text": c} for c in chunks]


def _distribute_timing(segments: list[dict], total_duration: float) -> list[dict]:
    """Reparte la duración del audio entre segmentos proporcionalmente a su longitud."""
    total_chars = sum(len(s["text"]) for s in segments) or 1
    t = 0.0
    for seg in segments:
        dur = total_duration * (len(seg["text"]) / total_chars)
        seg["start"] = t
        seg["end"] = t + dur
        t += dur
    return segments


def process_video_job(job_id: int, voice: str | None = None, visual_style: str = "cinematic",
                      music_style: str | None = None) -> dict:
    """Pipeline completo de generación de video (sincrónico, corre en el worker Celery).

    music_style: None/'' = sin música; 'ambient' | 'lofi' | 'upbeat' = música procedural.
    """
    db: Session = SessionLocal()
    try:
        job = db.get(VideoJob, job_id)
        if not job:
            return {"job_id": job_id, "error": "Job not found"}

        upd = JobUpdate(job, db)
        job_dir = MEDIA_ROOT / "videos" / f"job_{job_id}"
        audio_dir = MEDIA_ROOT / "audio"
        image_dir = MEDIA_ROOT / "images"
        for d in (job_dir, audio_dir, image_dir):
            d.mkdir(parents=True, exist_ok=True)

        try:
            # ── 1. Script ─────────────────────────────
            upd.step(5, "Generating script", JobStatus.PROCESSING)
            if job.script and job.script.strip():
                script = job.script.strip()
            else:
                script = _run_llm_script(job.prompt)
                job.script = script
                db.commit()

            # ── 2. Voiceover (TTS) ─────────────────────
            upd.step(20, "Synthesizing voiceover")
            audio_path = str(audio_dir / f"job_{job_id}.mp3")
            synthesize_speech(script, audio_path, voice)
            job.audio_path = audio_path
            db.commit()

            upd.step(40, "Voiceover ready")

            # ── 3. Background images ──────────────────
            upd.step(50, "Generating background images")
            visual_prompts = _run_llm_visual_prompts(script, n=5, style=visual_style)
            image_paths: list[str] = []
            for i, vp in enumerate(visual_prompts):
                img_path = str(image_dir / f"job_{job_id}_bg{i}.jpg")
                fetch_background_image(vp, img_path)
                image_paths.append(img_path)
                upd.step(50 + int((i + 1) / len(visual_prompts) * 15),
                         f"Background {i + 1}/{len(visual_prompts)}")

            # ── 4. Subtitles ───────────────────────────
            upd.step(68, "Building subtitles")
            audio_duration = probe_duration_seconds(audio_path)
            segments = _split_script_segments(script)
            segments = _distribute_timing(segments, audio_duration)
            subs_path = str(job_dir / f"job_{job_id}.ass")
            write_ass_file(segments, audio_duration, subs_path)

            # ── 5. Música de fondo (procedural, opcional) ─
            music_path = None
            if music_style:
                upd.step(75, f"Composing {music_style} music")
                try:
                    music_path = generate_background_music(
                        audio_duration + 1.0,
                        style=music_style,
                        out_path=str(audio_dir / f"job_{job_id}_music.wav"),
                    )
                except (MusicGenError, Exception):
                    music_path = None  # la música es best-effort: el video sigue sin ella

            # ── 6. Render ──────────────────────────────
            upd.step(80, "Rendering video (FFmpeg)")
            output_path = str(job_dir / f"job_{job_id}.mp4")
            render_vertical_video(image_paths, audio_path, subs_path, output_path,
                                   music_path=music_path)

            # ── 7. Complete ────────────────────────────
            job.video_path = output_path
            job.duration_seconds = int(audio_duration)
            upd.step(100, "Completed", JobStatus.COMPLETED)
            return {"job_id": job_id, "status": "COMPLETED", "video_path": output_path}

        except (TTSError, FFmpegError, Exception) as e:
            job.error = str(e)[:1800]
            upd.step(0, "Failed", JobStatus.FAILED)
            return {"job_id": job_id, "status": "FAILED", "error": str(e)[:300]}
    finally:
        db.close()


def _run_llm_script(prompt: str) -> str:
    from app.services.tts_service import _run_async

    try:
        return _run_async(llm.generate_script(prompt))
    except Exception:
        fallback = TemplateLLMService()
        try:
            return _run_async(fallback.generate_script(prompt))
        except Exception:
            return f"Ideas clave sobre {prompt}. Empieza simple, mide resultados y mejora cada día."


def _run_llm_visual_prompts(script: str, n: int, style: str) -> list[str]:
    from app.services.tts_service import _run_async

    try:
        prompts = _run_async(llm.generate_visual_prompts(script, n))
    except Exception:
        fallback = TemplateLLMService()
        try:
            prompts = _run_async(fallback.generate_visual_prompts(script, n))
        except Exception:
            prompts = [f"abstract {style} background {i}" for i in range(n)]
    return [f"{p}, {style} style" for p in prompts]
