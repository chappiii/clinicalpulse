from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from clinicalpulse.core.config import settings

engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10)

async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
