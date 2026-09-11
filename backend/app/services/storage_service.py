"""Servicio de persistencia de media en Supabase Storage (E2).

Si SUPABASE_URL + SUPABASE_KEY están configurados, sube archivos al bucket público
y retorna la URL pública. Si falla, devuelve None (fallback a media local efímero).
"""
import hashlib
import os
import time
from pathlib import Path

import httpx

from app.core.config import get_settings


def _sb_upload_headers(content_type: str) -> dict:
    s = get_settings()
    return {
        "apikey": s.supabase_key,
        "Authorization": f"Bearer {s.supabase_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }


def upload_file_to_storage(local_path: str, content_type: str = "video/mp4") -> str | None:
    """Sube un archivo al bucket de Supabase Storage y retorna la URL pública.

    Retorna None si no está configurado o falla.
    """
    s = get_settings()
    if not s.supabase_url or not s.supabase_key:
        return None

    p = Path(local_path)
    if not p.exists():
        return None

    ext = p.suffix.lstrip(".") or "bin"
    # Nombre único: timestamp + hash corto para dedup
    file_hash = hashlib.md5(p.read_bytes()[:65536]).hexdigest()[:10]
    object_name = f"videos/{p.stem}_{int(time.time())}_{file_hash}.{ext}"
    public_url = (
        f"{s.supabase_url.rstrip('/')}"
        f"/storage/v1/object/public/{s.supabase_bucket}/{object_name}"
    )
    upload_url = (
        f"{s.supabase_url.rstrip('/')}"
        f"/storage/v1/object/{s.supabase_bucket}/{object_name}"
    )

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                upload_url,
                headers=_sb_upload_headers(content_type),
                content=p.read_bytes(),
            )
            if resp.status_code in (200, 201):
                return public_url
    except Exception:
        pass
    return None


def upload_bytes_to_storage(data: bytes, filename: str, content_type: str) -> str | None:
    """Sube bytes al bucket de Supabase Storage y retorna la URL pública."""
    s = get_settings()
    if not s.supabase_url or not s.supabase_key:
        return None

    ext = filename.split(".")[-1] if "." in filename else "bin"
    file_hash = hashlib.md5(data[:65536]).hexdigest()[:10]
    object_name = f"media/{filename.rsplit('.', 1)[0]}_{int(time.time())}_{file_hash}.{ext}"
    public_url = (
        f"{s.supabase_url.rstrip('/')}"
        f"/storage/v1/object/public/{s.supabase_bucket}/{object_name}"
    )
    upload_url = (
        f"{s.supabase_url.rstrip('/')}"
        f"/storage/v1/object/{s.supabase_bucket}/{object_name}"
    )

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(
                upload_url,
                headers=_sb_upload_headers(content_type),
                content=data,
            )
            if resp.status_code in (200, 201):
                return public_url
    except Exception:
        pass
    return None
