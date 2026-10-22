"""Python -> Rust Risk Gate IPC client — RUST_ENGINE_INTEGRATION_SPEC.md §3-5.

Fail-closed: any timeout, HTTP error, bad payload or inconsistent verdict
returns a rejection. Never raises, so a broken engine can't let a signal through.
"""
import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from ..config import settings


class RiskEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signal_id: str
    passed: bool
    gates: dict[str, bool]
    rejection_reasons: list[str] = []


async def call_risk_engine(candidate: dict, client: httpx.AsyncClient | None = None) -> tuple[bool, list[str]]:
    """Returns (passed, rejection_reasons). ENGINE_UNAVAILABLE tells the caller to freeze trading (spec §5)."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    try:
        res = await client.post(
            f"{settings.engine_url.rstrip('/')}/evaluate",
            json=candidate,
            timeout=settings.engine_timeout_ms / 1000,
        )
        res.raise_for_status()
        result = RiskEvaluationResult.model_validate(res.json())
    except httpx.TimeoutException:
        return False, ["ENGINE_TIMEOUT"]
    except httpx.ConnectError:
        return False, ["ENGINE_UNAVAILABLE"]
    except httpx.HTTPError:
        return False, ["ENGINE_ERROR"]
    except (ValueError, ValidationError):
        return False, ["ENGINE_INVALID_RESPONSE"]
    finally:
        if owns_client:
            await client.aclose()

    # A verdict for another signal, or "passed" with a failed/missing gate, is not a verdict we trust.
    if result.signal_id != candidate["signal_id"] or (result.passed and not (result.gates and all(result.gates.values()))):
        return False, ["ENGINE_INVALID_RESPONSE"]
    if not result.passed:
        return False, result.rejection_reasons or ["ENGINE_REJECTED"]
    return True, []
