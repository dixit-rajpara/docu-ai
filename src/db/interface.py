import abc
import datetime
from typing import List, Optional, Tuple

# Re-import models for type hinting
from .models import DataSource, Document, DocumentChunk


class AbstractDBRepository(abc.ABC):
    """Abstract interface for database operations."""

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Initialize database connection and optionally create tables."""
        raise NotImplementedError

    @abc.abstractmethod
    async def shutdown(self) -> None:
        """Clean up database connections."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_or_create_data_source(
        self,
        name: str,
        base_url: Optional[str] = None,
        identifier: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DataSource:
        """Gets an existing data source by name or creates a new one."""
        raise NotImplementedError

    @abc.abstractmethod
    async def add_document(
        self,
        source_id: int,
        url: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        markdown_content: Optional[str] = None,
        last_modified: Optional[datetime.datetime] = None,  # Ensure datetime type hint
        content_hash: Optional[str] = None,
        metadata_: Optional[dict] = None,
    ) -> Document:
        """Adds a new document linked to a data source."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_document_by_url(self, source_id: int, url: str) -> Optional[Document]:
        """Retrieves a document by its source ID and URL."""
        raise NotImplementedError

    @abc.abstractmethod
    async def add_document_chunks(self, chunks_data: List[dict]) -> List[DocumentChunk]:
        """
        Adds multiple document chunks in bulk.
        Each dict in chunks_data should match DocumentChunk fields
        (e.g., {'document_id': id, 'chunk_text': text, 'chunk_order': i, ...}).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def find_similar_chunks(
        self,
        query_vector: List[float],
        limit: int = 5,
        min_similarity: Optional[
            float
        ] = None,  # Optional threshold (0.0 to 1.0 for cosine)
        source_ids: Optional[List[int]] = None,  # Optional filter by source
    ) -> List[Tuple[DocumentChunk, float]]:
        """
        Finds document chunks with embeddings similar to the query_vector.
        Returns a list of tuples: (DocumentChunk, similarity_score).
        Similarity is cosine similarity (higher is better).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_documents_by_source(self, source_id: int) -> int:
        """Deletes all documents (and their chunks due to cascade) for a
        given source ID. Returns count deleted."""
        raise NotImplementedError

    @abc.abstractmethod
    async def update_data_source_processed_time(self, source_id: int) -> None:
        """Updates the last_processed_at timestamp for a data source."""
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_chunks_by_document(self, document_id: int) -> int:
        """Deletes all chunks associated with a given document ID.
        Returns count deleted.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def update_document_metadata(
        self, document_id: int, title: Optional[str], summary: Optional[str]
    ) -> Optional[Document]:
        """Updates the title and summary for a given document ID.
        Returns the updated document or None.
        """
        raise NotImplementedError
