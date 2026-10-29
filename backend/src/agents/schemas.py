"""Strict output contracts for each .agents/skills/*/SKILL.md — whatever the LLM
says, only these fields/types/literals can ever reach the database (ROADMAP
Milestone 3: "prompt injection tidak mengubah skema output")."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegimeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    regime: Literal["TRENDING_BULLISH", "TRENDING_BEARISH", "SIDEWAYS", "VOLATILE_HIGH_RISK"]
    adx_strength: float | None = None  # ADX isn't in the context (indicators.py is EMA/RSI only); model returns null
    volatility_state: str
    recommended_strategy_type: str
    confidence: float = Field(ge=0, le=1)


class SafetyResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset_identifier: str
    venue_type: str
    contract_safety_score: float
    risk_classification: str
    checks_passed: dict[str, bool | None] = Field(default_factory=dict)  # null = check N/A for the venue
    verdict: Literal["APPROVED", "REJECTED"]


class SignalResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signal_id: str
    symbol: str
    strategy_type: str
    action: Literal["BUY", "SELL", "HOLD", "NO_TRADE"]  # NO_TRADE: score < 0.75 per SKILL.md
    # Price fields are null when the model decides not to trade; hermes drops BUY/SELL missing any of them.
    entry_price: float | None = None
    stop_loss: float | None = None
    take_profit_1: float | None = None
    take_profit_2: float | None = None
    estimated_winrate_pct: float | None = None
    confidence_score: float | None = Field(default=0.0, ge=0, le=1)
    risk_reward_ratio: float | None = None
    rationale: str
