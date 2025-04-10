from .interface import AbstractDBRepository
from .postgres import PostgresDBRepository
from .session import async_engine, AsyncSessionLocal, get_db_session
from .models import Base, DataSource, Document, DocumentChunk


# Utility function for setup
async def init_db():
    """Initializes the database by creating tables."""
    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Uncomment with extreme caution!
        await conn.run_sync(Base.metadata.create_all)


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
]
