import asyncio
from typing import Optional
import sys
import os

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult

# --- Add src directory to sys.path ---
# Calculate the path to the src directory relative to this file
# This file is in src/mcp_server, so src is one level up
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
# ------------------------------------

# Setup logger first (ensure logger config is loaded)
from config.logger import setup_logging, get_logger

# Import DB and LLM components
from db import PostgresDBRepository, AsyncSessionLocal, async_engine, shutdown_db_engine
from llm.embedding import create_embedding_client

# Import tool functions
from .tools import (
    vector_search,
    get_document_by_id,
    get_documents_by_url,
    get_document_chunks,
    list_data_sources,
)

setup_logging()

logger = get_logger("MCPServer")

# --- Initialize MCP Server ---
# Choose a name for your server
mcp = FastMCP("docu-ai-search-server", version="0.1.0")

# --- Initialize Dependencies ---
# These need to be available to the tool functions
# Using globals here for simplicity, consider dependency injection for larger apps
db_repo = PostgresDBRepository(session_maker=AsyncSessionLocal, engine=async_engine)
embedding_client = create_embedding_client()  # Assumes settings are loaded via config

# --- Register Tools ---
# FastMCP uses function signatures and docstrings for schema generation


@mcp.tool()
async def search_similar_chunks(
    query_text: str, limit: int = 5, min_similarity: Optional[float] = None
) -> CallToolResult:
    """Finds document text chunks semantically similar to a query."""
    # Pass dependencies to the actual tool logic
    return await vector_search(
        mcp, db_repo, embedding_client, query_text, limit, min_similarity
    )


@mcp.tool()
async def retrieve_document_by_id(document_id: int) -> CallToolResult:
    """Retrieves full document content and metadata by its unique ID."""
    return await get_document_by_id(db_repo, document_id)


@mcp.tool()
async def retrieve_documents_by_url(url: str) -> CallToolResult:
    """Retrieves metadata for all documents matching a specific URL."""
    return await get_documents_by_url(db_repo, url)


@mcp.tool()
async def retrieve_document_chunks(
    document_id: int, limit: Optional[int] = 20
) -> CallToolResult:
    """Retrieves the text chunks for a specific document ID, ordered sequentially."""
    return await get_document_chunks(db_repo, document_id, limit)


@mcp.tool()
async def list_available_sources() -> CallToolResult:
    """Lists all the data sources available in the system."""
    return await list_data_sources(db_repo)


# --- Main Execution ---
if __name__ == "__main__":
    logger.info("Starting Docu-AI MCP Server...")
    try:
        # Run the server using stdio transport
        # mcp.run() defaults to stdio
        mcp.run(transport="stdio")
    except Exception as e:
        logger.critical(f"MCP Server failed to start or crashed: {e}", exc_info=True)
    finally:
        # Ensure DB engine is closed when server stops
        logger.info("MCP Server shutting down. Closing database engine...")
        # Need to run async shutdown in an event loop
        asyncio.run(shutdown_db_engine())
        logger.info("Database engine closed.")
