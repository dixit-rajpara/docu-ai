from typing import List, Optional, Tuple

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import (
    selectinload,
)  # Use selectinload for eager loading relationships
from sqlalchemy.exc import IntegrityError

from .interface import AbstractDBRepository
from .models import (
    DataSource,
    Document,
    DocumentChunk,
    Base,
)  # Import Base for table creation
from config.settings import settings
from config.logger import get_logger

logger = get_logger(__name__)

# Type alias for the query vector
QueryVector = List[float]


class PostgresDBRepository(AbstractDBRepository):
    """PostgreSQL implementation of the database repository."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession], engine):
        self.session_maker = session_maker
        self.engine = engine  # Keep engine reference for table creation/deletion

    async def initialize(self) -> None:
        """Creates database tables if they don't exist."""
        logger.info("Initializing database schema...")
        async with self.engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all) # Use with caution!
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized.")

    async def shutdown(self) -> None:
        """Disposes the database engine."""
        logger.info("Shutting down database engine.")
        await self.engine.dispose()

    async def get_or_create_data_source(
        self,
        name: str,
        base_url: Optional[str] = None,
        identifier: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DataSource:
        """Gets an existing data source by name or creates a new one."""
        async with self.session_maker() as session:
            try:
                # Attempt to fetch existing source
                stmt = select(DataSource).where(DataSource.name == name)
                result = await session.execute(stmt)
                source = result.scalar_one_or_none()

                if source:
                    logger.debug(f"Found existing data source: {name}")
                    # Optionally update existing source details if needed here
                    # source.base_url = base_url or source.base_url
                    # ...
                    # await session.commit()
                    return source
                else:
                    # Create new source
                    logger.info(f"Creating new data source: {name}")
                    new_source = DataSource(
                        name=name,
                        base_url=base_url,
                        identifier=identifier,
                        metadata_=metadata,
                    )
                    session.add(new_source)
                    await session.commit()
                    await session.refresh(
                        new_source
                    )  # Refresh to get DB defaults like ID and timestamp
                    return new_source
            except IntegrityError as e:
                await session.rollback()
                logger.error(
                    f"Integrity error getting or creating data source '{name}': {e}",
                    exc_info=True,
                )
                # Attempt to fetch again in case of race condition
                stmt = select(DataSource).where(DataSource.name == name)
                result = await session.execute(stmt)
                source = (
                    result.scalar_one()
                )  # Should exist now if IntegrityError was due to concurrent creation
                return source
            except Exception as e:
                await session.rollback()
                logger.error(
                    f"Error getting or creating data source '{name}': {e}",
                    exc_info=True,
                )
                raise

    async def add_document(
        self,
        source_id: int,
        url: str,
        title: Optional[str] = None,
        last_modified: Optional[str] = None,  # Assuming datetime string or object
        content_hash: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Document:
        """Adds a new document linked to a data source."""
        async with self.session_maker() as session:
            try:
                # Consider adding logic here to check if document already
                # exists based on URL/hash
                # and update instead of inserting if needed.
                new_doc = Document(
                    source_id=source_id,
                    url=url,
                    title=title,
                    # SQLAlchemy handles datetime conversion if type matches
                    last_modified=last_modified,
                    content_hash=content_hash,
                    metadata_=metadata,
                )
                session.add(new_doc)
                await session.commit()
                await session.refresh(new_doc)
                logger.debug(f"Added document: ID={new_doc.document_id}, URL={url}")
                return new_doc
            except Exception as e:
                await session.rollback()
                logger.error(
                    f"Error adding document with URL '{url}' for "
                    f"source {source_id}: {e}",
                    exc_info=True,
                )
                raise

    async def get_document_by_url(self, source_id: int, url: str) -> Optional[Document]:
        """Retrieves a document by its source ID and URL."""
        async with self.session_maker() as session:
            stmt = select(Document).where(
                Document.source_id == source_id, Document.url == url
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def add_document_chunks(self, chunks_data: List[dict]) -> List[DocumentChunk]:
        """Adds multiple document chunks in bulk using ORM bulk insert."""
        if not chunks_data:
            return []

        async with self.session_maker() as session:
            try:
                # Convert dicts to ORM objects
                chunk_objects = [DocumentChunk(**data) for data in chunks_data]
                session.add_all(chunk_objects)
                await session.commit()
                # Note: bulk insert doesn't easily return IDs/defaults like
                # individual add+refresh
                # If you need the created objects with IDs, fetch them separately or
                # insert individually (less efficient)
                logger.info(
                    f"Added {len(chunk_objects)} chunks for document ID "
                    f"{chunks_data[0].get('document_id')}."
                )
                # Return the objects added (they might not have IDs populated
                # unless refreshed)
                return chunk_objects
            except Exception as e:
                await session.rollback()
                doc_id = chunks_data[0].get("document_id", "unknown")
                logger.error(
                    f"Error adding chunks for document {doc_id}: {e}", exc_info=True
                )
                raise

    async def find_similar_chunks(
        self,
        query_vector: QueryVector,
        limit: int = 5,
        min_similarity: Optional[float] = None,
        source_ids: Optional[List[int]] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Finds document chunks similar to the query_vector using cosine similarity.
        Returns list of (DocumentChunk, similarity_score).
        """
        expected_dim = settings.core.embedding_dimension
        if len(query_vector) != expected_dim:
            raise ValueError(
                f"Query vector dimension ({len(query_vector)}) does not match "
                f"expected dimension ({expected_dim})"
            )

        async with self.session_maker() as session:
            # Cosine distance = 1 - Cosine Similarity
            # We want highest similarity, so order by distance ASCENDING.
            distance_function = DocumentChunk.embedding.cosine_distance(query_vector)
            similarity_function = (1 - distance_function).label(
                "similarity"
            )  # Calculate similarity

            stmt = (
                select(DocumentChunk, similarity_function)
                .where(DocumentChunk.embedding.is_not(None))  # Ensure embedding exists
                .order_by(distance_function.asc())  # Order by distance (closest first)
                .limit(limit)
                # Eager load the related document to avoid N+1 queries if accessing
                # doc details later
                .options(
                    selectinload(DocumentChunk.document).selectinload(Document.source)
                )
            )

            # Optional filtering
            if source_ids:
                # Join with Document table to filter by source_id
                stmt = stmt.join(DocumentChunk.document).where(
                    Document.source_id.in_(source_ids)
                )

            if min_similarity is not None:
                # Filter by similarity. distance = 1 - similarity
                # So, distance <= 1 - min_similarity
                stmt = stmt.where(distance_function <= (1.0 - min_similarity))

            logger.debug(
                f"Executing similarity search with limit={limit}, "
                f"min_similarity={min_similarity}, sources={source_ids}"
            )
            results = await session.execute(stmt)
            similar_chunks = (
                results.all()
            )  # Gets list of Rows, each containing (DocumentChunk, similarity)

            # Check if results is empty or None before logging
            if similar_chunks:
                logger.debug(f"Found {len(similar_chunks)} similar chunks.")
            else:
                logger.debug("Found 0 similar chunks matching criteria.")

            # Return as list of tuples (DocumentChunk_object, similarity_score)
            return [
                (chunk, similarity) for chunk, similarity in similar_chunks
            ]  # Corrected unpacking

    async def delete_documents_by_source(self, source_id: int) -> int:
        """
        Deletes all documents (and their chunks due to cascade) for a given source ID.
        """
        async with self.session_maker() as session:
            try:
                stmt = delete(Document).where(Document.source_id == source_id)
                result = await session.execute(stmt)
                await session.commit()
                deleted_count = result.rowcount
                logger.info(
                    f"Deleted {deleted_count} documents (and their chunks) "
                    f"for source_id {source_id}."
                )
                return deleted_count
            except Exception as e:
                await session.rollback()
                logger.error(
                    f"Error deleting documents for source_id {source_id}: {e}",
                    exc_info=True,
                )
                raise

    async def update_data_source_processed_time(self, source_id: int) -> None:
        """Updates the last_processed_at timestamp for a data source."""
        async with self.session_maker() as session:
            try:
                stmt = (
                    update(DataSource)
                    .where(DataSource.source_id == source_id)
                    .values(last_processed_at=func.now())
                    # synchronize_session=False is recommended for async updates
                    .execution_options(synchronize_session=False)
                )
                await session.execute(stmt)
                await session.commit()
                logger.debug(f"Updated last_processed_at for source_id {source_id}.")
            except Exception as e:
                await session.rollback()
                logger.error(
                    f"Error updating last_processed_at for source_id {source_id}: {e}",
                    exc_info=True,
                )
                raise
