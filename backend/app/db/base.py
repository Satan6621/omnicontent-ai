from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def _metadata() -> MetaData:
    # El schema "omnicontent" solo aplica a Postgres; SQLite lo ignora.
    if get_settings().sqlite:
        return MetaData(naming_convention=naming_convention)
    return MetaData(schema="omnicontent", naming_convention=naming_convention)


class Base(DeclarativeBase):
    metadata = _metadata()
