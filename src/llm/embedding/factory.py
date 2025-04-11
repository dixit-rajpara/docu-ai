from .interface import AbstractEmbeddingClient
from .errors import EmbeddingConfigurationError

from config.settings import settings
from config.logger import get_logger

logger = get_logger(__name__)


def create_embedding_client() -> AbstractEmbeddingClient:
    """
    Factory function to create the appropriate embedding client based on settings.
    """
    provider = settings.embedding.provider.lower()
    logger.info(f"Creating embedding client for provider: {provider}")

    if provider == "openai":
        from .openai_client import OpenAIEmbeddingClient  # Lazy import

        return OpenAIEmbeddingClient()
    elif provider == "huggingface":
        from .huggingface_client import HuggingFaceEmbeddingClient  # Lazy import

        return HuggingFaceEmbeddingClient()
    elif provider == "ollama":
        from .ollama_client import OllamaEmbeddingClient  # Lazy import

        return OllamaEmbeddingClient()
    else:
        logger.error(f"Unsupported embedding provider configured: {provider}")
        raise EmbeddingConfigurationError(f"Unsupported embedding provider: {provider}")
