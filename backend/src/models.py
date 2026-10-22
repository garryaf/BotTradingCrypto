"""SQLModel table definitions, one-to-one with docs/04-data/DATA_DICTIONARY.md."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Domain 0: Auth & Accounts ----------------------------------------------

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role: str = Field(max_length=16, default="user")  # "user" | "admin"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class BinanceCredential(SQLModel, table=True):
    __tablename__ = "binance_credentials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True)
    api_key_encrypted: str
    api_secret_encrypted: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# --- Domain 1: Observasi Pasar & Blockchain ---------------------------------

class Wallet(SQLModel, table=True):
    __tablename__ = "wallets"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    address: str = Field(max_length=128, unique=True, index=True)
    chain: str = Field(max_length=32, default="solana")
    label: str | None = Field(default=None, max_length=64)
    status: str = Field(max_length=32, default="DISCOVERED")
    composite_score: Decimal = Field(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    net_pnl_usd: Decimal = Field(default=Decimal("0.0000"), max_digits=16, decimal_places=4)
    win_rate_pct: Decimal = Field(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    profit_factor: Decimal = Field(default=Decimal("0.00"), max_digits=6, decimal_places=2)
    max_drawdown_pct: Decimal = Field(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    last_active_at: datetime | None = Field(default=None)
    approved_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Token(SQLModel, table=True):
    __tablename__ = "tokens"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    address: str = Field(max_length=128, unique=True, index=True)
    chain: str = Field(max_length=32, default="solana")
    symbol: str = Field(max_length=32)
    name: str | None = Field(default=None, max_length=128)
    decimals: int = Field(default=9)
    min_lot_size: Decimal = Field(default=Decimal("0.001"), max_digits=18, decimal_places=8)
    tick_size: Decimal = Field(default=Decimal("0.01"), max_digits=18, decimal_places=8)
    is_blacklisted: bool = Field(default=False)
    freeze_authority_revoked: bool = Field(default=True)
    mint_authority_revoked: bool = Field(default=True)
    pool_liquidity_usd: Decimal | None = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class WalletObservation(SQLModel, table=True):
    __tablename__ = "wallet_observations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    wallet_id: UUID = Field(foreign_key="wallets.id", index=True)
    tx_signature: str = Field(max_length=128, unique=True, index=True)
    chain: str = Field(max_length=32, default="solana")
    dex_protocol: str | None = Field(default=None, max_length=32)
    action: str = Field(max_length=32)
    token_in_id: UUID | None = Field(default=None, foreign_key="tokens.id")
    token_out_id: UUID | None = Field(default=None, foreign_key="tokens.id")
    amount_in: Decimal = Field(default=Decimal(0), max_digits=24, decimal_places=8)
    amount_out: Decimal = Field(default=Decimal(0), max_digits=24, decimal_places=8)
    price_usd: Decimal = Field(default=Decimal(0), max_digits=18, decimal_places=6)
    network_fee_native: Decimal = Field(default=Decimal("0.000005"), max_digits=16, decimal_places=8)
    finality_status: str = Field(max_length=16, default="confirmed")
    block_time: datetime
    raw_payload: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    ingested_at: datetime = Field(default_factory=_utcnow)


class MarketSnapshot(SQLModel, table=True):
    __tablename__ = "market_snapshots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_id: UUID = Field(foreign_key="tokens.id", index=True)
    price_usd: Decimal = Field(max_digits=18, decimal_places=6)
    price_native: Decimal | None = Field(default=None, max_digits=24, decimal_places=8)
    volume_24h_usd: Decimal | None = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    pool_liquidity_usd: Decimal | None = Field(default=Decimal("0.00"), max_digits=18, decimal_places=2)
    bid_price: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    ask_price: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    spread_pct: Decimal | None = Field(default=Decimal("0.0000"), max_digits=6, decimal_places=4)
    source: str = Field(max_length=32, default="Binance_WS")
    snapshot_time: datetime
    is_stale: bool = Field(default=False)


# --- Domain 2: Orkestrasi AI & Strategi -------------------------------------

class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=64, unique=True)
    description: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_utcnow)


class StrategyVersion(SQLModel, table=True):
    __tablename__ = "strategy_versions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_id: UUID = Field(foreign_key="strategies.id", index=True)
    version_tag: str = Field(max_length=16, default="v1.0.0")
    parameters_config: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    is_default: bool = Field(default=True)
    deployed_at: datetime = Field(default_factory=_utcnow)


class AgentRun(SQLModel, table=True):
    __tablename__ = "agent_runs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    strategy_version_id: UUID | None = Field(default=None, foreign_key="strategy_versions.id")
    agent_name: str = Field(max_length=32)
    task_type: str = Field(max_length=32)
    status: str = Field(max_length=16, default="STARTED")
    execution_time_ms: Decimal | None = Field(default=Decimal("0.00"), max_digits=8, decimal_places=2)
    created_at: datetime = Field(default_factory=_utcnow)


class LLMRequest(SQLModel, table=True):
    __tablename__ = "llm_requests"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    provider: str = Field(max_length=32, default="OPENROUTER")
    model_name: str = Field(max_length=64)
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    cost_usd: Decimal | None = Field(default=Decimal("0.000000"), max_digits=8, decimal_places=6)
    latency_ms: Decimal = Field(max_digits=8, decimal_places=2)
    status_code: int = Field(default=200)
    request_prompt_summary: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    response_json: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    requested_at: datetime = Field(default_factory=_utcnow)


class TradingSignal(SQLModel, table=True):
    __tablename__ = "trading_signals"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    agent_run_id: UUID = Field(foreign_key="agent_runs.id", index=True)
    token_id: UUID = Field(foreign_key="tokens.id", index=True)
    symbol: str = Field(max_length=32)
    action: str = Field(max_length=16)
    target_entry_price: Decimal = Field(max_digits=18, decimal_places=6)
    suggested_stop_loss: Decimal = Field(max_digits=18, decimal_places=6)
    suggested_take_profit_1: Decimal = Field(max_digits=18, decimal_places=6)
    suggested_take_profit_2: Decimal = Field(max_digits=18, decimal_places=6)
    recommended_allocation_pct: Decimal = Field(default=Decimal("0.0050"), max_digits=5, decimal_places=4)
    confidence_score: Decimal = Field(max_digits=4, decimal_places=3)
    estimated_winrate_pct: Decimal | None = Field(default=Decimal("50.00"), max_digits=5, decimal_places=2)
    rationale: str | None = Field(default=None)
    status: str = Field(max_length=16, default="PENDING")
    generated_at: datetime = Field(default_factory=_utcnow)
    expires_at: datetime


# --- Domain 3: Risiko & Keselamatan (Deterministic Risk Gate) ---------------

class RiskCheck(SQLModel, table=True):
    __tablename__ = "risk_checks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    trading_signal_id: UUID = Field(foreign_key="trading_signals.id", index=True)
    passed: bool
    expectancy_check: bool
    risk_per_trade_check: bool
    daily_loss_check: bool
    drawdown_check: bool
    spread_check: bool
    stop_loss_check: bool
    balance_lot_check: bool
    max_positions_check: bool  # ROADMAP.md pintu 8 ("Batas Posisi Terbuka Maksimal")
    circuit_breaker_check: bool  # DATA_DICTIONARY.md pintu 8 (Circuit Breaker/Freeze) — kept as a distinct gate
    data_freshness_check: bool
    rejection_reasons: list = Field(default_factory=list, sa_column=Column(JSONB))
    evaluated_at: datetime = Field(default_factory=_utcnow)


# --- Domain 4: Simulasi Eksekusi & Portofolio -------------------------------

class PaperOrder(SQLModel, table=True):
    __tablename__ = "paper_orders"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    risk_check_id: UUID = Field(foreign_key="risk_checks.id", unique=True)
    client_order_id: str = Field(max_length=64, unique=True)
    symbol: str = Field(max_length=32)
    side: str = Field(max_length=8)
    order_type: str = Field(max_length=16, default="MARKET")
    requested_quantity: Decimal = Field(max_digits=24, decimal_places=8)
    requested_price: Decimal = Field(max_digits=18, decimal_places=6)
    calculated_dollar_risk: Decimal = Field(max_digits=12, decimal_places=4)
    status: str = Field(max_length=16, default="SUBMITTED")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class Position(SQLModel, table=True):
    __tablename__ = "positions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    token_id: UUID = Field(foreign_key="tokens.id", index=True)
    symbol: str = Field(max_length=32)
    status: str = Field(max_length=16, default="OPEN")
    current_quantity: Decimal = Field(max_digits=24, decimal_places=8)
    average_entry_price: Decimal = Field(max_digits=18, decimal_places=6)
    current_stop_loss: Decimal = Field(max_digits=18, decimal_places=6)
    take_profit_1: Decimal = Field(max_digits=18, decimal_places=6)
    take_profit_2: Decimal = Field(max_digits=18, decimal_places=6)
    is_tp1_hit: bool = Field(default=False)
    trailing_stop_price: Decimal | None = Field(default=None, max_digits=18, decimal_places=6)
    realized_pnl_usd: Decimal = Field(default=Decimal("0.0000"), max_digits=16, decimal_places=4)
    unrealized_pnl_usd: Decimal | None = Field(default=Decimal("0.0000"), max_digits=16, decimal_places=4)
    opened_at: datetime = Field(default_factory=_utcnow)
    closed_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=_utcnow)


class PaperTrade(SQLModel, table=True):
    __tablename__ = "paper_trades"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    paper_order_id: UUID = Field(foreign_key="paper_orders.id", index=True)
    position_id: UUID = Field(foreign_key="positions.id", index=True)
    executed_quantity: Decimal = Field(max_digits=24, decimal_places=8)
    executed_price: Decimal = Field(max_digits=18, decimal_places=6)
    slippage_pct: Decimal = Field(default=Decimal("0.0000"), max_digits=6, decimal_places=4)
    transaction_fee_usd: Decimal = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    gas_fee_native: Decimal | None = Field(default=Decimal("0.000005"), max_digits=16, decimal_places=8)
    execution_venue: str = Field(max_length=32, default="Binance_SPOT_SIM")
    executed_at: datetime = Field(default_factory=_utcnow)


class PortfolioSnapshot(SQLModel, table=True):
    __tablename__ = "portfolio_snapshots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    total_equity_usd: Decimal = Field(max_digits=18, decimal_places=4)
    cash_balance_usd: Decimal = Field(max_digits=18, decimal_places=4)
    open_positions_value_usd: Decimal = Field(max_digits=18, decimal_places=4)
    daily_realized_pnl_usd: Decimal = Field(default=Decimal("0.0000"), max_digits=16, decimal_places=4)
    daily_loss_pct: Decimal = Field(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    high_water_mark_usd: Decimal = Field(max_digits=18, decimal_places=4)
    current_drawdown_pct: Decimal = Field(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    win_rate_pct: Decimal | None = Field(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    profit_factor: Decimal | None = Field(default=Decimal("0.00"), max_digits=6, decimal_places=2)
    net_expectancy_usd: Decimal | None = Field(default=Decimal("0.0000"), max_digits=12, decimal_places=4)
    snapshot_time: datetime = Field(default_factory=_utcnow)


# --- Domain 5: Kontrol & Kejadian Sistem -------------------------------------

class UserSetting(SQLModel, table=True):
    __tablename__ = "user_settings"

    key: str = Field(max_length=64, primary_key=True)
    value: str
    description: str | None = Field(default=None, max_length=255)
    is_mutable: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)


class IngestionError(SQLModel, table=True):
    """Dead Letter Queue — docs/03-diagrams/DATA_FLOW.mmd ("ingestion_errors table")."""

    __tablename__ = "ingestion_errors"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(max_length=32)  # BINANCE / SOLANA_RPC
    reason: str = Field(max_length=32)  # PARSE_ERROR, DUPLICATE_SIGNATURE, STALE_DATA
    reference: str | None = Field(default=None, max_length=128)
    detail: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    occurred_at: datetime = Field(default_factory=_utcnow)


class MarketOHLCV(SQLModel, table=True):
    """M1/M5/H1 aggregation of market_snapshots — ROADMAP.md TASK-2.6."""

    __tablename__ = "market_ohlcv"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    token_id: UUID = Field(foreign_key="tokens.id", index=True)
    interval: str = Field(max_length=8)  # M1, M5, H1
    bucket_time: datetime
    open: Decimal = Field(max_digits=18, decimal_places=6)
    high: Decimal = Field(max_digits=18, decimal_places=6)
    low: Decimal = Field(max_digits=18, decimal_places=6)
    close: Decimal = Field(max_digits=18, decimal_places=6)
    sample_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=_utcnow)


class SystemEvent(SQLModel, table=True):
    __tablename__ = "system_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_type: str = Field(max_length=64)
    severity: str = Field(max_length=16, default="INFO")
    message: str
    metadata_: dict = Field(default_factory=dict, sa_column=Column("metadata", JSONB))
    created_at: datetime = Field(default_factory=_utcnow)
