import abc
from typing import List, Optional


class AbstractEmbeddingClient(abc.ABC):
    """Abstract interface for embedding generation clients."""

    @abc.abstractmethod
    async def generate_embeddings(
        self, texts: List[str]
    ) -> Optional[List[List[float]]]:
        """
        Generates embeddings for a list of text chunks.

        Args:
            texts: A list of strings to embed.

        Returns:
            A list of embeddings (each embedding is a list of floats),
            or None if an error occurred. The order matches the input texts.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Returns the expected output dimension of the embeddings.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_model_name(self) -> str:
        """
        Returns the identifier of the underlying embedding model.
        """
        raise NotImplementedError
