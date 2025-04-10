# src/scraper/discovery.py
import asyncio
import aiohttp
from typing import List, Optional

from config.logger import get_logger

# Import the specific functions from the refactored modules
from .sitemap_finder import find_sitemap
from .link_crawler import scrape_internal_links

# Import the factory to create scraper instance for fallback
from .factory import ScraperFactory

logger = get_logger(__name__)


async def get_site_urls(
    start_url: str,
    fallback_max_depth: int = 1,
    # Optional session/scraper can be added if preferred, but internal creation
    # is simpler
) -> List[str]:
    """
    Attempts to discover URLs for a given site, prioritizing explicit sitemaps
    (via sitemap.xml/robots.txt using aiohttp) and falling back to recursive
    link scraping if the first method fails or yields no results.

    Args:
        start_url: The initial URL of the website.
        fallback_max_depth: The maximum depth for the recursive link scraping
                            fallback method (default: 1).

    Returns:
        A sorted list of unique URLs discovered, or an empty list if both
        methods fail or find nothing.
    """
    logger.info(f"Starting URL discovery for: {start_url}")
    sitemap_urls: Optional[List[str]] = None

    # --- Attempt 1: Use aiohttp Sitemap Finder ---
    logger.info("Attempting discovery via sitemap_finder (aiohttp)...")
    try:
        # Create a session internally for this attempt
        async with aiohttp.ClientSession() as session:
            sitemap_urls = await find_sitemap(start_url, session)
    except Exception as e:
        logger.error(f"Error during sitemap_finder attempt: {e}", exc_info=True)
        sitemap_urls = None  # Ensure it's None on error

    if sitemap_urls:  # Check if list is not None *and* not empty
        logger.info(f"Sitemap finder successful. Found {len(sitemap_urls)} URLs.")
        return sitemap_urls  # Return immediately if successful

    logger.warning(
        "Sitemap finder failed or found no URLs. "
        "Attempting fallback: link_crawler (scraper)..."
    )

    # --- Attempt 2: Fallback to Recursive Link Crawler ---
    try:
        # Create scraper instance internally using the factory
        # Assumes factory uses settings from environment/config file
        scraper_instance = ScraperFactory.create_scraper()
        # Use the scraper within its context
        async with scraper_instance:
            crawled_urls = await scrape_internal_links(
                start_url=start_url,
                scraper=scraper_instance,
                max_depth=fallback_max_depth,
            )
        # Ensure return is a list, even if scrape_internal_links returns None on error
        return crawled_urls if crawled_urls is not None else []
    except Exception as e:
        logger.error(f"Error during link_crawler fallback attempt: {e}", exc_info=True)
        return []  # Return empty list on fallback error


# --- Example Usage ---
async def main():
    # Make sure logging is configured (e.g., via setup_logging())
    from config.logger import setup_logging

    setup_logging()

    # target_site = "https://docs.pydantic.dev/latest/" # Should use sitemap_finder
    target_site = "https://example.com/"  # Might use link_crawler if sitemap fails
    # target_site = "https://nonexistent-domain-xyz-abc.com/" # Should fail both

    print(f"\n--- Discovering URLs for: {target_site} ---")
    discovered_urls = await get_site_urls(target_site, fallback_max_depth=1)

    if discovered_urls:
        print(f"Discovered {len(discovered_urls)} URLs:")
        limit = 50
        for i, url in enumerate(discovered_urls):
            if i < limit:
                print(f"  - {url}")
            elif i == limit:
                print(f"  ... (showing first {limit})")
                break
    else:
        print("Could not discover any URLs using either method.")

    print("-" * 40)


if __name__ == "__main__":
    # Ensure dependencies are installed:
    # pip install aiohttp beautifulsoup4 lxml html2text pydantic-settings
    # Also ensure your scraper implementation's dependencies are met.
    asyncio.run(main())
