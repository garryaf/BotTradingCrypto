"""Strict output contracts for each .agents/skills/*/SKILL.md — whatever the LLM
says, only these fields/types/literals can ever reach the database (ROADMAP
Milestone 3: "prompt injection tidak mengubah skema output")."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RegimeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    regime: Literal["TRENDING_BULLISH", "TRENDING_BEARISH", "SIDEWAYS", "VOLATILE_HIGH_RISK"]
    adx_strength: float
    volatility_state: str
    recommended_strategy_type: str
    confidence: float = Field(ge=0, le=1)


class SafetyResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    asset_identifier: str
    venue_type: str
    contract_safety_score: float
    risk_classification: str
    checks_passed: dict[str, bool] = Field(default_factory=dict)
    verdict: Literal["APPROVED", "REJECTED"]


class SignalResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signal_id: str
    symbol: str
    strategy_type: str
    action: Literal["BUY", "SELL", "HOLD"]
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    estimated_winrate_pct: float
    confidence_score: float = Field(ge=0, le=1)
    risk_reward_ratio: float
    rationale: str
