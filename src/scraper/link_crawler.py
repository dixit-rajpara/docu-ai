import asyncio
from typing import Optional, List, Set, Deque, Tuple
from urllib.parse import urlparse, urlunparse, urljoin
from collections import deque
from bs4 import BeautifulSoup

from config.logger import get_logger, setup_logging

# Assuming your interface and factory are importable
from .interface import ScraperInterface
from .factory import ScraperFactory

# Assuming your exceptions are defined or accessible
from .crawl4ai_client import (  # Or import generic exceptions if defined
    JobTimeoutError,
    JobFailedError,
    ConnectionError,
    APIError,
    Crawl4AIError,
)

logger = get_logger("recursive_link_scraper")
# logging.basicConfig(level=logging.INFO) # Basic logging setup for example


def _is_same_domain(url_str1: str, url_str2: str) -> bool:
    """Checks if two URLs belong to the same domain (scheme + netloc)."""
    try:
        p1 = urlparse(url_str1)
        p2 = urlparse(url_str2)
        return p1.scheme == p2.scheme and p1.netloc == p2.netloc
    except ValueError:
        logger.warning(
            f"Could not parse URLs for domain check: '{url_str1}', '{url_str2}'"
        )
        return False


def _normalize_url(base_url: str, link: str) -> Optional[str]:
    """Constructs an absolute URL from a base URL and a link string."""
    try:
        # Join the base URL with the potentially relative link
        absolute_link = urljoin(base_url, link)
        # Parse the result to clean it up and remove fragments
        parsed_link = urlparse(absolute_link)
        # Reconstruct without fragment
        normalized = urlunparse(
            (
                parsed_link.scheme,
                parsed_link.netloc,
                parsed_link.path,
                parsed_link.params,
                parsed_link.query,
                "",  # No fragment
            )
        )
        # Basic check for valid schemes
        if parsed_link.scheme in ("http", "https"):
            return normalized
        else:
            logger.debug(f"Skipping link with unsupported scheme: {absolute_link}")
            return None
    except ValueError:
        logger.warning(
            f"Could not normalize URL from base '{base_url}' and link '{link}'"
        )
        return None


