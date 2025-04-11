import abc
from typing import List, Optional, Dict, Any

# Consider defining more structured input/output types if needed later
# e.g., using Pydantic models for messages and responses.


class AbstractCompletionClient(abc.ABC):
    """Abstract interface for LLM completion clients."""

    @abc.abstractmethod
    async def generate_completion(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,  # Allow passing provider-specific kwargs
    ) -> Optional[str]:
        """
        Generates a text completion based on a prompt or message history.

        Provide *either* 'prompt' (for simple user input) *or* 'messages'
        (for chat-based models with history/roles).

        Args:
            prompt: A simple user prompt string.
            messages: A list of message dictionaries (e.g., [{"role": "user", "content": "..."}]).
            temperature: Overrides the default temperature.
            max_tokens: Overrides the default max_tokens.
            stop: Optional list of sequences to stop generation at.
            **kwargs: Additional keyword arguments passed directly to the underlying provider API.

        Returns:
            The generated completion text as a string, or None if generation failed.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_model_name(self) -> str:
        """
        Returns the identifier of the underlying completion model being used.
        """
        raise NotImplementedError

    # Optional: Add methods for streaming, token counting for completion, etc. later if needed
    # def calculate_completion_tokens(self, text: str) -> Optional[int]: ...
    # async def stream_completion(self, ...) -> AsyncIterator[str]: ...
