import tiktoken
from typing import List, Optional

from openai import (
    AsyncOpenAI,
    OpenAIError,
    APIConnectionError,
    RateLimitError,
    AuthenticationError,
)

from .interface import AbstractEmbeddingClient
from .errors import EmbeddingConfigurationError, EmbeddingGenerationError
from config.settings import settings
from config.logger import get_logger

logger = get_logger(__name__)


class OpenAIEmbeddingClient(AbstractEmbeddingClient):
    """Embedding client implementation using the OpenAI API."""

    def __init__(self):
        self.provider = settings.embedding.provider
        self.model_name = settings.embedding.openai_model
        self.dimension = settings.embedding.dimension
        self.batch_size = settings.embedding.batch_size
        api_key = (
            settings.embedding.openai_api_key.get_secret_value()
            if settings.embedding.openai_api_key
            else None
        )

        if not api_key:
            logger.error(
                "OpenAI API key is not configured in settings "
                "(EMBEDDING_OPENAI_API_KEY)."
            )
            raise EmbeddingConfigurationError("OpenAI API key not configured.")

        try:
            self.client = AsyncOpenAI(api_key=api_key)
            logger.info(
                f"Initialized OpenAIEmbeddingClient with model: {self.model_name}"
            )
        except Exception as e:
            logger.exception("Failed to initialize OpenAI client.")
            raise EmbeddingConfigurationError(
                f"Failed to initialize OpenAI client: {e}"
            ) from e

    def get_embedding_dimension(self) -> int:
        """Returns the configured embedding dimension."""
        # Ideally, this could dynamically fetch from OpenAI, but models have
        # fixed dimensions.
        # Relying on the config value ensures consistency with DB schema.
        # Add a check during init or first call if possible in future.
        return self.dimension

    def get_model_name(self) -> str:
        """Returns the configured OpenAI model name."""
        return self.model_name

    async def generate_embeddings(
        self, texts: List[str]
    ) -> Optional[List[List[float]]]:
        """Generates embeddings for a list of texts using OpenAI API."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        try:
            logger.info(
                f"Requesting OpenAI embeddings for {len(texts)} text "
                f"chunks using model {self.model_name}..."
            )

            # Process in batches (OpenAI API might have limits, and it can be
            # more efficient)
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i : i + self.batch_size]
                logger.debug(
                    f"Processing batch {i // self.batch_size + 1} "
                    f"with {len(batch_texts)} items."
                )

                response = await self.client.embeddings.create(
                    input=batch_texts,
                    model=self.model_name,
                    # Optionally specify dimensions if supported by the model and
                    # needed dimensions=self.dimension # e.g., text-embedding-3 models
                    # allow this
                )

                batch_embeddings = [item.embedding for item in response.data]

                # Basic dimension check for the first item in the first batch
                if (
                    i == 0
                    and batch_embeddings
                    and len(batch_embeddings[0]) != self.dimension
                ):
                    logger.warning(
                        f"Mismatch between configured dimension ({self.dimension}) and "
                        f"received embedding dimension ({len(batch_embeddings[0])}) "
                        f"from model '{self.model_name}'. Check configuration."
                    )
                    # Decide whether to raise an error or just warn
                    # raise EmbeddingGenerationError("Embedding dimension mismatch.")

                all_embeddings.extend(batch_embeddings)
                logger.debug(f"Received {len(batch_embeddings)} embeddings for batch.")

            logger.info(f"Successfully generated {len(all_embeddings)} embeddings.")
            return all_embeddings

        except AuthenticationError as e:
            logger.error(
                f"OpenAI authentication error: {e}. Check your API key.", exc_info=True
            )
            raise EmbeddingGenerationError(f"OpenAI Authentication Error: {e}") from e
        except RateLimitError as e:
            logger.error(
                f"OpenAI rate limit exceeded: {e}. Check usage limits or "
                "implement backoff.",
                exc_info=True,
            )
            raise EmbeddingGenerationError(f"OpenAI Rate Limit Error: {e}") from e
        except APIConnectionError as e:
            logger.error(f"OpenAI API connection error: {e}.", exc_info=True)
            raise EmbeddingGenerationError(f"OpenAI Connection Error: {e}") from e
        except OpenAIError as e:
            logger.error(f"An OpenAI API error occurred: {e}", exc_info=True)
            raise EmbeddingGenerationError(f"OpenAI API Error: {e}") from e
        except Exception as e:
            logger.exception(
                "An unexpected error occurred during embedding generation."
            )
            raise EmbeddingGenerationError(f"Unexpected Error: {e}") from e

        return None  # Should not be reached if exceptions are raised properly
