import re
import json
from typing import Dict, Optional

from config.logger import get_logger

# Assume llm interface/factory is correctly set up in src/llm/completion
from llm.completion import AbstractCompletionClient, CompletionError

logger = get_logger(__name__)

# --- Prompt Templates (Adjust as needed) ---

DOCUMENT_METADATA_PROMPT_TEMPLATE = """
Analyze the following document content (in Markdown format) and extract the primary title and a concise one-sentence summary.
Provide the output ONLY in JSON format with keys "title" and "summary".
If you cannot determine a title or summary, use null for that value.

CONTENT:
{content_snippet}

JSON OUTPUT:
"""

CHUNK_METADATA_PROMPT_TEMPLATE = """
Analyze the following text chunk (in Markdown format) and extract the most relevant heading or title for this specific chunk and a very concise one-sentence summary of its main topic.
Provide the output ONLY in JSON format with keys "title" and "summary".
If you cannot determine a title or summary, use null for that value.

CHUNK CONTENT:
{chunk_content}

JSON OUTPUT:
"""

MAX_CONTENT_SNIPPET_LENGTH = 3000  # Limit context sent to LLM for document metadata


async def generate_metadata(
    content: str,
    prompt_template: str,
    llm_client: AbstractCompletionClient,
    max_snippet_length: Optional[int] = None,
) -> Optional[Dict[str, Optional[str]]]:
    """
    Generates title and summary for given content using an LLM.

    Args:
        content: The text content (document or chunk).
        prompt_template: The prompt template to use.
        llm_client: An instance of AbstractCompletionClient.
        max_snippet_length: Max characters of content to send (for documents).

    Returns:
        A dictionary with 'title' and 'summary' keys, or None on failure.
        Values can be None if the LLM couldn't determine them.
    """
    if not content:
        return None

    content_to_send = content
    if max_snippet_length and len(content) > max_snippet_length:
        content_to_send = content[:max_snippet_length] + "\n... [content truncated]"
        logger.debug(
            f"Truncated content to {max_snippet_length} chars for LLM metadata generation."
        )

    prompt = prompt_template.format(
        content_snippet=content_to_send, chunk_content=content_to_send
    )  # Use both formats

    try:
        logger.debug(
            f"Requesting metadata generation from LLM: {llm_client.get_model_name()}"
        )
        completion = await llm_client.generate_completion(
            prompt=prompt, temperature=0.1
        )  # Low temp for factual extraction

        if not completion:
            logger.warning("LLM completion returned empty for metadata generation.")
            return None

        # Attempt to parse the JSON response
        try:
            # Find the JSON part (sometimes LLMs add preamble/postamble)
            json_match = re.search(r"\{.*\}", completion, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                metadata = json.loads(json_str)
                # Basic validation
                if (
                    isinstance(metadata, dict)
                    and "title" in metadata
                    and "summary" in metadata
                ):
                    # Normalize empty strings to None
                    title = metadata.get("title")
                    summary = metadata.get("summary")
                    return {
                        "title": title if title else None,
                        "summary": summary if summary else None,
                    }
                else:
                    logger.warning(
                        f"LLM metadata response JSON missing keys: {completion}"
                    )
                    return None
            else:
                logger.warning(
                    f"Could not find JSON in LLM metadata response: {completion}"
                )
                return None

        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse JSON from LLM metadata response: {completion}"
            )
            return None  # Return None if JSON parsing fails

    except (CompletionError, Exception) as e:
        logger.error(f"Error during LLM metadata generation: {e}", exc_info=True)
        return None  # Return None on any LLM error


async def generate_document_metadata(
    content: str, llm_client: AbstractCompletionClient
) -> Optional[Dict[str, Optional[str]]]:
    """Helper to generate metadata specifically for a full document."""
    return await generate_metadata(
        content,
        DOCUMENT_METADATA_PROMPT_TEMPLATE,
        llm_client,
        max_snippet_length=MAX_CONTENT_SNIPPET_LENGTH,
    )


async def generate_chunk_metadata(
    chunk_content: str, llm_client: AbstractCompletionClient
) -> Optional[Dict[str, Optional[str]]]:
    """Helper to generate metadata specifically for a text chunk."""
    return await generate_metadata(
        chunk_content, CHUNK_METADATA_PROMPT_TEMPLATE, llm_client
    )
