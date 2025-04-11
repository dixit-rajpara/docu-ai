import asyncio
import random

from db import PostgresDBRepository, AsyncSessionLocal, async_engine, init_db

from config.settings import settings
from config.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def main():
    await init_db()
    repository = PostgresDBRepository(
        session_maker=AsyncSessionLocal, engine=async_engine
    )

    try:
        source = await repository.get_or_create_data_source(
            name="Python 3.12 Docs",
            base_url="https://docs.python.org/3.12/",
            identifier="3.12",
        )
        print(f"Data source: {source}")
        # ... add document logic ...
        existing_doc = await repository.get_document_by_url(
            source.source_id, "https://docs.python.org/3.12/library/asyncio.html"
        )
        if not existing_doc:
            doc = await repository.add_document(
                source_id=source.source_id,
                url="https://docs.python.org/3.12/library/asyncio.html",
                title="asyncio — Asynchronous I/O",
                content_hash="dummy_hash_123",  # Replace with actual hash
            )
            print(f"Added document: {doc}")
        else:
            doc = existing_doc
            print(f"Document already exists: {doc}")

        # --- Use settings for embedding dimension ---
        if doc and doc.document_id:  # Check if doc exists and has an ID
            embed_dim = settings.core.embedding_dimension  # Get dimension from settings
            dummy_embedding = [random.random() for _ in range(embed_dim)]
            chunks_to_add = [
                {
                    "document_id": doc.document_id,
                    "chunk_text": "This is the first chunk about asyncio basics.",
                    "chunk_order": 0,
                    "embedding": dummy_embedding,
                    "embedding_model": "text-embedding-ada-002",
                    "token_count": 7,
                },
                {
                    "document_id": doc.document_id,
                    "chunk_text": "This second chunk discusses event loops.",
                    "chunk_order": 1,
                    "embedding": [
                        random.random() for _ in range(embed_dim)
                    ],  # Use correct dim
                    "embedding_model": "text-embedding-ada-002",
                    "token_count": 6,
                },
            ]
            await repository.add_document_chunks(chunks_to_add)
            print(f"Attempted to add {len(chunks_to_add)} chunks.")

            # --- Use settings for embedding dimension in search ---
            print("\nSearching for chunks similar to the first chunk's embedding...")
            query_vector = dummy_embedding
            similar_results = await repository.find_similar_chunks(
                query_vector=query_vector,
                limit=5,
                min_similarity=0.7,
            )
            # ... (rest of the printing logic remains the same) ...
            if similar_results:
                print("Found similar chunks:")
                for chunk, similarity in similar_results:
                    doc_url = chunk.document.url if chunk.document else "N/A"
                    print(
                        f"  - Chunk ID: {chunk.chunk_id}, Order: {chunk.chunk_order}, "
                        f"Similarity: {similarity:.4f}, Doc URL: {doc_url}"
                    )
            else:
                print("No similar chunks found matching the criteria.")

    except Exception as e:
        logger.error(
            f"An error occurred during database operations: {e}", exc_info=True
        )
    finally:
        await repository.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
