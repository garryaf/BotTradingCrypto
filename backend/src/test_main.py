"""Plain-assert self-check for the background-loop states /health reports (GAP-14).
No DB needed. Run: python -m src.test_main
"""
import asyncio

from .main import _task_state


async def _states() -> dict:
    async def forever():
        await asyncio.sleep(3600)

    async def idle():
        return None  # e.g. Hermes/Telegram returning early because they're unconfigured

    async def boom():
        raise RuntimeError("loop crashed")

    running = asyncio.create_task(forever())
    exited = asyncio.create_task(idle())
    crashed = asyncio.create_task(boom())
    cancelled = asyncio.create_task(forever())
    await asyncio.sleep(0)
    cancelled.cancel()
    await asyncio.gather(exited, crashed, cancelled, return_exceptions=True)
    states = {name: _task_state(t) for name, t in
              [("running", running), ("exited", exited), ("crashed", crashed), ("cancelled", cancelled)]}
    running.cancel()
    return states


def test_task_states():
    assert asyncio.run(_states()) == {
        "running": "running", "exited": "exited", "crashed": "crashed", "cancelled": "cancelled",
    }


if __name__ == "__main__":
    test_task_states()
    print("ok")
