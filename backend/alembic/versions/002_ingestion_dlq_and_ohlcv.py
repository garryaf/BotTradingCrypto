"""002_ingestion_dlq_and_ohlcv

Revision ID: 002_ingestion_dlq_and_ohlcv
Revises: 001_initial_schema_baseline
Create Date: 2026-10-20 00:00:00

Adds ingestion_errors (DLQ, docs/03-diagrams/DATA_FLOW.mmd) and
market_ohlcv (ROADMAP.md TASK-2.6) for Fase 2 — Market Data Engine.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_ingestion_dlq_and_ohlcv"
down_revision = "001_initial_schema_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("reference", sa.String(128), nullable=True),
        sa.Column("detail", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ingestion_errors_occurred_at", "ingestion_errors", ["occurred_at"])

    op.create_table(
        "market_ohlcv",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=False),
        sa.Column("interval", sa.String(8), nullable=False),
        sa.Column("bucket_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_market_ohlcv_token_id", "market_ohlcv", ["token_id"])
    op.create_unique_constraint(
        "uq_market_ohlcv_token_interval_bucket", "market_ohlcv", ["token_id", "interval", "bucket_time"]
    )


def downgrade() -> None:
    op.drop_table("market_ohlcv")
    op.drop_table("ingestion_errors")
