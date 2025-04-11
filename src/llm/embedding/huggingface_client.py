from sentence_transformers import SentenceTransformer
from typing import List, Optional
import numpy as np

from .interface import AbstractEmbeddingClient
from .errors import EmbeddingConfigurationError, EmbeddingGenerationError
from config.settings import settings
from config.logger import get_logger


logger = get_logger(__name__)


class HuggingFaceEmbeddingClient(AbstractEmbeddingClient):
    """Embedding client implementation using Hugging Face sentence-transformers."""

    def __init__(self):
        self.provider = settings.embedding.provider
        self.model_name = settings.embedding.huggingface_model
        self.device = settings.embedding.huggingface_device
        self.dimension = settings.embedding.dimension
        self.batch_size = settings.embedding.batch_size

        if not self.model_name:
            logger.error(
                "Hugging Face model name is not configured "
                "(EMBEDDING_HUGGINGFACE_MODEL)."
            )
            raise EmbeddingConfigurationError("Hugging Face model name not configured.")

        try:
            logger.info(
                f"Loading Hugging Face model: {self.model_name} "
                f"onto device: {self.device}"
            )
            # If device='auto', let sentence-transformers choose
            device_to_use = None if self.device == "auto" else self.device
            self.client = SentenceTransformer(
                model_name_or_path=self.model_name, device=device_to_use
            )
            logger.info(f"Successfully loaded Hugging Face model: {self.model_name}")

            # Optional: Verify configured dimension matches model dimension
            actual_dimension = self.client.get_sentence_embedding_dimension()
            if actual_dimension != self.dimension:
                logger.warning(
                    f"Configured dimension ({self.dimension}) does not match model "
                    f"'{self.model_name}' actual dimension ({actual_dimension}). "
                    f"Using actual dimension: {actual_dimension}. Update your "
                    f"config/DB schema if needed."
                )
                # Optionally override self.dimension or raise an error
                self.dimension = (
                    actual_dimension  # Trust the model over config if they mismatch
                )

        except Exception as e:
            logger.exception(f"Failed to load Hugging Face model: {self.model_name}")
            raise EmbeddingConfigurationError(
                f"Failed to load Hugging Face model '{self.model_name}': {e}"
            ) from e

    def get_embedding_dimension(self) -> int:
        """Returns the embedding dimension of the loaded model."""
        return self.dimension  # Returns the potentially corrected dimension

    def get_model_name(self) -> str:
        """Returns the configured Hugging Face model name."""
        return self.model_name

    async def generate_embeddings(
        self, texts: List[str]
    ) -> Optional[List[List[float]]]:
        """
        Generates embeddings using the loaded SentenceTransformer model.
        Note: SentenceTransformer.encode is synchronous, but we run it within an
        async method.
        """
        if not texts:
            return []

        logger.info(
            f"Generating Hugging Face embeddings for {len(texts)} text chunks "
            f"using model {self.model_name}..."
        )
        try:
            # SentenceTransformer encode is synchronous, but okay to call
            # from async function
            embeddings_np: np.ndarray = self.client.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=False,  # Disable progress bar for non-interactive use
            )
            # Convert numpy array to list of lists
            embeddings_list = embeddings_np.tolist()
            logger.info(f"Successfully generated {len(embeddings_list)} embeddings.")
            return embeddings_list
        except Exception as e:
            logger.exception(
                "An unexpected error occurred during Hugging Face embedding generation."
            )
            # Raise specific error if possible, otherwise generic
            raise EmbeddingGenerationError(f"HuggingFace embedding failed: {e}") from e

        return None  # Should not be reached
