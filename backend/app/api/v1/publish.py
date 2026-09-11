import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.security import require_api_key
from app.schemas import PublishRequest, PublishResponse

router = APIRouter(prefix="/publish", tags=["publish"])

settings = get_settings()


def _autosocial_headers() -> dict:
    return {
        "X-API-Key": settings.autosocial_api_key,
        "Content-Type": "application/json",
    }


def _autosocial_publish_url() -> str:
    base = settings.autosocial_url.rstrip("/")
    return f"{base}/publish"


@router.post("", response_model=PublishResponse, dependencies=[Depends(require_api_key)])
async def publish_to_socials(req: PublishRequest):
    """Publica contenido (texto/imagen/video) en las redes vía la API de AutoSocial."""
    if not settings.autosocial_api_key or settings.autosocial_api_key.startswith("change-me"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTOSOCIAL_API_KEY no configurada en el backend",
        )

    # Si el video no tiene URL pública absoluta, convertirla desde la ruta local
    video_url = req.video_url
    if video_url and not video_url.startswith("http"):
        video_url = f"{settings.public_media_base_url.rstrip('/')}/{video_url.replace(chr(92), '/').lstrip('/')}"

    content = req.content.strip()
    if req.hashtags:
        content = f"{content}\n\n{req.hashtags.strip()}"

    payload: dict = {"content": content, "platforms": req.platforms}
    if video_url:
        payload["video_url"] = video_url
    if req.image_data_uri:
        payload["image"] = req.image_data_uri

    try:
        timeout = httpx.Timeout(300.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                _autosocial_publish_url(),
                headers=_autosocial_headers(),
                json=payload,
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No se pudo contactar AutoSocial: {e}",
        )

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="AutoSocial rechazó la API key (AUTOSOCIAL_API_KEY)")
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AutoSocial respondió HTTP {resp.status_code}: {resp.text[:200]}",
        )

    data = resp.json()
    results: dict = data.get("results", {})

    errors: list[str] = []
    succeeded = 0
    for plat, outcome in results.items():
        if isinstance(outcome, dict) and outcome.get("success"):
            succeeded += 1
        else:
            msg = outcome.get("error", "error desconocido") if isinstance(outcome, dict) else str(outcome)
            errors.append(f"{plat}: {msg}")

    return PublishResponse(
        results=results,
        requested=len(req.platforms),
        succeeded=succeeded,
        errors=errors,
    )
