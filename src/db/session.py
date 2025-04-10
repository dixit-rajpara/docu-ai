from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)

from config.settings import settings
from config.logger import get_logger


logger = get_logger(__name__)


def create_async_engine_and_sessionmaker():
    """Creates the async engine and session maker using settings."""
    # --- Use settings for configuration ---
    db_settings = settings.database
    # Log safely, database_url_str property uses the DSN which masks password
    # by default
    logger.info(f"Creating database engine for URL: {db_settings.database_url_str}")

    try:
        engine = create_async_engine(
            db_settings.database_url_str,  # Use the string representation
            echo=db_settings.echo,  # Use echo setting
            pool_size=db_settings.pool_size,
            max_overflow=db_settings.max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        SessionLocal = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        logger.info("Database engine and session maker created successfully.")
        return engine, SessionLocal
    except Exception as e:
        # Log the specific error during engine creation
        logger.critical(
            f"Failed to create database engine for {db_settings.database_url_str} "
            f"(User: {db_settings.user}, Host: {db_settings.host}): {e}",
            exc_info=True,
        )
        raise


# Create engine and session instances
async_engine, AsyncSessionLocal = create_async_engine_and_sessionmaker()


# Optional: Dependency for FastAPI or other frameworks
async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
