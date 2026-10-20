"""Position sizing & adaptive risk — .agents/skills/position-sizing-compounding/SKILL.md."""
from decimal import Decimal


def adaptive_risk_pct(base_risk_pct: Decimal, current_drawdown_pct: Decimal) -> Decimal:
    """Drawdown >=5% -> 0.25%, >=3% -> 0.35%, else the configured base (0.5%)."""
    if current_drawdown_pct >= 5:
        return Decimal("0.0025")
    if current_drawdown_pct >= 3:
        return Decimal("0.0035")
    return base_risk_pct


def position_size(equity_usd: Decimal, risk_pct: Decimal, entry_price: Decimal, stop_loss: Decimal) -> dict:
    """Lot Size = (Equity * risk_pct) / |Entry - StopLoss| — ROADMAP Q-07/TASK-4.3."""
    risk_per_unit = abs(entry_price - stop_loss)
    dollar_risk = equity_usd * risk_pct
    if risk_per_unit <= 0:
        return {"dollar_risk": dollar_risk, "quantity": Decimal(0), "capital_required": Decimal(0)}
    quantity = dollar_risk / risk_per_unit
    return {
        "dollar_risk": dollar_risk,
        "quantity": quantity,
        "capital_required": quantity * entry_price,
    }


def cap_to_cash(sizing: dict, cash_balance_usd: Decimal, entry_price: Decimal) -> dict:
    """Jika modal yang dibutuhkan melebihi kas, potong kuantitas tanpa melanggar batas risiko (bukan menaikkannya)."""
    if sizing["capital_required"] <= cash_balance_usd or entry_price <= 0:
        return sizing
    capped_quantity = cash_balance_usd / entry_price
    return {**sizing, "quantity": capped_quantity, "capital_required": cash_balance_usd}
