"""001_initial_schema_baseline

Revision ID: 001_initial_schema_baseline
Revises: None
Create Date: 2026-10-20 00:00:00

Schema mirrors docs/04-data/DATA_DICTIONARY.md and backend/src/models.py.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(128), nullable=False, unique=True),
        sa.Column("chain", sa.String(32), nullable=False, server_default="solana"),
        sa.Column("label", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="DISCOVERED"),
        sa.Column("composite_score", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("net_pnl_usd", sa.Numeric(16, 4), nullable=False, server_default="0.0000"),
        sa.Column("win_rate_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("profit_factor", sa.Numeric(6, 2), nullable=False, server_default="0.00"),
        sa.Column("max_drawdown_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_wallets_address", "wallets", ["address"])

    op.create_table(
        "tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(128), nullable=False, unique=True),
        sa.Column("chain", sa.String(32), nullable=False, server_default="solana"),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=True),
        sa.Column("decimals", sa.Integer, nullable=False, server_default="9"),
        sa.Column("min_lot_size", sa.Numeric(18, 8), nullable=False, server_default="0.001"),
        sa.Column("tick_size", sa.Numeric(18, 8), nullable=False, server_default="0.01"),
        sa.Column("is_blacklisted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("freeze_authority_revoked", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("mint_authority_revoked", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("pool_liquidity_usd", sa.Numeric(18, 2), nullable=True, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tokens_address", "tokens", ["address"])

    op.create_table(
        "wallet_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wallets.id"), nullable=False),
        sa.Column("tx_signature", sa.String(128), nullable=False, unique=True),
        sa.Column("chain", sa.String(32), nullable=False, server_default="solana"),
        sa.Column("dex_protocol", sa.String(32), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("token_in_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=True),
        sa.Column("token_out_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=True),
        sa.Column("amount_in", sa.Numeric(24, 8), nullable=False, server_default="0"),
        sa.Column("amount_out", sa.Numeric(24, 8), nullable=False, server_default="0"),
        sa.Column("price_usd", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("network_fee_native", sa.Numeric(16, 8), nullable=False, server_default="0.000005"),
        sa.Column("finality_status", sa.String(16), nullable=False, server_default="confirmed"),
        sa.Column("block_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_wallet_observations_wallet_id", "wallet_observations", ["wallet_id"])
    op.create_index("ix_wallet_observations_tx_signature", "wallet_observations", ["tx_signature"])
    op.create_index(
        "ix_wallet_observations_raw_payload_gin", "wallet_observations", ["raw_payload"], postgresql_using="gin"
    )

    op.create_table(
        "market_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=False),
        sa.Column("price_usd", sa.Numeric(18, 6), nullable=False),
        sa.Column("price_native", sa.Numeric(24, 8), nullable=True),
        sa.Column("volume_24h_usd", sa.Numeric(18, 2), nullable=True, server_default="0.00"),
        sa.Column("pool_liquidity_usd", sa.Numeric(18, 2), nullable=True, server_default="0.00"),
        sa.Column("bid_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("ask_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("spread_pct", sa.Numeric(6, 4), nullable=True, server_default="0.0000"),
        sa.Column("source", sa.String(32), nullable=False, server_default="Binance_WS"),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_stale", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_market_snapshots_token_id", "market_snapshots", ["token_id"])
    op.create_index("ix_market_snapshots_snapshot_time", "market_snapshots", ["snapshot_time"])

    op.create_table(
        "strategies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "strategy_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("strategy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("version_tag", sa.String(16), nullable=False, server_default="v1.0.0"),
        sa.Column("parameters_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_strategy_versions_strategy_id", "strategy_versions", ["strategy_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "strategy_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_versions.id"),
            nullable=True,
        ),
        sa.Column("agent_name", sa.String(32), nullable=False),
        sa.Column("task_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="STARTED"),
        sa.Column("execution_time_ms", sa.Numeric(8, 2), nullable=True, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "llm_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False, server_default="OPENROUTER"),
        sa.Column("model_name", sa.String(64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(8, 6), nullable=True, server_default="0.000000"),
        sa.Column("latency_ms", sa.Numeric(8, 2), nullable=False),
        sa.Column("status_code", sa.Integer, nullable=False, server_default="200"),
        sa.Column("request_prompt_summary", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("response_json", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_llm_requests_agent_run_id", "llm_requests", ["agent_run_id"])

    op.create_table(
        "trading_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("token_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("target_entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("suggested_stop_loss", sa.Numeric(18, 6), nullable=False),
        sa.Column("suggested_take_profit_1", sa.Numeric(18, 6), nullable=False),
        sa.Column("suggested_take_profit_2", sa.Numeric(18, 6), nullable=False),
        sa.Column("recommended_allocation_pct", sa.Numeric(5, 4), nullable=False, server_default="0.0050"),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("estimated_winrate_pct", sa.Numeric(5, 2), nullable=True, server_default="50.00"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trading_signals_agent_run_id", "trading_signals", ["agent_run_id"])
    op.create_index("ix_trading_signals_token_id", "trading_signals", ["token_id"])

    op.create_table(
        "risk_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trading_signal_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("trading_signals.id"),
            nullable=False,
        ),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("expectancy_check", sa.Boolean, nullable=False),
        sa.Column("risk_per_trade_check", sa.Boolean, nullable=False),
        sa.Column("daily_loss_check", sa.Boolean, nullable=False),
        sa.Column("drawdown_check", sa.Boolean, nullable=False),
        sa.Column("spread_check", sa.Boolean, nullable=False),
        sa.Column("stop_loss_check", sa.Boolean, nullable=False),
        sa.Column("balance_lot_check", sa.Boolean, nullable=False),
        sa.Column("circuit_breaker_check", sa.Boolean, nullable=False),
        sa.Column("data_freshness_check", sa.Boolean, nullable=False),
        sa.Column("rejection_reasons", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_risk_checks_trading_signal_id", "risk_checks", ["trading_signal_id"])

    op.create_table(
        "paper_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "risk_check_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risk_checks.id"), nullable=False, unique=True
        ),
        sa.Column("client_order_id", sa.String(64), nullable=False, unique=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("order_type", sa.String(16), nullable=False, server_default="MARKET"),
        sa.Column("requested_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("requested_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("calculated_dollar_risk", sa.Numeric(12, 4), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="SUBMITTED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tokens.id"), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="OPEN"),
        sa.Column("current_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("current_stop_loss", sa.Numeric(18, 6), nullable=False),
        sa.Column("take_profit_1", sa.Numeric(18, 6), nullable=False),
        sa.Column("take_profit_2", sa.Numeric(18, 6), nullable=False),
        sa.Column("is_tp1_hit", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("trailing_stop_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("realized_pnl_usd", sa.Numeric(16, 4), nullable=False, server_default="0.0000"),
        sa.Column("unrealized_pnl_usd", sa.Numeric(16, 4), nullable=True, server_default="0.0000"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_positions_token_id", "positions", ["token_id"])

    op.create_table(
        "paper_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "paper_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_orders.id"), nullable=False
        ),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("positions.id"), nullable=False),
        sa.Column("executed_quantity", sa.Numeric(24, 8), nullable=False),
        sa.Column("executed_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("slippage_pct", sa.Numeric(6, 4), nullable=False, server_default="0.0000"),
        sa.Column("transaction_fee_usd", sa.Numeric(12, 4), nullable=False, server_default="0.0000"),
        sa.Column("gas_fee_native", sa.Numeric(16, 8), nullable=True, server_default="0.000005"),
        sa.Column("execution_venue", sa.String(32), nullable=False, server_default="Binance_SPOT_SIM"),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_paper_trades_paper_order_id", "paper_trades", ["paper_order_id"])
    op.create_index("ix_paper_trades_position_id", "paper_trades", ["position_id"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("total_equity_usd", sa.Numeric(18, 4), nullable=False),
        sa.Column("cash_balance_usd", sa.Numeric(18, 4), nullable=False),
        sa.Column("open_positions_value_usd", sa.Numeric(18, 4), nullable=False),
        sa.Column("daily_realized_pnl_usd", sa.Numeric(16, 4), nullable=False, server_default="0.0000"),
        sa.Column("daily_loss_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("high_water_mark_usd", sa.Numeric(18, 4), nullable=False),
        sa.Column("current_drawdown_pct", sa.Numeric(5, 2), nullable=False, server_default="0.00"),
        sa.Column("win_rate_pct", sa.Numeric(5, 2), nullable=True, server_default="0.00"),
        sa.Column("profit_factor", sa.Numeric(6, 2), nullable=True, server_default="0.00"),
        sa.Column("net_expectancy_usd", sa.Numeric(12, 4), nullable=True, server_default="0.0000"),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "user_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_mutable", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "system_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="INFO"),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("system_events")
    op.drop_table("user_settings")
    op.drop_table("portfolio_snapshots")
    op.drop_table("paper_trades")
    op.drop_table("positions")
    op.drop_table("paper_orders")
    op.drop_table("risk_checks")
    op.drop_table("trading_signals")
    op.drop_table("llm_requests")
    op.drop_table("agent_runs")
    op.drop_table("strategy_versions")
    op.drop_table("strategies")
    op.drop_table("market_snapshots")
    op.drop_table("wallet_observations")
    op.drop_table("tokens")
    op.drop_table("wallets")
