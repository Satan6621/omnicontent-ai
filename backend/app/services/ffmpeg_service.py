import subprocess
from pathlib import Path


class FFmpegError(Exception):
    pass


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        # Persiste el stderr completo para diagnóstico
        try:
            log_dir = Path("media/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "ffmpeg_latest.log").write_text(proc.stderr or "", encoding="utf-8")
        except Exception:
            pass
        raise FFmpegError(f"FFmpeg falló (rc={proc.returncode}): {proc.stderr[:1500]}")


def probe_duration_seconds(path: str) -> float:
    """Duración del archivo via ffprobe (incluido con FFmpeg)."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise FFmpegError(f"ffprobe falló: {proc.stderr[-300:]}")
    return float(proc.stdout.strip())


def render_vertical_video(
    image_paths: list[str],
    audio_path: str,
    subtitles_path: str,
    output_path: str,
    segment_duration: float = 4.0,
    width: int = 1080,
    height: int = 1920,
    music_path: str | None = None,
    music_volume: float = 0.22,
    low_memory: bool = False,
) -> str:
    """Compila imágenes + audio + subtítulos ASS en un MP4 vertical 1080x1920.

    Estrategia:
    1. Concatena las imágenes como slideshow con zoom sutil (Ken Burns via zoompan).
    2. Mezcla la voz con la música de fondo (music_volume relativo, sidechain no necesario).
    3. Subtítulos quemados via filtro ass.
    """
    if not image_paths:
        raise FFmpegError("No hay imágenes de fondo")

    total_duration = probe_duration_seconds(audio_path)
    n = len(image_paths)
    per_img = max(total_duration / n, 1.0)

    inputs: list[str] = []
    filter_parts: list[str] = []
    for i, img in enumerate(image_paths):
        inputs.extend(["-loop", "1", "-t", f"{per_img:.3f}", "-i", img])

    # Escalar cada imagen a 1080x1920 (cover) y aplicar zoompan suave
    for i in range(n):
        zoom_scale = 1.0 + 0.08 * (i % 2)  # alterna 1.0x / 1.08x por variedad
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='{zoom_scale}+0.0006*on':d=1:{'x=0:y=0' if i % 2 == 0 else 'x=iw-iw/zoom:y=ih-ih/zoom'}:s={width}x{height}:fps=25,"
            f"format=yuv420p[v{i}]"
        )

    # Concatenar
    concat_in = "".join(f"[v{i}]" for i in range(n))
    filter_parts.append(f"{concat_in}concat=n={n}:v=1:a=0[vcat]")

    voice_index = n
    music_index = n + 1
    filter_parts.append(f"[vcat]ass='{subtitles_path.replace(chr(92), '/')}':fontsdir=fonts[vout]")

    # Audio: voz sola, o mezclada con música
    if music_path:
        filter_parts.append(
            f"[{voice_index}:a]aresample=44100[va];"
            f"[{music_index}:a]volume={music_volume},aresample=44100[ma];"
            f"[va][ma]amix=inputs=2:duration=first:dropout_transition=3,alimiter=limit=0.9[aout]"
        )
        audio_map = "[aout]"
    else:
        audio_map = f"{voice_index}:a"

    filter_complex = ";".join(filter_parts)

    preset = "veryfast" if low_memory else "medium"
    crf = "25" if low_memory else "21"
    threads = ("-threads", "1") if low_memory else ("-threads", "0")

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend(["-i", audio_path])
    if music_path:
        cmd.extend(["-stream_loop", "-1", "-i", music_path])
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", audio_map,
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", crf,
        *threads,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ])
    _run(cmd)

    if not Path(output_path).exists() or Path(output_path).stat().st_size < 5000:
        raise FFmpegError("Render no produjo un archivo válido")
    return output_path
