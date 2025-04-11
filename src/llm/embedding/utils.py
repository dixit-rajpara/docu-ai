import tiktoken
from typing import Optional
from config.logger import get_logger

logger = get_logger(__name__)

# --- Cache the tokenizer encoding globally ---
# Getting the encoding can be slightly expensive, so cache it.
# 'cl100k_base' is the encoding used by GPT-3.5-turbo, GPT-4,
# text-embedding-3-small, text-embedding-3-large and text-embedding-ada-002.
# It's a good general-purpose choice for approximation.
try:
    _encoding = tiktoken.get_encoding("cl100k_base")
    TIKTOKEN_AVAILABLE = True
    logger.info("Initialized tiktoken encoding 'cl100k_base' for token counting.")
except Exception as e:
    _encoding = None
    TIKTOKEN_AVAILABLE = False
    logger.warning(
        f"Could not initialize tiktoken, token counting will be unavailable: {e}"
    )

# --- Token Counting Function ---


def calculate_token_count(text: str) -> Optional[int]:
    """
    Calculates the number of tokens in a given text string using tiktoken.

    Uses the 'cl100k_base' encoding as a general approximation suitable
    for many modern LLMs (GPT-4, GPT-3.5, OpenAI embeddings).

    Args:
        text: The input string.

    Returns:
        The estimated number of tokens, or None if tiktoken is unavailable
        or the input is invalid. Returns 0 for empty string.
    """
    if not TIKTOKEN_AVAILABLE or _encoding is None:
        logger.debug("Tiktoken unavailable, cannot calculate token count.")
        return None  # Return None if tiktoken couldn't be loaded

    if not isinstance(text, str):
        logger.warning(
            f"Invalid input type for token counting: {type(text)}. Expected str."
        )
        return None  # Return None for non-string input

    if not text:
        return 0  # Empty string has 0 tokens

    try:
        tokens = _encoding.encode(
            text,
            # disallowed_special=() # Allow all special tokens if needed, default usually ok
            # allowed_special="all"
        )
        return len(tokens)
    except Exception as e:
        # Handle potential errors during encoding, though less common for basic text
        logger.error(
            f"Error calculating token count for text snippet '{text[:50]}...': {e}",
            exc_info=False,
        )  # Avoid logging potentially large text
        return None
