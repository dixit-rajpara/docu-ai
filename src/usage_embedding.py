import asyncio
from typing import List

# Import necessary components
from llm.embedding import (
    create_embedding_client,
    EmbeddingError,
    calculate_token_count,
)

from config.logger import get_logger, setup_logging

logger = get_logger(__name__)


async def process_and_store_embeddings(chunks_data: List[dict]):
    texts_to_embed = [chunk["text"] for chunk in chunks_data]

    if not texts_to_embed:
        logger.info("No text chunks found to embed.")
        return

    try:
        # 1. Create the embedding client using the factory
        embedding_client = create_embedding_client()
        model_name = embedding_client.get_model_name()
        expected_dimension = (
            embedding_client.get_embedding_dimension()
        )  # For validation if needed
        logger.info(f"Using model: {model_name} with dimension: {expected_dimension}")

        # 2. Generate embeddings
        embeddings = await embedding_client.generate_embeddings(texts_to_embed)

        if embeddings is None or len(embeddings) != len(texts_to_embed):
            logger.error(
                "Failed to generate embeddings or received incorrect number of embeddings."
            )
            # Handle error appropriately - maybe skip storing these chunks or retry
            return

        # 3. Prepare data for database insertion
        chunks_for_db = []
        for i, chunk_data in enumerate(chunks_data):
            if (
                embeddings[i] is not None
            ):  # Check if embedding generation succeeded for this chunk
                chunks_for_db.append(
                    {
                        "chunk_text": chunk_data["text"],
                        "chunk_order": chunk_data["order"],
                        "embedding": embeddings[i],  # Add the generated embedding
                        "embedding_model": model_name,  # Store which model was used
                        "token_count": calculate_token_count(
                            chunk_data["text"]
                        ),  # Optional
                    }
                )
            else:
                logger.warning(f"Skipping chunk {i} due to missing embedding.")
    except EmbeddingError as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        # Handle embedding specific errors (config, generation)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during embedding: {e}", exc_info=True
        )

    logger.info(f"Successfully processed and stored {len(chunks_for_db)} embeddings.")
    logger.info(f"Chunks for database: {chunks_for_db[0]}")


if __name__ == "__main__":
    setup_logging()
    # Assuming you have processed scraped HTML into text chunks
    # List[dict] where each dict might contain {'text': '...', 'order': ...}
    processed_chunks_data = [
        {"text": "This is the first piece of documentation content.", "order": 0},
        {"text": "Here is some more information about feature X.", "order": 1},
        {"text": "Remember to install package Y using pip.", "order": 2},
        # ... more chunks
    ]
    asyncio.run(process_and_store_embeddings(processed_chunks_data))
