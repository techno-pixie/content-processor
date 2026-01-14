import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from processor_app.repositories.repository import Repository
from processor_app.content_processor_service.schema import Base
from processor_app.config import (DATABASE_URL)
logger = logging.getLogger(__name__)


class ProcessorRepository(Repository):
    def __init__(self) -> None:
        # DATABASE_URL = "sqlite+aiosqlite:///./submissions.db"
        self._engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            echo=False,
            future=True
        )
        
        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        logger.info(f"Database engine created: {DATABASE_URL}")

    async def init_db(self) -> None:
        if self._engine is None:
            raise RuntimeError("Database engine not initialized")
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")

    def get_session(self) -> AsyncSession:
        if self._session_maker is None:
            raise RuntimeError("Session maker not initialized")
        return self._session_maker()