# Expose key components from submodules

# Embedding components (Adjust based on your actual embedding __init__.py)
from .embedding import (
    AbstractEmbeddingClient,
    create_embedding_client,
    EmbeddingError,
    calculate_token_count,
    # ... other embedding exports if needed
)

# Completion components
from .completion import (
    AbstractCompletionClient,
    create_completion_client,
    CompletionError,
    LiteLLMCompletionClient,  # Expose implementation if needed directly
    # ... other completion exports if needed
)

__all__ = [
    # Embedding
    "AbstractEmbeddingClient",
    "create_embedding_client",
    "EmbeddingError",
    # Completion
    "AbstractCompletionClient",
    "create_completion_client",
    "CompletionError",
    "LiteLLMCompletionClient",
    "calculate_token_count",
]
