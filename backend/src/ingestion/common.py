import logging
from datetime import datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import settings
from ..models import IngestionError

logger = logging.getLogger("ingestion")


async def log_dlq(session: AsyncSession, source: str, reason: str, reference: str | None, detail: dict) -> None:
    session.add(IngestionError(source=source, reason=reason, reference=reference, detail=detail))
    await session.commit()
    logger.warning("DLQ %s/%s ref=%s", source, reason, reference)


def is_stale(event_time: datetime) -> bool:
    age = (datetime.now(timezone.utc) - event_time).total_seconds()
    return age > settings.data_freshness_max_age_sec
