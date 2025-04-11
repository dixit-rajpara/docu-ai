import re
from typing import List, Dict

from config.logger import get_logger

logger = get_logger(__name__)

# Regex to split by Markdown headings (##, ###, etc.) or multiple newlines
MARKDOWN_SPLIT_REGEX = r"(?=\n{2,}|\n#+\s)"

DEFAULT_MIN_CHUNK_SIZE = 50
DEFAULT_MAX_CHUNK_SIZE = 1000
DEFAULT_OVERLAP_SIZE = 100  # Default character overlap


def chunk_markdown(
    markdown_content: str,
    min_chunk_size: int = DEFAULT_MIN_CHUNK_SIZE,
    max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
    overlap_size: int = DEFAULT_OVERLAP_SIZE,  # Added overlap parameter
) -> List[Dict[str, any]]:
    """
    Splits markdown content into potentially overlapping chunks based on
    headings or paragraphs.

    Args:
        markdown_content: The markdown string to chunk.
        min_chunk_size: Minimum character length for a chunk (excluding overlap).
        max_chunk_size: Target maximum character length for a chunk (excluding overlap).
        overlap_size: Number of characters to overlap between consecutive chunks.

    Returns:
        A list of dictionaries, each representing a chunk with 'text' and 'order'.
    """
    if not markdown_content:
        return []

    if overlap_size >= max_chunk_size:
        logger.warning(
            "Overlap size is greater than or equal to max chunk size. "
            "Setting overlap to 0."
        )
        overlap_size = 0
    if overlap_size < 0:
        overlap_size = 0

    # Split based on regex
    potential_chunks = re.split(MARKDOWN_SPLIT_REGEX, markdown_content)

    chunks = []
    current_chunk_content = ""
    chunk_order = 0
    previous_overlap = ""  # Store overlap from the *previous* finalized chunk

    for part in potential_chunks:
        part = part.strip()
        if not part:
            continue

        # If adding the next part doesn't exceed max size (roughly), append it
        # Note: This check doesn't precisely account for future overlap removal yet
        if (
            not current_chunk_content
            or len(current_chunk_content) + len(part) + 1 <= max_chunk_size
        ):
            current_chunk_content += ("\n" + part) if current_chunk_content else part
        else:
            # Current chunk is full or next part makes it too big.
            # Finalize current_chunk_content.
            if len(current_chunk_content) >= min_chunk_size:
                # Prepend overlap from the previous chunk before adding
                chunk_text_with_overlap = (
                    (previous_overlap + "\n" + current_chunk_content).strip()
                    if previous_overlap
                    else current_chunk_content
                )

                chunks.append({"text": chunk_text_with_overlap, "order": chunk_order})
                chunk_order += 1

                # Calculate the overlap for the *next* chunk from the end
                # of *this* chunk's original content
                if overlap_size > 0 and len(current_chunk_content) > overlap_size:
                    previous_overlap = current_chunk_content[-overlap_size:]
                else:
                    # Overlap is the whole chunk if it's small
                    previous_overlap = current_chunk_content
            else:
                # Chunk too small, potentially discard or merge? For now, discard.
                # Update overlap in case the small chunk still provides context
                if overlap_size > 0 and len(current_chunk_content) > 0:
                    previous_overlap = current_chunk_content[-overlap_size:]

            # Start a new chunk with the current part
            current_chunk_content = part

        # Handle cases where a single part exceeds max_chunk_size (simple split)
        # This part needs refinement to handle overlap correctly during forced splits
        while len(current_chunk_content) > max_chunk_size:
            split_index = current_chunk_content.rfind(". ", 0, max_chunk_size) + 1
            if split_index <= 0:
                split_index = current_chunk_content.rfind("\n", 0, max_chunk_size) + 1
            if split_index <= 0:
                split_index = max_chunk_size

            chunk_to_add_content = current_chunk_content[:split_index].strip()

            if len(chunk_to_add_content) >= min_chunk_size:
                chunk_text_with_overlap = (
                    (previous_overlap + "\n" + chunk_to_add_content).strip()
                    if previous_overlap
                    else chunk_to_add_content
                )
                chunks.append({"text": chunk_text_with_overlap, "order": chunk_order})
                chunk_order += 1

                # Update overlap for the next piece
                if overlap_size > 0 and len(chunk_to_add_content) > overlap_size:
                    previous_overlap = chunk_to_add_content[-overlap_size:]
                else:
                    previous_overlap = chunk_to_add_content

            current_chunk_content = current_chunk_content[split_index:].strip()

    # Add the last remaining chunk
    if current_chunk_content and len(current_chunk_content) >= min_chunk_size:
        chunk_text_with_overlap = (
            (previous_overlap + "\n" + current_chunk_content).strip()
            if previous_overlap
            else current_chunk_content
        )
        chunks.append({"text": chunk_text_with_overlap, "order": chunk_order})

    if chunks:
        logger.info(
            f"Chunked content into {len(chunks)} chunks with overlap approx "
            f"{overlap_size} chars."
        )
    else:
        logger.warning("No chunks were generated after processing.")
    return chunks
