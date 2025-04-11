"""Command Line Interface for Documentation Scraper.

This module provides the main CLI interface for the documentation scraper application.
It allows users to run various commands like crawling documentation, managing the database,
and searching through documentation.
"""

import click

from config.logger import setup_logging, get_logger
from config.settings import settings

# Configure logging
setup_logging()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Documentation Scraper CLI.

    A tool for scraping, processing, and searching framework documentation.
    """
    pass


@cli.command()
def init_db():
    """Initialize the database with required schema."""
    logger.info("Initializing database")
    logger.info(f"Database URL: {settings.database.database_url}")
    # TODO: Implement database initialization logic
    click.echo("Initializing database...")


if __name__ == "__main__":
    cli()
