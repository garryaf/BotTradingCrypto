"""004_users_and_account_scoping

Revision ID: 004_users_and_account_scoping
Revises: 003_risk_checks_max_positions
Create Date: 2026-10-21 00:00:00

Introduces per-user accounts (1 Binance API key per user) and scopes the
paper-trading execution tables (positions, portfolio_snapshots, risk_checks)
to a user_id. trading_signals/agent_runs/llm_requests stay shared — Hermes's
market analysis isn't account-specific, only the risk gate's per-account
sizing/execution against it is.

Pre-existing paper-trading rows have no owner to backfill, and live trading
is hard-locked off (main.py), so this truncates them rather than attempting
a backfill.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "004_users_and_account_scoping"
down_revision = "003_risk_checks_max_positions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "binance_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("api_key_encrypted", sa.String, nullable=False),
        sa.Column("api_secret_encrypted", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_binance_credentials_user_id", "binance_credentials", ["user_id"])

    op.execute("TRUNCATE positions, portfolio_snapshots, risk_checks, paper_orders, paper_trades CASCADE")

    for table in ("positions", "portfolio_snapshots", "risk_checks"):
        op.add_column(
            table, sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False)
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    for table in ("positions", "portfolio_snapshots", "risk_checks"):
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_column(table, "user_id")
    op.drop_index("ix_binance_credentials_user_id", table_name="binance_credentials")
    op.drop_table("binance_credentials")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
