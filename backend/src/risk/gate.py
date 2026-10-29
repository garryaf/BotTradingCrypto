"""Deterministic Risk Gate — 9 pintu serial, fail-closed.
docs/00-overview/OPEN_QUESTIONS.md Q-08, ROADMAP.md TASK-4.1, .agents/skills/risk-gate-validation.

Pure function: no DB/network access here, so every gate is unit-testable
without a running Postgres — see test_gate.py.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from ..config import settings
from .sizing import adaptive_risk_pct, cap_to_cash, position_size

MAX_OPEN_POSITIONS = 5
MIN_24H_VOLUME_USD = Decimal("1000000")
BINANCE_TAKER_FEE_PCT = Decimal("0.0010")
DEX_TAKER_FEE_PCT = Decimal("0.0030")  # 0.30% standard Raydium/Orca AMM swap fee


@dataclass
class RiskCheckOutcome:
    passed: bool
    expectancy_check: bool
    risk_per_trade_check: bool
    daily_loss_check: bool
    drawdown_check: bool
    spread_check: bool
    stop_loss_check: bool
    balance_lot_check: bool
    max_positions_check: bool
    circuit_breaker_check: bool
    data_freshness_check: bool
    rejection_reasons: list[str] = field(default_factory=list)
    risk_pct_used: Decimal = Decimal(0)
    dollar_risk: Decimal = Decimal(0)
    quantity: Decimal = Decimal(0)
    fee_usd: Decimal = Decimal(0)


def evaluate_risk(
    *,
    action: str,
    entry_price: Decimal,
    stop_loss: Decimal,
    take_profit_1: Decimal,
    take_profit_2: Decimal,
    estimated_winrate_pct: Decimal,
    equity_usd: Decimal,
    cash_balance_usd: Decimal,
    daily_loss_pct: Decimal,
    current_drawdown_pct: Decimal,
    spread_pct: Decimal,
    volume_24h_usd: Decimal,
    snapshot_time: datetime,
    is_stale: bool,
    open_positions_count: int,
    circuit_breaker_active: bool,
    min_lot_size: Decimal,
    venue: str = "Binance_SPOT_SIM",
    max_spread_pct: Decimal | None = None,
    min_24h_volume_usd: Decimal | None = None,
) -> RiskCheckOutcome:
    reasons: list[str] = []

    is_dex = venue == "SOLANA_DEX_SIM"
    effective_taker_fee_pct = DEX_TAKER_FEE_PCT if is_dex else BINANCE_TAKER_FEE_PCT
    effective_max_spread = (
        (max_spread_pct * 100)
        if max_spread_pct is not None
        else ((settings.max_dex_spread_pct if is_dex else settings.max_spread_pct) * 100)
    )
    effective_min_volume = (
        min_24h_volume_usd
        if min_24h_volume_usd is not None
        else (settings.min_dex_24h_volume_usd if is_dex else MIN_24H_VOLUME_USD)
    )

    # Pintu 6 — Stop Loss wajib eksplisit, di sisi yang benar, DAN rasio R:R ≥ 1.5 (FR-RSK-01 baris 106).
    direction_ok = (action == "BUY" and stop_loss < entry_price) or (action == "SELL" and stop_loss > entry_price)
    sl_present = stop_loss > 0 and stop_loss != entry_price and direction_ok
    if not sl_present:
        reasons.append("INVALID_STOP_LOSS")

    # R:R sub-check: jarak TP1 ke entry ≥ min_risk_reward_ratio × risk_unit (TP1 only, FR-RSK-01).
    if sl_present:
        risk_unit = abs(entry_price - stop_loss)
        rr_ok = risk_unit > 0 and abs(take_profit_1 - entry_price) >= settings.min_risk_reward_ratio * risk_unit
        if not rr_ok:
            reasons.append("INSUFFICIENT_RISK_REWARD")
    else:
        rr_ok = False

    stop_loss_check = sl_present and rr_ok

    # Pintu 4/2 — drawdown menentukan risk_pct adaptif (Q-07), lalu dipakai untuk sizing.
    risk_pct_used = adaptive_risk_pct(settings.max_risk_per_trade_pct, current_drawdown_pct)
    risk_per_trade_check = risk_pct_used <= settings.max_risk_per_trade_pct
    if not risk_per_trade_check:
        reasons.append("RISK_PER_TRADE_EXCEEDED")

    # Sizing dihitung jika SL valid (meski R:R belum lolos); sinyal ditolak lewat stop_loss_check.
    sizing = position_size(equity_usd, risk_pct_used, entry_price, stop_loss) if sl_present else {
        "dollar_risk": Decimal(0), "quantity": Decimal(0), "capital_required": Decimal(0)
    }
    capped = cap_to_cash(sizing, cash_balance_usd, entry_price)
    fee_usd = capped["capital_required"] * effective_taker_fee_pct

    # Pintu 7 — kas & lot minimum setelah dipotong ke kas yang tersedia.
    balance_lot_check = (
        sl_present
        and capped["quantity"] >= min_lot_size
        and capped["capital_required"] + fee_usd <= cash_balance_usd + Decimal("0.01")
    )
    if not balance_lot_check:
        reasons.append("INSUFFICIENT_BALANCE_OR_LOT")

    # Pintu 1 — Expectancy positif bersih biaya. Blend TP1(1.5R)/TP2(3.0R) 50/50 per skill doc.
    winrate = estimated_winrate_pct / Decimal(100)
    if sl_present:
        _risk_unit_exp = abs(entry_price - stop_loss)
        r1 = abs(take_profit_1 - entry_price) / _risk_unit_exp if _risk_unit_exp else Decimal(0)
        r2 = abs(take_profit_2 - entry_price) / _risk_unit_exp if _risk_unit_exp else Decimal(0)
        reward_r = (r1 + r2) / 2
        fee_ratio_r = (fee_usd / sizing["dollar_risk"]) if sizing["dollar_risk"] else Decimal(1)
        expectancy_r = winrate * reward_r - (1 - winrate) - fee_ratio_r
        expectancy_check = expectancy_r > 0
    else:
        expectancy_check = False
    if not expectancy_check:
        reasons.append("NON_POSITIVE_EXPECTANCY")

    # Pintu 3 — Daily loss limit (persen, bukan pecahan — konsisten dgn portfolio_snapshots.daily_loss_pct).
    daily_loss_check = daily_loss_pct < settings.daily_loss_limit_pct * 100
    if not daily_loss_check:
        reasons.append("DAILY_LOSS_LIMIT_EXCEEDED")

    # Pintu 4 — Drawdown limit.
    drawdown_check = current_drawdown_pct < settings.max_drawdown_limit_pct * 100
    if not drawdown_check:
        reasons.append("DRAWDOWN_LIMIT_EXCEEDED")

    # Pintu 5 — Spread & likuiditas.
    spread_check = spread_pct <= effective_max_spread and volume_24h_usd >= effective_min_volume
    if not spread_check:
        reasons.append("SPREAD_OR_LIQUIDITY_INADEQUATE")

    # Pintu 8 — Batas posisi terbuka maksimal.
    max_positions_check = open_positions_count < MAX_OPEN_POSITIONS
    if not max_positions_check:
        reasons.append("MAX_OPEN_POSITIONS_REACHED")

    # Pintu 8b (DATA_DICTIONARY) — Circuit breaker / freeze.
    circuit_breaker_check = not circuit_breaker_active
    if not circuit_breaker_check:
        reasons.append("CIRCUIT_BREAKER_ACTIVE")

    # Pintu 9 — Freshness data.
    age_sec = (datetime.now(timezone.utc) - snapshot_time).total_seconds()
    data_freshness_check = (not is_stale) and age_sec <= settings.data_freshness_max_age_sec
    if not data_freshness_check:
        reasons.append("STALE_MARKET_DATA")

    all_checks = [
        expectancy_check, risk_per_trade_check, daily_loss_check, drawdown_check, spread_check,
        stop_loss_check, balance_lot_check, max_positions_check, circuit_breaker_check, data_freshness_check,
    ]

    return RiskCheckOutcome(
        passed=all(all_checks),
        expectancy_check=expectancy_check,
        risk_per_trade_check=risk_per_trade_check,
        daily_loss_check=daily_loss_check,
        drawdown_check=drawdown_check,
        spread_check=spread_check,
        stop_loss_check=stop_loss_check,
        balance_lot_check=balance_lot_check,
        max_positions_check=max_positions_check,
        circuit_breaker_check=circuit_breaker_check,
        data_freshness_check=data_freshness_check,
        rejection_reasons=reasons,
        risk_pct_used=risk_pct_used,
        dollar_risk=sizing["dollar_risk"],
        quantity=capped["quantity"],
        fee_usd=fee_usd,
    )
