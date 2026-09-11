"""v3: content scheduler (scheduled_for/published_at), style_preset y webhook_subscriptions

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _schema() -> str:
    from app.core.config import get_settings

    return "" if get_settings().sqlite else "omnicontent"


def upgrade() -> None:
    s = _schema()
    if not s:
        # SQLite local: create_all del startup cubre el schema; la migración es para Postgres.
        return
    schema = f'"{s}".'

    # video_jobs: scheduler + style preset
    op.execute(f'ALTER TABLE {schema}video_jobs ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ')
    op.execute(f'ALTER TABLE {schema}video_jobs ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ')
    op.execute(f"ALTER TABLE {schema}video_jobs ADD COLUMN IF NOT EXISTS style_preset VARCHAR(40) NOT NULL DEFAULT 'cinematic'")
    op.execute(f"ALTER TABLE {schema}video_jobs ADD COLUMN IF NOT EXISTS voice VARCHAR(60)")
    op.execute(f"ALTER TABLE {schema}video_jobs ADD COLUMN IF NOT EXISTS visual_style VARCHAR(60) NOT NULL DEFAULT 'cinematic'")
    op.execute(f"ALTER TABLE {schema}video_jobs ADD COLUMN IF NOT EXISTS music_style VARCHAR(20)")
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_video_jobs_scheduled_for ON {schema}video_jobs (scheduled_for)")

    # social_posts: scheduler
    op.execute(f'ALTER TABLE {schema}social_posts ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ')
    op.execute(f'ALTER TABLE {schema}social_posts ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ')
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_social_posts_scheduled_for ON {schema}social_posts (scheduled_for)")

    # webhook_subscriptions
    op.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}webhook_subscriptions (
            id SERIAL PRIMARY KEY,
            url VARCHAR(2000) NOT NULL,
            event_type VARCHAR(60) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT true,
            secret VARCHAR(500),
            headers JSONB,
            description TEXT NOT NULL DEFAULT '',
            last_status VARCHAR(20),
            last_sent_at TIMESTAMPTZ,
            last_error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(f"CREATE INDEX IF NOT EXISTS ix_webhook_subscriptions_event_type ON {schema}webhook_subscriptions (event_type)")


def downgrade() -> None:
    s = _schema()
    schema = f'"{s}".' if s else ""
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS scheduled_for')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS published_at')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS style_preset')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS voice')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS visual_style')
    op.execute(f'ALTER TABLE {schema}video_jobs DROP COLUMN IF EXISTS music_style')
    op.execute(f'ALTER TABLE {schema}social_posts DROP COLUMN IF EXISTS scheduled_for')
    op.execute(f'ALTER TABLE {schema}social_posts DROP COLUMN IF EXISTS published_at')
    op.execute(f"DROP TABLE IF EXISTS {schema}webhook_subscriptions")