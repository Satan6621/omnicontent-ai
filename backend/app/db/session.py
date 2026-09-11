from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {}
# Supabase transaction pooler (port 6543) no admite prepared statements con nombre
engine_kwargs: dict = {"pool_pre_ping": True, "connect_args": connect_args}

if settings.sqlite:
    connect_args["check_same_thread"] = False
elif ":6543" in settings.database_url:
    engine_kwargs["connect_args"] = {
        **connect_args,
        "prepare_threshold": None,
    }

engine = create_engine(settings.database_url, **engine_kwargs)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
