"""Cross-implementation parity: Python gate (gate.py) vs Rust engine (/evaluate).

Closes F-02: proves both reach the SAME pass/fail verdict on identical input.
Two ways to run:
    PARITY_ENGINE_URL=http://engine:8080 python -m src.risk.test_parity   # a running engine (Docker image)
    cargo build --release && python -m src.risk.test_parity               # spawns ../engine native binary

Skips with a clear message if neither is available — it is a parity harness, not a
unit test, so it must not fail the suite when the engine isn't built here.
"""
import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from decimal import Decimal
from pathlib import Path

from .. import config
from .gate import MAX_OPEN_POSITIONS, MIN_24H_VOLUME_USD, evaluate_risk

ENGINE_BIN = Path(__file__).resolve().parents[3] / "engine" / "target" / "release" / "auto-trade-engine"
NOW = datetime.now(timezone.utc)

# Same raw inputs fed to BOTH implementations. Mirrors risk/engine.py _signal_candidate.
BASELINE = dict(
    action="BUY", entry_price=Decimal(150), stop_loss=Decimal(145),
    take_profit_1=Decimal(160), take_profit_2=Decimal(170),
    estimated_winrate_pct=Decimal(60), equity_usd=Decimal(10000),
    cash_balance_usd=Decimal(10000), daily_loss_pct=Decimal(0),
    current_drawdown_pct=Decimal(0), spread_pct=Decimal("0.01"),
    volume_24h_usd=Decimal(2_000_000), snapshot_time=NOW, is_stale=False,
    open_positions_count=0, circuit_breaker_active=False, min_lot_size=Decimal("0.001"),
)

# Matrix: each case is a single-field override exercising a different gate boundary.
CASES = [
    ("baseline_pass", {}),
    ("risk_cap_boundary", {}),  # risk_pct_used is structural; baseline already at cap
    ("daily_loss_exceeded", {"daily_loss_pct": Decimal(3)}),
    ("drawdown_exceeded", {"current_drawdown_pct": Decimal(9)}),
    ("wide_spread", {"spread_pct": Decimal("0.5")}),
    ("thin_liquidity", {"volume_24h_usd": Decimal(100)}),
    ("max_positions", {"open_positions_count": 5}),
    ("fourth_position_ok", {"open_positions_count": 4}),
    ("stale_data", {"snapshot_time": NOW.replace(year=NOW.year - 1)}),
    ("bad_stop_loss", {"stop_loss": Decimal(155)}),  # above entry on a BUY
    ("low_winrate_neg_expectancy", {"estimated_winrate_pct": Decimal(10)}),
    ("rr_below_minimum", {"take_profit_1": Decimal(155)}),  # TP1 at 1.0R < 1.5R minimum
]


def _candidate(inputs: dict, outcome) -> dict:
    """Exactly the payload risk/engine.py._signal_candidate builds."""
    age = int((datetime.now(timezone.utc) - inputs["snapshot_time"]).total_seconds())
    return {
        "signal_id": "parity-1", "symbol": "SOLUSDT", "action": inputs["action"],
        "target_entry_price": float(inputs["entry_price"]),
        "suggested_stop_loss": float(inputs["stop_loss"]),
        "suggested_take_profit_1": float(inputs["take_profit_1"]),
        "suggested_take_profit_2": float(inputs["take_profit_2"]),
        "recommended_allocation_pct": float(outcome.risk_pct_used),
        "confidence_score": 0.9,
        "estimated_winrate_pct": float(inputs["estimated_winrate_pct"]),
        "dollar_risk": float(outcome.dollar_risk),
        "fee_usd": float(outcome.fee_usd),
        "limits": {  # same single-source block _signal_candidate sends
            "max_risk_per_trade_pct": float(config.settings.max_risk_per_trade_pct),
            "daily_loss_limit_pct": float(config.settings.daily_loss_limit_pct * 100),
            "max_drawdown_limit_pct": float(config.settings.max_drawdown_limit_pct * 100),
            "max_spread_pct": float(config.settings.max_spread_pct * 100),
            "min_24h_volume_usd": float(MIN_24H_VOLUME_USD),
            "max_open_positions": MAX_OPEN_POSITIONS,
            "data_freshness_max_age_sec": config.settings.data_freshness_max_age_sec,
            "min_risk_reward_ratio": float(config.settings.min_risk_reward_ratio),
        },
        "snapshot": {
            "price_usd": float(inputs["entry_price"]), "bid_price": float(inputs["entry_price"]),
            "ask_price": float(inputs["entry_price"]), "spread_pct": float(inputs["spread_pct"]),
            "snapshot_age_seconds": age, "pool_liquidity_usd": float(inputs["volume_24h_usd"]),
        },
        "portfolio": {
            "total_equity_usd": float(inputs["equity_usd"]), "cash_balance_usd": float(inputs["cash_balance_usd"]),
            "daily_realized_pnl_usd": 0.0, "daily_loss_pct": float(inputs["daily_loss_pct"]),
            "high_water_mark_usd": float(inputs["equity_usd"]),
            "current_drawdown_pct": float(inputs["current_drawdown_pct"]),
            "open_positions_count": inputs["open_positions_count"],
        },
    }


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _post(host: str, port: int, payload: dict) -> dict:
    # Raw socket keeps this harness dependency-free (pydantic-settings only). Request framing with
    # split TCP writes — what httpx does — is covered by cargo test and test_engine_e2e mode=up.
    body = json.dumps(payload).encode()
    req = (
        b"POST /evaluate HTTP/1.1\r\nHost: %b\r\nContent-Type: application/json\r\n"
        b"Content-Length: %d\r\nConnection: close\r\n\r\n%b"
        % (host.encode(), len(body), body)
    )
    with socket.create_connection((host, port), timeout=2) as s:
        s.sendall(req)
        chunks = []
        while True:
            b = s.recv(4096)
            if not b:
                break
            chunks.append(b)
    raw = b"".join(chunks)
    status = int(raw.split(b"\r\n", 1)[0].split(b" ")[1])
    json_body = raw.split(b"\r\n\r\n", 1)[1]
    if status != 200:
        raise OSError(f"engine HTTP {status}: {json_body!r}")
    return json.loads(json_body)


def run_parity() -> None:
    proc = None
    if os.environ.get("PARITY_ENGINE_URL"):
        url = urlparse(os.environ["PARITY_ENGINE_URL"])
        host, port = url.hostname, url.port or 80
    elif ENGINE_BIN.exists():
        host, port = "127.0.0.1", _free_port()
        proc = subprocess.Popen([str(ENGINE_BIN), f"{host}:{port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print(f"SKIP parity: set PARITY_ENGINE_URL or build {ENGINE_BIN} (`cargo build --release` in engine/).")
        return

    try:
        for _ in range(50):  # wait for listener
            try:
                _post(host, port, {"signal_id": "ping", "symbol": "X", "action": "BUY"})
                break
            except OSError:
                time.sleep(0.05)

        mismatches = []
        for name, override in CASES:
            inputs = {**BASELINE, **override}
            py = evaluate_risk(**inputs)
            rust = _post(host, port, _candidate(inputs, py))
            # Parity contract: same pass/fail verdict on identical input.
            if bool(rust["passed"]) != bool(py.passed):
                mismatches.append((name, py.passed, rust["passed"], py.rejection_reasons, rust.get("rejection_reasons")))
        assert not mismatches, "Python/Rust verdict mismatch:\n" + "\n".join(str(m) for m in mismatches)
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)


if __name__ == "__main__":
    run_parity()
    print("ok")
