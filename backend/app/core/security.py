import hashlib
from datetime import datetime, timezone

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Valida X-API-Key contra: (1) tabla api_keys (multi-cliente, E5),
    (2) fallback al API_KEY del entorno. Sin key configurada → todo pasa."""
    settings = get_settings()
    if not settings.api_key_is_configured:
        return
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key",
        )

    # 1) Copia maestra del entorno siempre válida
    if x_api_key == settings.api_key:
        return

    # 2) Multi-cliente: verificar en DB (hash)
    try:
        from app.db.session import SessionLocal
        from app.models import ApiKey
    except Exception:
        return  # sin modelo, solo key master

    db = SessionLocal()
    try:
        row = db.query(ApiKey).filter(
            ApiKey.key_hash == hash_api_key(x_api_key),
            ApiKey.active.is_(True),
        ).first()
        if row:
            row.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return
    except Exception:
        pass
    finally:
        db.close()

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-API-Key",
    )