from typing import Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

# Use relative imports assuming structure allows it or adjust as needed
from db import AbstractDBRepository, Document, DocumentChunk
from llm.embedding import AbstractEmbeddingClient, EmbeddingError

from config.logger import get_logger

logger = get_logger(__name__)


# --- Helper Function to Format Results ---
def format_chunk_result(chunk: DocumentChunk, score: Optional[float] = None) -> str:
    """Formats a single chunk result for display."""
    doc_id = chunk.document_id
    chunk_id = chunk.chunk_id
    order = chunk.chunk_order
    # Access the document's URL, providing a default if document is missing
    doc_url = chunk.document.url if chunk.document else "[URL Not Available]"
    text_preview = chunk.chunk_text[:200].strip().replace("\n", " ") + "..."
    similarity_str = f" (Similarity: {score:.4f})" if score is not None else ""
    return (
        f"DocID: {doc_id}, ChunkID: {chunk_id}, "
        f"Order: {order}{similarity_str}\n"
        f"URL: {doc_url}\n"
        f"Preview: {text_preview}\n"
    )


def format_document_result(doc: Document) -> str:
    """Formats a single document result."""
    title = doc.title or "[No Title]"
    summary = doc.summary or "[No Summary]"
    url = doc.url
    source_name = doc.source.name if doc.source else "[Unknown Source]"
    # content_preview = (
    #     doc.markdown_content[:300].strip().replace("\n", " ") + "..."
    #     if doc.markdown_content
    #     else "[No Content]"
    # )
    return (
        f"DocID: {doc.document_id}\n"
        f"Title: {title}\n"
        f"URL: {url}\n"
        f"Source: {source_name}\n"
        f"Summary: {summary}\n"
        # f"Content Preview: {content_preview}\n" # Maybe too verbose for default tool output
    )


# --- Tool Implementations ---


async def vector_search(
    mcp: FastMCP,  # FastMCP instance is often passed implicitly or use context
    db_repo: AbstractDBRepository,
    embedding_client: AbstractEmbeddingClient,
    query_text: str,
    limit: int = 5,
    min_similarity: Optional[float] = None,
) -> CallToolResult:
    """
    Performs vector similarity search over document chunks based on query text.
    Each result includes the chunk preview and the URL of the parent document.

    Args:
        query_text: The natural language query to search for.
        limit: Maximum number of similar chunks to return (default: 5).
        min_similarity: Minimum cosine similarity threshold (0.0 to 1.0, optional).
    """
    logger.info(
        f"Received vector_search tool call. Query: '{query_text[:50]}...', "
        f"Limit: {limit}, Min Sim: {min_similarity}"
    )
    try:
        # 1. Get query embedding
        logger.debug("Generating embedding for query...")
        query_embedding = await embedding_client.generate_embeddings([query_text])
        if not query_embedding or not query_embedding[0]:
            raise EmbeddingError("Failed to generate embedding for the query text.")
        logger.debug("Query embedding generated.")

        # 2. Perform DB Search
        logger.debug("Searching database for similar chunks...")
        similar_chunks_with_scores = await db_repo.find_similar_chunks(
            query_vector=query_embedding[0],
            limit=limit,
            min_similarity=min_similarity,
            # source_ids=None # Add filter later if needed
        )
        logger.debug(f"Found {len(similar_chunks_with_scores)} potential chunks.")

        # 3. Format Results
        if not similar_chunks_with_scores:
            result_text = "No similar document chunks found matching your query."
        else:
            formatted_results = [
                format_chunk_result(chunk, score)
                for chunk, score in similar_chunks_with_scores
            ]
            result_text = (
                f"Found {len(formatted_results)} similar chunks for "
                f"query '{query_text}':\n\n\n---\n".join(formatted_results)
            )

        return CallToolResult(content=[TextContent(type="text", text=result_text)])

    except EmbeddingError as e:
        logger.error(f"Embedding error during vector_search: {e}", exc_info=True)
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=f"Error generating embedding: {e}")],
        )
    except Exception as e:
        logger.exception(
            f"Error during vector_search for query '{query_text[:50]}...': {e}"
        )
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=f"An unexpected error occurred during vector search: {e}",
                )
            ],
        )


