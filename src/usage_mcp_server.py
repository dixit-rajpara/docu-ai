import asyncio
import random
from typing import cast

# Database Imports
from db import (
    PostgresDBRepository,
    AsyncSessionLocal,
    async_engine,
    init_db,
    AbstractDBRepository,
    DocumentChunk,  # Import DocumentChunk for type hints if needed elsewhere
)

# Embedding Imports
from llm.embedding import (
    create_embedding_client,
    AbstractEmbeddingClient,
    EmbeddingError,
)

# MCP Tool Imports
from mcp_server.tools import (
    vector_search,
    get_document_by_id,
    get_documents_by_url,
    get_document_chunks,
    list_data_sources,
)

# Configuration and Logging
from config.settings import settings
from config.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def setup_sample_data(repository: AbstractDBRepository):
    """Adds some sample data for testing the tools."""
    logger.info("Setting up sample data...")
    try:
        # --- Create Source ---
        source = await repository.get_or_create_data_source(
            name="Sample Framework Docs",
            base_url="https://example.com/docs",
            identifier="sample-v1",
        )
        logger.debug(f"Ensured data source exists: {source.name}")

        # --- Add Document ---
        doc_url = "https://example.com/docs/getting-started"
        existing_doc = await repository.get_document_by_url(source.source_id, doc_url)
        if not existing_doc:
            doc = await repository.add_document(
                source_id=source.source_id,
                url=doc_url,
                title="Getting Started Guide",
                markdown_content="""
# Getting Started

This is the introduction to the sample framework.

## Installation

Run `pip install sample-framework`.

## Basic Usage

```python
import sample_framework

client = sample_framework.Client()
result = client.process("some data")
print(result)
```
""",
                summary="An introductory guide to setting up and using the framework.",
                content_hash="dummy_hash_gs_" + str(random.randint(1000, 9999)),
            )
            logger.debug(f"Added document: {doc.title}")
        else:
            doc = existing_doc
            logger.debug(f"Document already exists: {doc.title}")

        # --- Add Chunks (if document exists and has ID) ---
        if doc and doc.document_id:
            # Check if chunks already exist for this doc to avoid duplicates
            existing_chunks = await repository.get_chunks_by_document_id(
                doc.document_id, limit=1
            )
            if not existing_chunks:
                embed_dim = settings.core.embedding_dimension
                # Provider is now determined by settings
                embedding_client = create_embedding_client()
                logger.info(
                    f"Using embedding provider from settings for setup: {settings.embedding.provider}"
                )
                chunks_data = [
                    "This is the introduction to the sample framework.",
                    "Run `pip install sample-framework`.",
                    "Basic Usage: import sample_framework...",
                ]
                embeddings = await embedding_client.generate_embeddings(chunks_data)

                chunks_to_add = [
                    {
                        "document_id": doc.document_id,
                        "chunk_text": text,
                        "chunk_order": i,
                        "embedding": embeddings[i]
                        if embeddings and i < len(embeddings)
                        else [
                            random.random() for _ in range(embed_dim)
                        ],  # Fallback if embedding fails
                        "embedding_model": embedding_client.get_model_name(),
                        "token_count": len(text.split()),  # Simple token count
                    }
                    for i, text in enumerate(chunks_data)
                ]
                await repository.add_document_chunks(chunks_to_add)
                logger.debug(
                    f"Added {len(chunks_to_add)} chunks for doc ID {doc.document_id}."
                )
            else:
                logger.debug(f"Chunks already exist for doc ID {doc.document_id}.")

            return doc.document_id  # Return an existing document ID for later use
        else:
            logger.warning("Could not obtain a valid document ID for adding chunks.")
            return None

    except EmbeddingError as e:
        logger.error(f"Failed to generate embeddings during setup: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error setting up sample data: {e}", exc_info=True)
        return None


async def main():
    logger.info("Initializing database and dependencies for MCP tool usage demo...")
    await init_db()
    repository = PostgresDBRepository(
        session_maker=AsyncSessionLocal, engine=async_engine
    )
    # Embedding client is created based on settings in .env
    embedding_client = create_embedding_client()
    logger.info(
        f"Using embedding provider from settings for main execution: {settings.embedding.provider}"
    )
    # Cast for type hinting compatibility with tool functions
    db_repo: AbstractDBRepository = repository
    embed_client: AbstractEmbeddingClient = embedding_client

    sample_doc_id = None
    try:
        # --- Setup ---
        sample_doc_id = await setup_sample_data(db_repo)
        if sample_doc_id is None:
            logger.warning(
                "Proceeding without a guaranteed sample_doc_id due to setup issues."
            )
            # Try to find *any* existing doc id as a fallback
            sources = await db_repo.get_data_sources(limit=1)
            if sources:
                docs = await db_repo.get_documents_by_source(
                    sources[0].source_id, limit=1
                )
                if docs:
                    sample_doc_id = docs[0].document_id
                    logger.info(f"Using fallback document ID: {sample_doc_id}")

        # --- Call list_data_sources ---
        logger.info("\n--- Testing list_data_sources ---")
        result_list = await list_data_sources(db_repo=db_repo)
        print(f"Result isError: {result_list.isError}")
        print(
            f"Content: {result_list.content[0].text if result_list.content else 'No Content'}"
        )

        # --- Call vector_search ---
        logger.info("\n--- Testing vector_search ---")
        query = "pydantic-ai documentation features AI agent structure"
        # query = "How do I install the framework?"
        result_search = await vector_search(
            mcp=None,  # MCP instance not needed for direct call
            db_repo=db_repo,
            embedding_client=embed_client,
            query_text=query,
            limit=3,
            min_similarity=0.5,
        )
        print(f"Result isError: {result_search.isError}")
        print(
            f"Content: {result_search.content[0].text if result_search.content else 'No Content'}"
        )

        # --- Call get_document_by_id ---
        logger.info("\n--- Testing get_document_by_id ---")
        if sample_doc_id:
            result_get_id = await get_document_by_id(
                db_repo=db_repo, document_id=sample_doc_id
            )
            print(f"Result isError: {result_get_id.isError}")
            print(
                f"Content: {result_get_id.content[0].text if result_get_id.content else 'No Content'}"
            )
        else:
            logger.warning(
                "Skipping get_document_by_id test: No sample document ID available."
            )

        # --- Call get_documents_by_url ---
        logger.info("\n--- Testing get_documents_by_url ---")
        sample_url = (
            "https://example.com/docs/getting-started"  # Use the one from setup
        )
        result_get_url = await get_documents_by_url(db_repo=db_repo, url=sample_url)
        print(f"Result isError: {result_get_url.isError}")
        print(
            f"Content: {result_get_url.content[0].text if result_get_url.content else 'No Content'}"
        )

        # --- Call get_document_chunks ---
        logger.info("\n--- Testing get_document_chunks ---")
        if sample_doc_id:
            result_get_chunks = await get_document_chunks(
                db_repo=db_repo, document_id=sample_doc_id, limit=10
            )
            print(f"Result isError: {result_get_chunks.isError}")
            print(
                f"Content: {result_get_chunks.content[0].text if result_get_chunks.content else 'No Content'}"
            )
        else:
            logger.warning(
                "Skipping get_document_chunks test: No sample document ID available."
            )

    except Exception as e:
        logger.error(
            f"An error occurred during MCP tool usage demo: {e}", exc_info=True
        )
    finally:
        logger.info("Shutting down database connection.")
        await repository.shutdown()  # Use the original repository instance


if __name__ == "__main__":
    logger.info("Running MCP Server Tool Usage Demo...")
    asyncio.run(main())
    logger.info("Demo finished.")
