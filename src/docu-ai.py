import asyncio
from functools import wraps
import typer
from typing_extensions import Annotated

from config.logger import setup_logging, get_logger

# --- Update import path ---
from ingestion_pipeline.processor import process_data_source

# --------------------------
from db import PostgresDBRepository, AsyncSessionLocal, async_engine, shutdown_db_engine

setup_logging()

logger = get_logger("CLI")
# Define app name based on renamed pipeline directory
app = typer.Typer(
    help="Docu-AI CLI for ingesting and processing documentation sources."
)


def async_command(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


@app.command(
    name="ingest-site",  # Changed command name to be more descriptive
    help="Discover, scrape, process, and ingest a documentation source URL using sitemap or link crawling.",
)
@async_command
async def ingest_site_command(  # Changed function name
    source_url: Annotated[
        str, typer.Argument(..., help="The starting URL of the documentation source.")
    ],
):
    """
    CLI command to run the full ingestion pipeline for a source URL.
    """
    logger.info(f"Received ingest command for URL: {source_url}")
    db_repo = None
    try:
        logger.info("Initializing database repository...")
        db_repo = PostgresDBRepository(
            session_maker=AsyncSessionLocal, engine=async_engine
        )

        logger.info("Starting data source ingestion pipeline...")
        # Call the renamed pipeline function
        await process_data_source(source_url, db_repo)
        logger.info("Ingestion pipeline command finished.")

    except Exception as e:
        logger.critical(f"CLI command failed: {e}", exc_info=True)
        typer.echo(
            f"Error: An critical error occurred. Check logs/app.log. Details: {e}",
            err=True,
        )
        raise typer.Exit(code=1)
    finally:
        if db_repo:
            logger.info("Shutting down database engine...")
            await shutdown_db_engine()
        else:
            logger.info("DB repository not initialized, skipping engine shutdown.")


@app.command(name="hello", help="A simple test command.")
def hello_command(
    name: Annotated[str, typer.Option(help="The name to say hello to.")] = "World",
):
    """Says hello."""
    message = f"Hello {name}!"
    logger.info(f"Executing hello command: {message}")
    typer.echo(message)


if __name__ == "__main__":
    app()
