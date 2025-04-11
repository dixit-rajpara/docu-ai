from .interface import AbstractCompletionClient
from .errors import CompletionConfigurationError

# Import the specific implementation
from .litellm_client import LiteLLMCompletionClient

from config.logger import get_logger

logger = get_logger(__name__)


# Currently, we only have the LiteLLM implementation,
# but the factory pattern allows adding others later.
def create_completion_client() -> AbstractCompletionClient:
    """
    Factory function to create the completion client.
    Currently always returns the LiteLLM client.
    """
    logger.info("Creating LiteLLM completion client.")
    try:
        # Can add logic here later to choose client based on config if needed
        return LiteLLMCompletionClient()
    except CompletionConfigurationError:
        # Log the config error and re-raise
        logger.exception("Configuration error during completion client creation.")
        raise
    except Exception as e:
        # Catch unexpected errors during instantiation
        logger.exception("Unexpected error creating completion client.")
        raise CompletionConfigurationError(
            f"Failed to create completion client: {e}"
        ) from e
