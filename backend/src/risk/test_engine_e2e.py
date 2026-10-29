"""Risk Engine end-to-end against a real Postgres.

- A PENDING signal that passes the gate produces exactly one RiskCheck(passed), PaperOrder,
  Position, PaperTrades and a new PortfolioSnapshot.
- Offering the same signal again (crash/restart before DISPATCHED) creates nothing new (F-13).
- A rejected signal gets a RiskCheck but no order.
- TP1 then stop-loss exits close the position and update the account snapshot (F-26).
- _dispatch_pending leaves a signal with no market data PENDING (F-15) and survives a DB error
  without killing the loop (F-14).

E2E_ENGINE_MODE says how the optional Rust gate is wired (ENGINE_URL):
  off  (default) no ENGINE_URL — Python gate only
  up   ENGINE_URL -> a running engine: the real _signal_candidate payload must pass it too
  down ENGINE_URL -> a closed port: fail-closed (rejected, ENGINE_UNAVAILABLE, account frozen)

Needs DATABASE_URL on a migrated disposable DB — see scripts/run_integration_tests.sh.
Skips cleanly if DATABASE_URL isn't set.
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal


def run_e2e() -> None:
    if not os.environ.get("DATABASE_URL"):
        print("SKIP e2e: DATABASE_URL not set (needs a migrated disposable Postgres).")
        return
    mode = os.environ.get("E2E_ENGINE_MODE", "off")

    from sqlalchemy import text
    from sqlmodel import select

    from . import engine as risk_engine
    from ..config import settings
    from ..db import async_session_factory
    from ..models import (
        AgentRun, BinanceCredential, MarketSnapshot, PaperOrder, PaperTrade, Position,
        PortfolioSnapshot, RiskCheck, Token, TradingSignal, User, UserSetting,
    )

    assert (mode == "off") == (not settings.engine_url), f"E2E_ENGINE_MODE={mode} but ENGINE_URL={settings.engine_url!r}"

    def new_signal(run_id, token_id, stop_loss=Decimal(95)) -> TradingSignal:
        return TradingSignal(
            agent_run_id=run_id, token_id=token_id, symbol="BTCUSDT", action="BUY",
            target_entry_price=Decimal(100), suggested_stop_loss=stop_loss,
            suggested_take_profit_1=Decimal(110), suggested_take_profit_2=Decimal(120),
            confidence_score=Decimal("0.9"), estimated_winrate_pct=Decimal(60),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )

    async def run():
        async with async_session_factory() as s:
            # Synthetic, clearly-tagged fixtures. Ids are captured up front: a rollback later in
            # the test expires every loaded object.
            user = User(email=f"e2e-{uuid.uuid4().hex[:8]}@test.local", password_hash="x", role="user")
            token = Token(address=f"E2E-BTCUSDT-{uuid.uuid4().hex[:6]}", chain="binance", symbol="BTC",
                          min_lot_size=Decimal("0.00001"))
            run_row = AgentRun(agent_name="TEST", task_type="E2E", status="SUCCESS")
            s.add_all([user, token, run_row])
            await s.commit()
            user_id, token_id, run_id = user.id, token.id, run_row.id
            s.add(BinanceCredential(user_id=user_id, api_key_encrypted="x", api_secret_encrypted="x"))
            s.add(MarketSnapshot(
                token_id=token_id, price_usd=Decimal(100), bid_price=Decimal("99.99"), ask_price=Decimal("100.01"),
                spread_pct=Decimal("0.01"), volume_24h_usd=Decimal(50_000_000),
                snapshot_time=datetime.now(timezone.utc), is_stale=False,
            ))
            sig = new_signal(run_id, token_id)
            s.add(sig)
            await s.commit()
            sig_id = sig.id

            async def checks_for(signal_id):
                return (await s.exec(select(RiskCheck).where(
                    RiskCheck.trading_signal_id == signal_id, RiskCheck.user_id == user_id))).all()

            async def user_orders():
                return (await s.exec(select(PaperOrder).join(RiskCheck, PaperOrder.risk_check_id == RiskCheck.id)
                                     .where(RiskCheck.user_id == user_id))).all()

            async def status_of(signal_id):
                return (await s.exec(select(TradingSignal.status).where(TradingSignal.id == signal_id))).one()

            assert await risk_engine._process_signal(s, sig, user_id) is True
            checks = await checks_for(sig_id)
            assert len(checks) == 1, [c.rejection_reasons for c in checks]

            if mode == "down":
                assert not checks[0].passed and "ENGINE_UNAVAILABLE" in checks[0].rejection_reasons, checks[0].rejection_reasons
                assert await user_orders() == [], "fail-closed: no order while the engine is unreachable"
                flag = await s.get(UserSetting, f"ACCOUNT_CIRCUIT_BREAKER:{user_id}")
                assert flag is not None and flag.value == "true", "an unreachable engine must freeze the account"
                return

            assert checks[0].passed, checks[0].rejection_reasons
            orders = await user_orders()
            positions = (await s.exec(select(Position).where(Position.user_id == user_id))).all()
            assert len(orders) == 1 and len(positions) == 1 and positions[0].current_quantity > 0, (orders, positions)
            snaps = (await s.exec(select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id))).all()
            assert len(snaps) >= 2, f"expected seed + post-fill snapshot, got {len(snaps)}"
            latest = max(snaps, key=lambda x: x.snapshot_time)
            # Cost-basis convention: cash drops by notional + fee, positions carry the notional.
            assert latest.cash_balance_usd < settings.initial_paper_capital_usd, latest.cash_balance_usd
            assert latest.open_positions_value_usd > 0, latest.open_positions_value_usd

            # F-13: the same signal offered again must not produce a second verdict or order.
            assert await risk_engine._process_signal(s, sig, user_id) is True
            assert len(await checks_for(sig_id)) == 1 and len(await user_orders()) == 1, "duplicate execution"

            # A rejected signal gets a verdict but never an order.
            bad = new_signal(run_id, token_id, stop_loss=Decimal(105))  # wrong side for a BUY
            s.add(bad)
            await s.commit()
            bad_id = bad.id
            assert await risk_engine._process_signal(s, bad, user_id) is True
            [bad_check] = await checks_for(bad_id)
            assert not bad_check.passed and "INVALID_STOP_LOSS" in bad_check.rejection_reasons, bad_check.rejection_reasons
            assert len(await user_orders()) == 1, "a rejected signal must not create an order"

            if mode == "up":
                return  # the dispatch loop doesn't depend on the engine; covered in mode=off

            # F-26: a TP1 exit then a stop-loss exit must really close the position. Exit fills used to be
            # booked with paper_order_id = position.id, which broke the paper_trades FK on every exit, so
            # no position ever closed and the account snapshot never moved.
            [pos] = positions
            opened_qty = pos.current_quantity
            entry_fills = len((await s.exec(select(PaperTrade).where(PaperTrade.position_id == pos.id))).all())
            for price in (Decimal(111), Decimal(94)):  # above TP1 (110), then below the breakeven stop
                s.add(MarketSnapshot(token_id=token_id, price_usd=price, bid_price=price, ask_price=price,
                                     spread_pct=Decimal("0.01"), volume_24h_usd=Decimal(50_000_000),
                                     snapshot_time=datetime.now(timezone.utc)))
                await s.commit()
                await risk_engine._monitor_positions(s)
                await s.refresh(pos)
                if price == 111:
                    assert pos.status == "PARTIALLY_CLOSED" and pos.is_tp1_hit, pos.status
                    assert abs(pos.current_quantity - opened_qty / 2) < Decimal("0.00000002"), pos.current_quantity
                    assert pos.current_stop_loss == pos.average_entry_price  # stop moved to breakeven
            assert pos.status == "CLOSED" and pos.current_quantity == 0 and pos.closed_at is not None, pos.status
            assert pos.realized_pnl_usd > 0, pos.realized_pnl_usd  # +11/unit on half beats -6/unit on the other half
            trades = (await s.exec(select(PaperTrade).where(PaperTrade.position_id == pos.id))).all()
            assert len(trades) == entry_fills + 2 and {t.paper_order_id for t in trades} == {orders[0].id}
            latest = max((await s.exec(select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id))).all(),
                         key=lambda x: x.snapshot_time)
            assert latest.open_positions_value_usd == 0, latest.open_positions_value_usd
            assert latest.cash_balance_usd > settings.initial_paper_capital_usd, latest.cash_balance_usd

            # F-15: no market data for the token -> nobody can judge it -> stays PENDING (expires later).
            dry_token = Token(address=f"E2E-NOMKT-{uuid.uuid4().hex[:6]}", chain="binance", symbol="NOMKT")
            s.add(dry_token)
            await s.commit()
            dry = new_signal(run_id, dry_token.id)
            s.add(dry)
            await s.commit()
            dry_id = dry.id
            await risk_engine._dispatch_pending(s)
            assert await status_of(dry_id) == "PENDING"
            assert await checks_for(dry_id) == []
            assert await status_of(sig_id) == "DISPATCHED" and await status_of(bad_id) == "DISPATCHED"

            # F-14: a DB error mid-execution must not poison the session and kill the risk loop.
            flaky = new_signal(run_id, token_id)
            s.add(flaky)
            await s.commit()
            flaky_id = flaky.id
            real_process_signal = risk_engine._process_signal

            async def db_error(session, signal, uid, client=None):
                await session.exec(text("SELECT 1/0"))

            risk_engine._process_signal = db_error
            try:
                await risk_engine._dispatch_pending(s)  # must return, not raise
            finally:
                risk_engine._process_signal = real_process_signal
            assert await status_of(flaky_id) == "PENDING", "a failed signal must stay PENDING for the retry"
            await risk_engine._dispatch_pending(s)  # next round: session healthy, signal executes once
            assert await status_of(flaky_id) == "DISPATCHED"
            assert len(await checks_for(flaky_id)) == 1 and len(await user_orders()) == 2

    asyncio.run(run())


if __name__ == "__main__":
    run_e2e()
    print("ok")
