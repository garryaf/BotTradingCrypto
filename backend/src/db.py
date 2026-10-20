from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from .config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)


async def get_session() -> AsyncSession:
    async with SQLModelAsyncSession(engine) as session:
        yield session
