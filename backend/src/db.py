from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession as SQLModelAsyncSession

from .config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)

# expire_on_commit=False: ingestion loops keep using ORM objects (wallet.id, token.id)
# across several commits in a row; the default expire-on-commit forces a lazy
# refresh on next access, which SQLAlchemy can't do silently in async code
# (raises MissingGreenlet) — see backend/src/ingestion/*.
async_session_factory = async_sessionmaker(engine, class_=SQLModelAsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session
