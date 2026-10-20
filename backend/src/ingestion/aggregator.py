"""M1/M5/H1 OHLCV aggregation from fresh market_snapshots — ROADMAP.md TASK-2.6."""
import asyncio

from sqlalchemy import text

from ..db import async_session_factory

POLL_INTERVAL_SEC = 60

# (label, bucket_sql, lookback)
BUCKETS = [
    ("M1", "date_trunc('minute', snapshot_time)", "5 minutes"),
    ("M5", "to_timestamp(floor(extract(epoch from snapshot_time) / 300) * 300)", "30 minutes"),
    ("H1", "date_trunc('hour', snapshot_time)", "4 hours"),
]

UPSERT_SQL = text(
    """
    INSERT INTO market_ohlcv (id, token_id, interval, bucket_time, open, high, low, close, sample_count)
    SELECT gen_random_uuid(), token_id, :label, bucket,
           (array_agg(price_usd ORDER BY snapshot_time ASC))[1],
           max(price_usd), min(price_usd),
           (array_agg(price_usd ORDER BY snapshot_time DESC))[1],
           count(*)
    FROM (
        SELECT token_id, snapshot_time, price_usd, (__BUCKET__) AS bucket
        FROM market_snapshots
        WHERE is_stale = false AND snapshot_time >= now() - (:lookback)::interval
    ) s
    GROUP BY token_id, bucket
    ON CONFLICT (token_id, interval, bucket_time) DO UPDATE SET
        high = excluded.high, low = excluded.low, close = excluded.close,
        sample_count = excluded.sample_count
    """
)


async def run_aggregator() -> None:
    while True:
        async with async_session_factory() as session:
            for label, bucket_sql, lookback in BUCKETS:
                sql = UPSERT_SQL.text.replace("__BUCKET__", bucket_sql)
                await session.execute(text(sql), {"label": label, "lookback": lookback})
            await session.commit()
        await asyncio.sleep(POLL_INTERVAL_SEC)
