import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import (
    String,
    Text,
    ForeignKey,
    TIMESTAMP,
    Integer,
    Index,
    func,
    MetaData,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from pgvector.sqlalchemy import Vector

from config.settings import settings

# Recommended naming convention for constraints and indexes
# See: https://alembic.sqlalchemy.org/en/latest/naming.html
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=convention)


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for SQLAlchemy models with async support and metadata."""

    metadata = metadata
    type_annotation_map = {
        Dict[str, Any]: JSONB  # Use JSONB for dicts by default
    }


class DataSource(Base):
    __tablename__ = "data_sources"

    source_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    base_url: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    identifier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_processed_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    documents: Mapped[List["Document"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataSource(source_id={self.source_id}, name='{self.name}')>"


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.source_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # URL or other unique identifier within source
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_modified: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # e.g., SHA-256
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    source: Mapped["DataSource"] = relationship(back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    # Optional: Add a unique constraint if URL should be unique per source
    # __table_args__ = (UniqueConstraint('source_id', 'url',
    # name='uq_documents_source_url'),)

    # Add index for faster lookups by source_id and url
    __table_args__ = (
        Index("ix_documents_source_url", "source_id", "url"),
        {
            "comment": "Represents individual items (pages, files, records) retrieved from a data source, including cleaned content."
        },  # Add table comment if desired
    )

    def __repr__(self) -> str:
        # Truncate URL for representation
        url_repr = f"{self.url[:50]}..." if len(self.url or "") > 53 else self.url
        return (
            f"<Document(id={self.document_id}, source={self.source_id}, "
            f"title='{self.title}', url='{url_repr}')>"
        )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )  # Use standard Integer if BIGSERIAL not strictly needed via ORM
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Use the Vector type from sqlalchemy-pgvector
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(settings.core.embedding_dimension),  # Use setting here
        nullable=True,
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")

    # Optional: Add a unique constraint if chunk order must be unique per document
    # __table_args__ = (UniqueConstraint('document_id', 'chunk_order',
    # name='uq_document_chunks_doc_order'),)

    # Add index for the vector embedding using HNSW (recommended)
    # Adapt 'vector_cosine_ops' if using L2 or IP distance
    __table_args__ = (
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={
                "m": 16,
                "ef_construction": 64,
            },  # Optional HNSW parameters
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"comment": "Stores text chunks and their vector embeddings."},
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(chunk_id={self.chunk_id}, "
            f"document_id={self.document_id}, order={self.chunk_order})>"
        )
