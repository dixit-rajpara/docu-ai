import ollama
from typing import List, Optional

from .interface import AbstractEmbeddingClient
from .errors import EmbeddingConfigurationError, EmbeddingGenerationError
from config.settings import settings
from config.logger import get_logger

logger = get_logger(__name__)


class OllamaEmbeddingClient(AbstractEmbeddingClient):
    """Embedding client implementation using a running Ollama server."""

    def __init__(self):
        self.provider = settings.embedding.provider
        self.host = settings.embedding.ollama_host
        self.model_name = settings.embedding.ollama_model
        self.dimension = settings.embedding.dimension
        # Batch size isn't directly used by ollama.embeddings
        # which processes one prompt

        if not self.host:
            logger.error("Ollama host URL is not configured (EMBEDDING_OLLAMA_HOST).")
            raise EmbeddingConfigurationError("Ollama host URL not configured.")
        if not self.model_name:
            logger.error(
                "Ollama model name is not configured (EMBEDDING_OLLAMA_MODEL)."
            )
            raise EmbeddingConfigurationError("Ollama model name not configured.")

        try:
            # Initialize async client targeting the configured host
            self.client = ollama.AsyncClient(host=self.host)
            logger.info(
                "Initialized OllamaEmbeddingClient targeting host: "
                f"{self.host} with model: {self.model_name}"
            )
            # Note: Connection isn't verified until the first API call typically
        except Exception as e:
            logger.exception("Failed to initialize Ollama client.")
            raise EmbeddingConfigurationError(
                f"Failed to initialize Ollama client: {e}"
            ) from e

    def get_embedding_dimension(self) -> int:
        """Returns the configured embedding dimension."""
        # Ollama model dimensions need to be known beforehand and configured.
        return self.dimension

    def get_model_name(self) -> str:
        """Returns the configured Ollama model name."""
        return self.model_name

    async def generate_embeddings(
        self, texts: List[str]
    ) -> Optional[List[List[float]]]:
        """Generates embeddings by calling the Ollama API for each text chunk."""
        if not texts:
            return []

        logger.info(
            f"Requesting Ollama embeddings for {len(texts)} text chunks "
            f"from {self.host} using model {self.model_name}..."
        )
        all_embeddings: List[List[float]] = []

        try:
            # Ollama library processes texts individually for embeddings
            for i, text in enumerate(texts):
                if not text.strip():  # Handle empty strings, Ollama might error
                    logger.warning(f"Skipping empty text chunk at index {i}.")
                    # Decide how to handle: None, default vector,
                    # or skip (here skipping)
                    # Could potentially add a zero vector of correct
                    # dimension if needed:
                    # all_embeddings.append([0.0] * self.dimension)
                    continue

                logger.debug(f"Requesting embedding for chunk {i + 1}/{len(texts)}")
                response = await self.client.embeddings(
                    model=self.model_name, prompt=text
                )
                embedding = response.get("embedding")

                if embedding:
                    # Optional: Verify dimension
                    if len(embedding) != self.dimension:
                        logger.warning(
                            "Mismatch between configured dimension "
                            f"({self.dimension}) and "
                            f"received Ollama embedding dimension ({len(embedding)}) "
                            f"for model '{self.model_name}'. "
                            "Check configuration/Ollama model."
                        )
                        # Handle mismatch: error out, skip, or use received?
                        # Using received for now.
                        # raise EmbeddingGenerationError(
                        # "Ollama embedding dimension mismatch.")

                    all_embeddings.append(embedding)
                else:
                    logger.error(
                        f"Ollama did not return an embedding for chunk {i}. "
                        f"Response: {response}"
                    )
                    # Handle missing embedding: skip or add None? Adding None for now.
                    all_embeddings.append(None)  # Or raise error?

            # Check if any embeddings were successfully generated
            successful_embeddings = [e for e in all_embeddings if e is not None]
            if not successful_embeddings:
                logger.error("Failed to generate any embeddings from Ollama.")
                return None  # Indicate complete failure

            logger.info(
                f"Successfully generated {len(successful_embeddings)}/{len(texts)} "
                "embeddings via Ollama."
            )
            # Replace None values if necessary or handle upstream. For now, returning
            # list with potential Nones.
            # A design choice: should this return partial results or fail entirely if
            # some chunks fail?
            # Returning partial results for now.
            return all_embeddings

        except ollama.ResponseError as e:
            logger.error(
                f"Ollama API error: {e.status_code} - {e.error}. Check Ollama server "
                f"and model '{self.model_name}'.",
                exc_info=True,
            )
            raise EmbeddingGenerationError(
                f"Ollama API Error: {e.error} (Status: {e.status_code})"
            ) from e
        except Exception as e:
            # Catch potential connection errors, timeouts etc.
            logger.exception(
                "An unexpected error occurred during Ollama embedding generation."
            )
            raise EmbeddingGenerationError(f"Ollama communication failed: {e}") from e

        return None  # Should not be reached
