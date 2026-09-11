import random
from pathlib import Path
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw

from app.core.config import get_settings

settings = get_settings()

TIMEOUT_SECONDS = 90
MIN_VALID_BYTES = 5000


def _pollinations_url(prompt: str, width: int, height: int, seed: int) -> str:
    styled = f"{prompt}, vertical composition, no text, no watermark"
    return (
        f"{settings.pollinations_base}/{quote(styled)}"
        f"?width={width}&height={height}&nologo=true&seed={seed}"
    )


def _gradient_placeholder(out_path: str, seed: int, width: int = 1080, height: int = 1920) -> str:
    """Fallback offline: gradiente vertical determinista por seed (Pillow)."""
    rnd = random.Random(seed)
    top = (
        rnd.randint(20, 90),
        rnd.randint(10, 60),
        rnd.randint(80, 200),
    )
    bottom = (
        rnd.randint(120, 240),
        rnd.randint(30, 90),
        rnd.randint(40, 120),
    )
    img = Image.new("RGB", (width, height))
    d = ImageDraw.Draw(img)
    for y in range(height):
        t = y / height
        color = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        d.line([(0, y), (width, y)], fill=color)

    for _ in range(6):
        x0 = rnd.randint(-200, width)
        y0 = rnd.randint(0, height)
        r = rnd.randint(150, 480)
        alpha_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        od = ImageDraw.Draw(alpha_overlay)
        od.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=(255, 255, 255, 18))
        img = Image.alpha_composite(img.convert("RGBA"), alpha_overlay).convert("RGB")

    img.save(out_path, quality=88)
    return out_path


def fetch_background_image(prompt: str, out_path: str, seed: int | None = None,
                           width: int = 1080, height: int = 1920) -> str:
    """Descarga una imagen de fondo (Pollinations). Fallback: gradiente local si falla."""
    seed = seed if seed is not None else random.randint(1, 10**6)
    url = _pollinations_url(prompt, width, height, seed)
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200 and len(resp.content) >= MIN_VALID_BYTES:
                Path(out_path).write_bytes(resp.content)
                return out_path
    except httpx.HTTPError:
        pass
    return _gradient_placeholder(out_path, seed, width, height)
