class EmbeddingError(Exception):
    """Base class for embedding related errors."""

    pass


class EmbeddingConfigurationError(EmbeddingError):
    """Error related to embedding client configuration."""

    pass


class EmbeddingGenerationError(EmbeddingError):
    """Error during the embedding generation process."""

    pass
