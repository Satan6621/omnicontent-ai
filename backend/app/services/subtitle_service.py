"""Generación de subtítulos ASS con presets de estilo configurables.

Cada preset mapea a: font family, font size, outline (borde), BackColour (fondo del
cuadro subtítulo) y bold. Se usan con el filtro `ass` de FFmpeg.
"""
import re

# ── Presets de estilo (Feature: Render Styling Presets) ──────────────────────────
STYLE_PRESETS: dict[str, dict] = {
    "cinematic": {
        "font": "DejaVu Sans",
        "size": 64,
        "outline": 4,
        "back_colour": "&H88000000",  # fondo semi-transparente
        "bold": -1,                   # -1 = bold activo en ASS
        "shadow": 2,
        "margin_v": 220,
        "primary": "&H00FFFFFF",
    },
    "minimalist": {
        "font": "DejaVu Sans Light",
        "size": 52,
        "outline": 2,
        "back_colour": "&H00000000",  # sin caja (transparente)
        "bold": 0,
        "shadow": 1,
        "margin_v": 260,
        "primary": "&H00FFFFFF",
    },
    "bold_contrast": {
        "font": "Arial Black",
        "size": 78,
        "outline": 6,
        "back_colour": "&H00000000",  # sin caja, solo borde grueso
        "bold": -1,
        "shadow": 4,
        "margin_v": 180,
        "primary": "&H00FFFFFF",
    },
    "retro": {
        "font": "Courier New",
        "size": 60,
        "outline": 3,
        "back_colour": "&H88001B0C",  # caja semi-transparente retro (marino)
        "bold": -1,
        "shadow": 2,
        "margin_v": 200,
        "primary": "&H00FFFF00",      # texto amarillo retro
    },
}


def resolve_style_preset(style_preset: str | None) -> dict:
    """Resuelve el preset pedido; si es inválido usa cinematic."""
    key = (style_preset or "cinematic").lower().replace("-", "_")
    return STYLE_PRESETS.get(key, STYLE_PRESETS["cinematic"])


def _header_for_style(style_preset: str | None) -> str:
    p = resolve_style_preset(style_preset)
    style = (
        "Style: Narration,{font},{size},{primary},&H000000FF,{outline_colour},{back},"
        "{bold},0,0,0,100,100,0,0,1,{outline},{shadow},2,90,90,{margin_v},1"
    ).format(
        font=p["font"],
        size=p["size"],
        primary=p["primary"],
        outline_colour="&H00101010",
        back=p["back_colour"],
        bold=p["bold"],
        outline=p["outline"],
        shadow=p["shadow"],
        margin_v=p["margin_v"],
    )
    return f"""[Script Info]
Script Type: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


ASS_HEADER_TEMPLATE = _header_for_style("cinematic")


def _ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _wrap_es(text: str, max_chars: int = 34) -> list[str]:
    """Envuelve texto en palabras completas (apto para español)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = f"{current} {w}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = w
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def build_ass_subtitles(segments: list[dict], total_duration: float,
                        style_preset: str | None = None) -> str:
    """Genera el archivo ASS completo con el preset de estilo elegido.

    segments: [{"text": str, "start": float, "end": float}, ...]
    """
    header = _header_for_style(style_preset)
    events = []
    for seg in segments:
        start = float(seg["start"])
        end = min(float(seg["end"]), total_duration if total_duration > 0 else float(seg["end"]))
        if end <= start:
            end = start + 0.5
        lines = _wrap_es(seg["text"])
        for i, line in enumerate(lines):
            sub_start = start + (end - start) * (i / len(lines))
            sub_end = start + (end - start) * ((i + 1) / len(lines))
            text = line.replace("\n", "\\N")
            events.append(
                f"Dialogue: 0,{_ts(sub_start)},{_ts(sub_end)},Narration,,0,0,0,,{text}"
            )
    return header + "\n".join(events) + "\n"


def write_ass_file(segments: list[dict], total_duration: float, out_path: str,
                   style_preset: str | None = None) -> str:
    content = build_ass_subtitles(segments, total_duration, style_preset)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path