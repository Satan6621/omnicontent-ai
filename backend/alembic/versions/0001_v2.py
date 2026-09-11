"""v2: columnas nuevas de video_jobs + publish_jobs + api_keys

Revision ID: 0001
Revises:
Create Date: 2026-09-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _schema() -> str:
    # La app usa schema "omnicontent" en Postgres, ninguno en SQLite
    from app.core.config import get_settings

    return "" if get_settings().sqlite else "omnicontent"


def upgrade() -> None:
    s = _schema()
    if not s:
        # SQLite local: create_all del startup cubre schema; la migración es para Postgres.
        return
    schema = f'"{s}".'

    # Affix: agregar columnas nuevas a video_jobs (idempotente)
    cols = [
        ('"text"', 'storage_url', 'storage_url',
         'ALTER TABLE {s}video_jobs ADD COLUMN IF NOT EXISTS storage_url TEXT'),
        ('"boolean"', 'auto_publish', 'auto_publish DEFAULT false',
         'ALTER TABLE {s}video_jobs ADD COLUMN IF NOT EXISTS auto_publish BOOLEAN NOT NULL DEFAULT false'),
        ('JSONB', 'publish_platforms', 'publish_platforms',
         'ALTER TABLE {s}video_jobs ADD COLUMN IF NOT EXISTS publish_platforms JSONB NOT NULL DEFAULT \'[]\''),
        ('"text"', 'publish_content', 'publish_content',
         'ALTER TABLE {s}video_jobs ADD COLUMN IF NOT EXISTS publish_content TEXT NOT NULL DEFAULT \'\''),
        ('"text"', 'publish_hashtags', 'publish_hashtags',
         'ALTER TABLE {s}video_jobs ADD COLUMN IF NOT EXISTS publish_hashtags TEXT NOT NULL DEFAULT \'\''),
    ]
    for _, _, _, sql in cols:
        op.execute(sql.format(s=schema))

    # publish_jobs
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}publish_jobs (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            platforms JSONB NOT NULL DEFAULT '[]',
            hashtags TEXT NOT NULL DEFAULT '',
            video_url TEXT,
            image_data_uri TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            per_network JSONB,
            error TEXT,
            scheduled_at TIMESTAMPTZ,
            published_at TIMESTAMPTZ,
            dedupe_key VARCHAR(128),
            source VARCHAR(40) NOT NULL DEFAULT 'api',
            retry_of INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_publish_jobs_status ON {schema}publish_jobs (status)")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_publish_jobs_scheduled_at ON {schema}publish_jobs (scheduled_at)")
    op.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS uq_publish_jobs_dedupe_key ON {schema}publish_jobs (dedupe_key)")

    # api_keys
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}api_keys (
            id SERIAL PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            key_hash VARCHAR(128) NOT NULL,
            scopes JSONB NOT NULL DEFAULT '["*"]',
            active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_used_at TIMESTAMPTZ
        )
    """)
    op.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_api_keys_key_hash ON {schema}api_keys (key_hash)")


def downgrade() -> None:
    s = _schema()
    schema = f'"{s}".' if s else ""
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS storage_url')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS auto_publish')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS publish_platforms')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS publish_content')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS publish_hashtags')
    op.execute(f"DROP TABLE IF EXISTS {schema}publish_jobs")
    op.execute(f"DROP TABLE IF EXISTS {schema}api_keys")