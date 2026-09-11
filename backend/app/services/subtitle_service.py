ASS_HEADER_TEMPLATE = """[Script Info]
Script Type: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,DejaVu Sans,64,&H00FFFFFF,&H000000FF,&H00101010,&H88000000,-1,0,0,0,100,100,0,0,1,4,2,2,90,90,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


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


def build_ass_subtitles(segments: list[dict], total_duration: float) -> str:
    """Genera el archivo ASS completo.

    segments: [{"text": str, "start": float, "end": float}, ...]
    """
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
    return ASS_HEADER_TEMPLATE + "\n".join(events) + "\n"


def write_ass_file(segments: list[dict], total_duration: float, out_path: str) -> str:
    content = build_ass_subtitles(segments, total_duration)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    return out_path
