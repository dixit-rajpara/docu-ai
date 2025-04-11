from typing import List, Optional, Dict, Any

from litellm import acompletion
from litellm.exceptions import (
    APIError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
    AuthenticationError,
    InvalidRequestError,
    BadRequestError,
    ContentPolicyViolationError,
)

from .interface import AbstractCompletionClient
from .errors import CompletionConfigurationError, CompletionGenerationError

from config.settings import settings
from config.logger import get_logger

logger = get_logger(__name__)

# Configure logging for LiteLLM (optional, but helpful for debugging)
# litellm.set_verbose = True


class LiteLLMCompletionClient(AbstractCompletionClient):
    """Completion client implementation using the LiteLLM library."""

    def __init__(self):
        comp_config = settings.completion
        self.model_name = comp_config.model
        self.default_temperature = comp_config.temperature
        self.default_max_tokens = comp_config.max_tokens
        self.api_base = str(comp_config.api_base) if comp_config.api_base else None
        self.timeout = comp_config.timeout

        if not self.model_name:
            logger.error("Completion model name is not configured (COMPLETION_MODEL).")
            raise CompletionConfigurationError("Completion model name not configured.")

        logger.info(
            f"Initialized LiteLLMCompletionClient with model: {self.model_name}, "
            f"default temp: {self.default_temperature}, default max_tokens: {self.default_max_tokens}"
        )
        # LiteLLM uses environment variables for API keys - log a reminder
        logger.info(
            "LiteLLM will use API keys from environment variables (e.g., OPENAI_API_KEY)."
        )
        if self.api_base:
            self.api_base = self.api_base.rstrip("/")
            logger.info(f"Using custom API base: {self.api_base}")

    def get_model_name(self) -> str:
        """Returns the configured LiteLLM model name."""
        return self.model_name

    async def generate_completion(
        self,
        prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Generates completion using LiteLLM."""

        if not prompt and not messages:
            logger.error("Either 'prompt' or 'messages' must be provided.")
            raise ValueError("Either 'prompt' or 'messages' must be provided.")
        if prompt and messages:
            logger.warning("Both 'prompt' and 'messages' provided. Using 'messages'.")
            # Or raise ValueError("Provide only one of 'prompt' or 'messages'.")

        # Prepare messages for LiteLLM
        if messages:
            llm_messages = messages
        else:  # Convert simple prompt to message format
            llm_messages = [{"role": "user", "content": prompt}]

        # Prepare parameters, using defaults from settings if not overridden
        llm_temperature = (
            temperature if temperature is not None else self.default_temperature
        )
        llm_max_tokens = (
            max_tokens if max_tokens is not None else self.default_max_tokens
        )

        call_kwargs = {
            "model": self.model_name,
            "messages": llm_messages,
            "temperature": llm_temperature,
            "max_tokens": llm_max_tokens,
            "api_base": self.api_base,  # Pass optional API base
            "timeout": self.timeout,  # Pass optional timeout
            **kwargs,  # Pass through any extra provider-specific args
        }
        if stop:
            call_kwargs["stop"] = stop

        # Filter out None values to avoid sending them to LiteLLM
        call_kwargs = {k: v for k, v in call_kwargs.items() if v is not None}

        try:
            logger.debug(
                f"Calling LiteLLM acompletion with parameters: { {k: v for k, v in call_kwargs.items() if k != 'messages'} }"
            )  # Don't log full messages unless needed
            response = await acompletion(**call_kwargs)

            # Extract the content
            if (
                response
                and response.choices
                and response.choices[0].message
                and response.choices[0].message.content
            ):
                completion_text = response.choices[0].message.content.strip()
                # Log usage details if available (depends on provider)
                try:
                    usage = response.usage
                    if usage:
                        logger.info(
                            f"LiteLLM completion successful. Usage: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
                        )
                    else:
                        logger.info(
                            "LiteLLM completion successful. Usage info not available."
                        )
                except Exception:
                    logger.info(
                        "LiteLLM completion successful. Could not parse usage info."
                    )

                return completion_text
            else:
                logger.error(
                    f"LiteLLM response structure unexpected or content missing. Response: {response}"
                )
                raise CompletionGenerationError("LiteLLM response invalid or empty.")

        # Specific LiteLLM/Provider exceptions
        except AuthenticationError as e:
            logger.error(
                f"LiteLLM Authentication Error for model {self.model_name}: {e}",
                exc_info=True,
            )
            raise CompletionConfigurationError(
                f"Authentication failed for {self.model_name}. Check API Key."
            ) from e
        except InvalidRequestError as e:
            logger.error(
                f"LiteLLM Invalid Request Error for model {self.model_name}: {e}",
                exc_info=True,
            )
            raise CompletionGenerationError(
                f"Invalid request for {self.model_name}: {e}"
            ) from e
        except BadRequestError as e:  # Sometimes used instead of InvalidRequestError
            logger.error(
                f"LiteLLM Bad Request Error for model {self.model_name}: {e}",
                exc_info=True,
            )
            raise CompletionGenerationError(
                f"Bad request for {self.model_name}: {e}"
            ) from e
        except ContentPolicyViolationError as e:
            logger.error(
                f"LiteLLM Content Policy Violation for model {self.model_name}: {e}",
                exc_info=True,
            )
            raise CompletionGenerationError(
                f"Content policy violation by {self.model_name}: {e}"
            ) from e
        except RateLimitError as e:
            logger.error(
                f"LiteLLM Rate Limit Error for model {self.model_name}: {e}",
                exc_info=True,
            )
            raise CompletionGenerationError(
                f"Rate limit hit for {self.model_name}. Check limits or retry later."
            ) from e
        except ServiceUnavailableError as e:
            logger.error(
                f"LiteLLM Service Unavailable Error for model {self.model_name}: {e}",
                exc_info=True,
            )
            raise CompletionGenerationError(
                f"Service unavailable for {self.model_name}. Retry later."
            ) from e
        except Timeout as e:
            logger.error(
                f"LiteLLM Timeout Error for model {self.model_name}: {e}", exc_info=True
            )
            raise CompletionGenerationError(
                f"Request timed out for {self.model_name}."
            ) from e
        except APIError as e:  # Catch other LiteLLM API errors
            logger.error(
                f"LiteLLM API Error for model {self.model_name}: {e}", exc_info=True
            )
            raise CompletionGenerationError(
                f"API error during completion with {self.model_name}: {e}"
            ) from e
        # Catch potential configuration errors missed earlier or generic exceptions
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred during LiteLLM completion with model {self.model_name}."
            )
            # Check if it might be config related
            if isinstance(e, (ValueError, TypeError)):
                raise CompletionConfigurationError(
                    f"Unexpected configuration issue: {e}"
                ) from e
            else:
                raise CompletionGenerationError(
                    f"Unexpected error during completion: {e}"
                ) from e

        return (
            None  # Should only be reached if generation somehow fails without exception
        )
