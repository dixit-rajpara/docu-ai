from .interface import AbstractDBRepository
from .postgres import PostgresDBRepository
from .session import async_engine, AsyncSessionLocal, get_db_session
from .models import Base, DataSource, Document, DocumentChunk
from config.logger import get_logger

logger = get_logger(__name__)  # Get logger for this module


# Utility function for setup
async def init_db():
    """Initializes the database by creating tables."""
    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment with extreme caution!
        await conn.run_sync(Base.metadata.create_all)


async def shutdown_db_engine():
    """Disposes the SQLAlchemy async engine."""
    logger.info("Shutting down database engine explicitly.")
    await async_engine.dispose()


__all__ = [
    "AbstractDBRepository",
    "PostgresDBRepository",
    "async_engine",
    "AsyncSessionLocal",
    "get_db_session",  # If using dependency injection
    "Base",
    "DataSource",
    "Document",
    "DocumentChunk",
    "init_db",
    "shutdown_db_engine",
]
