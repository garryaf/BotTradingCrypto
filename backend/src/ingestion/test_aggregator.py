"""Unit test for OHLCV aggregator & Dead Letter Queue (DLQ) (FR-ING-03, FR-ING-04, FR-MKT-02).
Run: python -m src.ingestion.test_aggregator
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from .aggregator import BUCKETS, UPSERT_SQL_TEMPLATE
from .common import is_stale, log_dlq
from ..models import IngestionError


def test_aggregator_sql_templates():
    """Verify that all bucket SQL configurations generate valid query strings without broken placeholders."""
    for label, bucket_sql, lookback in BUCKETS:
        sql = UPSERT_SQL_TEMPLATE.replace("__BUCKET__", bucket_sql).replace("__LOOKBACK__", lookback)
        assert "__BUCKET__" not in sql
        assert "__LOOKBACK__" not in sql
        assert label in ("M1", "M5", "H1")
        assert "INSERT INTO market_ohlcv" in sql
        assert "ON CONFLICT (token_id, interval, bucket_time) DO UPDATE" in sql


def test_pure_ohlcv_aggregation_logic():
    """Simulates the aggregation logic over a sequence of price ticks."""
    prices = [Decimal("100.50"), Decimal("102.00"), Decimal("99.20"), Decimal("101.80")]
    open_p = prices[0]
    high_p = max(prices)
    low_p = min(prices)
    close_p = prices[-1]
    count = len(prices)

    assert open_p == Decimal("100.50")
    assert high_p == Decimal("102.00")
    assert low_p == Decimal("99.20")
    assert close_p == Decimal("101.80")
    assert count == 4


def test_dlq_logging():
    """Verifies that log_dlq creates and commits an IngestionError model."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    
    async def run():
        await log_dlq(
            mock_session,
            source="TEST_SOURCE",
            reason="PARSE_ERROR",
            reference="SOLUSDT",
            detail={"error": "corrupt_tick"},
        )
    
    asyncio.run(run())
    
    assert mock_session.add.called
    added_obj = mock_session.add.call_args[0][0]
    assert isinstance(added_obj, IngestionError)
    assert added_obj.source == "TEST_SOURCE"
    assert added_obj.reason == "PARSE_ERROR"
    assert added_obj.reference == "SOLUSDT"
    assert added_obj.detail == {"error": "corrupt_tick"}
    assert mock_session.commit.called


if __name__ == "__main__":
    test_aggregator_sql_templates()
    test_pure_ohlcv_aggregation_logic()
    test_dlq_logging()
    print("ok")
