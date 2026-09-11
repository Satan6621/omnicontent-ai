import math
import random
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100

# Escala menor pentatónica (A minor pent: A C D E G) en varias octavas — suena bien con casi cualquier guion
CHORDS = [
    [220.00, 261.63, 329.63],   # A min
    [196.00, 246.94, 293.66],   # G maj-ish
    [174.61, 220.00, 261.63],   # F maj-ish
    [130.81, 164.81, 196.00],   # C maj-ish (bajo)
]

STYLES = {
    "ambient": {"tempo": 0, "attack": 1.5, "release": 3.0, "pad_gain": 0.16, "arp_gain": 0.0, "bass_gain": 0.05},
    "lofi": {"tempo": 72, "attack": 0.02, "release": 0.35, "pad_gain": 0.10, "arp_gain": 0.07, "bass_gain": 0.10},
    "upbeat": {"tempo": 108, "attack": 0.01, "release": 0.22, "pad_gain": 0.09, "arp_gain": 0.10, "bass_gain": 0.12},
}


class MusicGenError(Exception):
    pass


def _adsr(n: int, attack: float, release: float) -> np.ndarray:
    env = np.ones(n)
    a = max(1, int(attack * SAMPLE_RATE))
    r = max(1, int(release * SAMPLE_RATE))
    a = min(a, n)
    r = min(r, n)
    env[:a] = np.linspace(0, 1, a)
    env[n - r:] = np.linspace(1, 0, r)
    return env


def _tone(freq: float, seconds: float, gain: float, attack: float, release: float) -> np.ndarray:
    t = np.linspace(0, seconds, int(seconds * SAMPLE_RATE), endpoint=False)
    # Suavizar el timbre: seno + un poco de 2do/3er armónico
    wave_ = (
        np.sin(2 * np.pi * freq * t)
        + 0.35 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.15 * np.sin(2 * np.pi * freq * 3 * t)
    )
    return wave_ * gain * _adsr(len(t), attack, release)


def _write_wav(samples: np.ndarray, out_path: str) -> str:
    # Normalizar a int16 estéreo (duplicar canal)
    peak = np.max(np.abs(samples)) or 1.0
    normalized = samples / peak * 0.9
    pcm = (normalized * 32767).astype(np.int16)
    stereo = np.column_stack([pcm, pcm]).reshape(-1)

    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(stereo.tobytes())
    return out_path


def generate_background_music(duration_seconds: float, style: str = "lofi", seed: int | None = None,
                              out_path: str = "media/audio/music_bed.wav") -> str:
    """Genera una pista musical de fondo procedural (WAV 44.1kHz estéreo).

    Estilos: ambient (sin ritmo), lofi (72bpm), upbeat (108bpm).
    Requiere numpy. Sin dependencias externas ni archivos de audio.
    """
    style = STYLES.get(style, STYLES["lofi"])
    rng = random.Random(seed if seed is not None else 42)

    duration = max(2.0, float(duration_seconds))
    total_n = int(duration * SAMPLE_RATE)
    mix = np.zeros(total_n)

    # ── Pad de acordes: progresión Am-G-F-C cada 4s ──
    bar_seconds = 4.0
    n_bars = math.ceil(duration / bar_seconds)
    for bar in range(n_bars):
        chord = CHORDS[bar % len(CHORDS)]
        start = int(bar * bar_seconds * SAMPLE_RATE)
        for freq in chord:
            note = _tone(freq, bar_seconds + 0.5, style["pad_gain"] / len(chord),
                         style["attack"], style["release"])
            end = min(start + len(note), total_n)
            mix[start:end] += note[: end - start]

    # ── Arpegio rítmico (si el estilo tiene tempo) ──
    if style["tempo"] > 0:
        beat = 60.0 / style["tempo"]
        steps = int(duration / (beat / 2))
        scale = [220.00, 261.63, 293.66, 329.63, 392.00, 440.00, 523.25]
        for i in range(steps):
            if rng.random() < 0.65:  # deja silencios (groove)
                freq = scale[rng.randrange(len(scale))]
                start = int(i * beat / 2 * SAMPLE_RATE)
                note = _tone(freq, beat * 0.9, style["arp_gain"], style["attack"], style["release"] * 0.6)
                end = min(start + len(note), total_n)
                mix[start:end] += note[: end - start]

        # ── Bajo (fundamental del acorde, una nota por compás) ──
        for bar in range(n_bars):
            chord = CHORDS[bar % len(CHORDS)]
            start = int(bar * bar_seconds * SAMPLE_RATE)
            note = _tone(chord[0] / 2, bar_seconds * 0.95, style["bass_gain"], 0.05, 0.8)
            end = min(start + len(note), total_n)
            mix[start:end] += note[: end - start]

    # ── Filtro suave para quitar aspereza (media móvil corta) ──
    kernel = np.ones(6) / 6
    mix = np.convolve(mix, kernel, mode="same")

    # ── Fade global de entrada/salida ──
    fade = int(min(1.5, duration / 6) * SAMPLE_RATE)
    if fade > 0 and total_n > 2 * fade:
        mix[:fade] *= np.linspace(0, 1, fade)
        mix[-fade:] *= np.linspace(1, 0, fade)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    return _write_wav(mix, out_path)
