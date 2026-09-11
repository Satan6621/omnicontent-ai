import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_api_key, require_api_key
from app.db.session import get_db
from app.models import ApiKey
from app.schemas import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse

router = APIRouter(prefix="/apikeys", tags=["apikeys"], dependencies=[Depends(require_api_key)])

settings = get_settings()


def _to_response(row: ApiKey) -> ApiKeyResponse:
    resp = ApiKeyResponse(
        id=row.id,
        name=row.name,
        scopes=list(row.scopes or []),
        active=row.active,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        key_preview="",  # los hash no se muestran
    )
    return resp


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(db: Session = Depends(get_db)):
    rows = db.execute(select(ApiKey).order_by(ApiKey.created_at.desc())).scalars().all()
    return [_to_response(r) for r in rows]


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(req: ApiKeyCreate, db: Session = Depends(get_db)):
    """Crea un key multi-cliente. El key completo solo se devuelve una vez."""
    raw = secrets.token_urlsafe(32)
    row = ApiKey(
        name=req.name.strip(),
        key_hash=hash_api_key(raw),
        scopes=list(req.scopes or ["*"]),
        active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiKeyCreateResponse(id=row.id, name=row.name, scopes=list(row.scopes or []), key=raw)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(key_id: int, db: Session = Depends(get_db)):
    row = db.get(ApiKey, key_id)
    if not row:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(row)
    db.commit()


@router.post("/{key_id}/deactivate", response_model=ApiKeyResponse)
async def deactivate_api_key(key_id: int, db: Session = Depends(get_db)):
    row = db.get(ApiKey, key_id)
    if not row:
        raise HTTPException(status_code=404, detail="API key not found")
    row.active = False
    db.commit()
    db.refresh(row)
    return _to_response(row)