async def get_document_by_id(
    db_repo: AbstractDBRepository,
    document_id: int,
) -> CallToolResult:
    """
    Retrieves the full details (metadata and markdown content) for a specific
    document ID.

    Args:
        document_id: The unique identifier of the document to retrieve.
    """
    logger.info(f"Received get_document_by_id tool call for ID: {document_id}")
    try:
        document = await db_repo.get_document_by_id(document_id)
        if not document:
            result_text = f"No document found with ID: {document_id}"
        else:
            # Format the full document details
            title = document.title or "[No Title]"
            url = document.url
            source = document.source.name if document.source else "[Unknown Source]"
            summary = document.summary or "[No Summary]"
            content = document.markdown_content or "[No Content Stored]"
            result_text = (
                f"Document Details (ID: {document_id}):\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Source: {source}\n"
                f"Summary: {summary}\n"
                f"---\n"
                f"Content:\n{content}"
            )

        return CallToolResult(content=[TextContent(type="text", text=result_text)])

    except Exception as e:
        logger.exception(f"Error during get_document_by_id for ID {document_id}: {e}")
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=f"An unexpected error occurred retrieving document {document_id}: {e}",
                )
            ],
        )


async def get_documents_by_url(
    db_repo: AbstractDBRepository,
    url: str,
) -> CallToolResult:
    """
    Retrieves metadata for all documents matching a specific URL across all data sources.

    Args:
        url: The exact URL to search for.
    """
    logger.info(f"Received get_documents_by_url tool call for URL: {url}")
    try:
        documents = await db_repo.get_documents_by_url(url)
        if not documents:
            result_text = f"No documents found with URL: {url}"
        else:
            formatted_results = [format_document_result(doc) for doc in documents]
            result_text = (
                f"Found {len(documents)} document(s) matching URL '{url}':\n\n"
                + "\n---\n".join(formatted_results)
            )

        return CallToolResult(content=[TextContent(type="text", text=result_text)])

    except Exception as e:
        logger.exception(f"Error during get_documents_by_url for URL {url}: {e}")
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=f"An unexpected error occurred searching for URL {url}: {e}",
                )
            ],
        )


async def get_document_chunks(
    db_repo: AbstractDBRepository,
    document_id: int,
    limit: Optional[int] = 20,  # Add a default limit
) -> CallToolResult:
    """
    Retrieves the text chunks associated with a specific document ID.

    Args:
        document_id: The unique identifier of the document whose chunks are needed.
        limit: Maximum number of chunks to return (default: 20).
    """
    logger.info(
        f"Received get_document_chunks tool call for Doc ID: {document_id}, Limit: {limit}"
    )
    try:
        chunks = await db_repo.get_chunks_by_document_id(document_id, limit=limit)
        if not chunks:
            result_text = f"No chunks found for document ID: {document_id}"
        else:
            formatted_results = [format_chunk_result(chunk) for chunk in chunks]
            result_text = (
                f"Found {len(chunks)} chunk(s) for document ID {document_id}:\n\n"
                + "\n---\n".join(formatted_results)
            )
            if limit and len(chunks) >= limit:
                result_text += (
                    f"\n\n(Note: Results limited to the first {limit} chunks)"
                )

        return CallToolResult(content=[TextContent(type="text", text=result_text)])

    except Exception as e:
        logger.exception(
            f"Error during get_document_chunks for Doc ID {document_id}: {e}"
        )
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=f"An unexpected error occurred retrieving chunks for document {document_id}: {e}",
                )
            ],
        )


async def list_data_sources(
    db_repo: AbstractDBRepository,
) -> CallToolResult:
    """
    Lists all the data sources that have been ingested into the system.
    """
    logger.info("Received list_data_sources tool call.")
    try:
        sources = await db_repo.list_data_sources()
        if not sources:
            result_text = "No data sources found in the system."
        else:
            formatted_results = [
                f"- ID: {s.source_id}, Name: {s.name}, URL: {s.base_url or '[N/A]'}"
                for s in sources
            ]
            result_text = f"Found {len(sources)} data source(s):\n" + "\n".join(
                formatted_results
            )

        return CallToolResult(content=[TextContent(type="text", text=result_text)])

    except Exception as e:
        logger.exception(f"Error during list_data_sources: {e}")
        return CallToolResult(
            isError=True,
            content=[
                TextContent(
                    type="text",
                    text=f"An unexpected error occurred listing data sources: {e}",
                )
            ],
        )