async def scrape_internal_links(
    start_url: str,
    scraper: ScraperInterface,
    max_depth: int = 1,  # Default to only scraping the start page and its links
) -> List[str]:
    """
    Recursively scrapes pages starting from a URL to find internal links
    up to a specified depth.

    Args:
        start_url: The initial URL to start scraping from.
        scraper: An initialized instance implementing ScraperInterface.
        max_depth: The maximum number of link levels to follow.
                   Depth 0: Only scrape the start_url.
                   Depth 1: Scrape start_url and pages linked directly from it.
                   Depth 2: Scrape start_url, its links, and links from those pages.

    Returns:
        A sorted list of unique internal URLs discovered within the depth limit.
        Returns an empty list if the start URL cannot be scraped or no internal
        links are found.
    """
    if max_depth < 0:
        logger.error("max_depth cannot be negative.")
        return []

    try:
        # Validate and normalize the starting URL
        normalized_start_url = _normalize_url(start_url, "")  # Normalize itself
        if not normalized_start_url:
            logger.error(f"Invalid start_url provided: {start_url}")
            return []

        start_parsed = urlparse(normalized_start_url)
        start_domain = start_parsed.netloc  # Used for comparison

        # --- Initialization for BFS crawl ---
        # Queue stores tuples of (url_to_visit, current_depth)
        queue: Deque[Tuple[str, int]] = deque([(normalized_start_url, 0)])
        # Keep track of visited URLs to avoid loops and redundant scraping
        visited: Set[str] = set()
        # Store all unique internal URLs found
        internal_urls_found: Set[str] = set()

        logger.info(
            f"Starting recursive scrape from '{normalized_start_url}' with max_depth={max_depth}"
        )

        # --- Main BFS Loop ---
        while queue:
            current_url, current_depth = queue.popleft()

            # Skip if already visited
            if current_url in visited:
                logger.debug(f"Skipping already visited: {current_url}")
                continue

            # Add to visited set *before* potential depth check failure
            visited.add(current_url)

            # Add to results *if* it's confirmed internal (start URL always is)
            # We add it here because even if we don't crawl *its* links due to depth,
            # the URL itself was reachable within the depth limit.
            if _is_same_domain(normalized_start_url, current_url):
                internal_urls_found.add(current_url)
            else:
                # Should theoretically not happen if we only add internal links, but good sanity check
                logger.warning(
                    f"URL in queue is not from the start domain: {current_url}"
                )
                continue

            # Check depth *before* scraping and adding links
            if current_depth >= max_depth:
                logger.debug(
                    f"Max depth ({max_depth}) reached for {current_url}. Not scraping its links."
                )
                continue

            logger.info(f"Scraping [Depth {current_depth}]: {current_url}")

            # --- Scrape the current URL ---
            try:
                # Assuming scrape_and_wait is safe to call multiple times
                # within the managed context of the main function.
                result_dict = await scraper.scrape_and_wait(urls=current_url)

                if not result_dict.get("success"):
                    error_msg = result_dict.get("error_message", "Unknown error")
                    status_code = result_dict.get("status_code", "N/A")
                    logger.warning(
                        f"Scrape failed for {current_url}. Status: {status_code}, Error: {error_msg}. Skipping links."
                    )
                    continue  # Skip processing links if scrape failed

                html_content = result_dict.get("html")
                if not html_content:
                    logger.warning(
                        f"Scrape successful for {current_url}, but no 'html' content found. Skipping links."
                    )
                    continue  # Skip processing links if no HTML

                # --- Parse HTML and Extract Links ---
                try:
                    # soup = BeautifulSoup(html_content, "lxml")  # Or 'html.parser'
                    soup = BeautifulSoup(html_content, "html.parser")
                    links_found_on_page = 0
                    for link_tag in soup.find_all("a", href=True):
                        href = link_tag["href"]
                        normalized_link = _normalize_url(current_url, href)

                        if normalized_link and normalized_link not in visited:
                            # Check if the link belongs to the *original* start domain
                            if _is_same_domain(normalized_start_url, normalized_link):
                                logger.debug(
                                    f"  Found internal link: {normalized_link}"
                                )
                                # Add to queue for potential future visit
                                queue.append((normalized_link, current_depth + 1))
                                links_found_on_page += 1
                            else:
                                logger.debug(
                                    f"  Skipping external link: {normalized_link}"
                                )
                        elif normalized_link and normalized_link in visited:
                            logger.debug(
                                f"  Skipping already processed link: {normalized_link}"
                            )

                    logger.info(
                        f"Found {links_found_on_page} new internal links to queue from {current_url}"
                    )

                except Exception as parse_e:
                    logger.error(
                        f"Error parsing HTML or extracting links from {current_url}: {parse_e}"
                    )
                    # Continue the loop, but this page's links won't be processed

            # Handle specific scraping errors for this URL
            except JobTimeoutError:
                logger.error(f"Timeout scraping {current_url}. Skipping links.")
                continue
            except JobFailedError as e:
                logger.error(
                    f"Scrape job failed for {current_url}: {e}. Skipping links."
                )
                continue
            except (ConnectionError, APIError) as e:
                logger.error(
                    f"API/Connection error scraping {current_url}: {e}. Skipping links."
                )
                continue
            except Crawl4AIError as e:
                logger.error(
                    f"Scraper error scraping {current_url}: {e}. Skipping links."
                )
                continue
            except Exception as e:
                logger.exception(
                    f"Unexpected error scraping {current_url}: {e}. Skipping links."
                )
                continue
            # End of scraping block

        # --- End of BFS Loop ---
        logger.info(
            f"Finished scraping. Found {len(internal_urls_found)} unique internal URLs."
        )
        return sorted(list(internal_urls_found))

    except Exception as e:
        logger.exception(f"General error during recursive scrape for {start_url}: {e}")
        return []


# --- Example Usage ---
async def main():
    # Setup basic logging
    setup_logging()
    logger = get_logger("recursive_link_scraper")

    # Create a scraper instance using the factory
    try:
        scraper_instance = ScraperFactory.create_scraper()
    except ValueError as e:
        logger.error(f"Failed to create scraper: {e}")
        return
    except Exception as e:
        logger.error(f"Failed to create scraper due to other error: {e}")
        return

    target_url = "https://docs.pydantic.dev/"  # Choose a starting point
    crawl_depth = 1  # How many levels deep to go (0=start page only, 1=start page + its links, etc.)

    print("-" * 40)
    print(f"Starting recursive link scrape for: {target_url} (Depth: {crawl_depth})")

    # Manage the scraper context for the whole duration
    async with scraper_instance:
        internal_links = await scrape_internal_links(
            start_url=target_url, scraper=scraper_instance, max_depth=crawl_depth
        )

    if internal_links:
        print(f"\nFound {len(internal_links)} internal URLs:")
        limit = 50  # Limit display output
        for i, url in enumerate(internal_links):
            if i < limit:
                print(f"  - {url}")
            elif i == limit:
                print(f"  ... (showing first {limit})")
                break
    else:
        print("\nNo internal links found or scrape failed.")
    print("-" * 40)


if __name__ == "__main__":
    # Ensure you have beautifulsoup4 and lxml installed
    # pip install beautifulsoup4 lxml
    asyncio.run(main())
