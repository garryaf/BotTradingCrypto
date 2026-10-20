"""003_risk_checks_max_positions

Revision ID: 003_risk_checks_max_positions
Revises: 002_ingestion_dlq_and_ohlcv
Create Date: 2026-10-20 00:00:00

DATA_DICTIONARY.md's risk_checks only has circuit_breaker_check, but
ROADMAP.md/OPEN_QUESTIONS.md's numbered "9 pintu" list has pintu 8 as
"Batas Posisi Terbuka Maksimal" (max open positions), a distinct concept
from circuit breaker/freeze. Adding the missing column rather than
overloading circuit_breaker_check's meaning.
"""
from alembic import op
import sqlalchemy as sa

revision = "003_risk_checks_max_positions"
down_revision = "002_ingestion_dlq_and_ohlcv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "risk_checks",
        sa.Column("max_positions_check", sa.Boolean, nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("risk_checks", "max_positions_check")
