import asyncio
import aiohttp  # Direct dependency
from typing import Optional, List, Set, Deque, Tuple, Dict
from urllib.parse import urlparse, urlunparse, urljoin
import xml.etree.ElementTree as ET
from collections import deque
from bs4 import BeautifulSoup  # Still needed for parsing potentially rendered HTML

from config.logger import get_logger, setup_logging

logger = get_logger(__name__)
# logging.basicConfig(level=logging.INFO) # Basic logging setup for example

# Namespace for sitemap schemas (remains the same)
SITEMAP_NS = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Default Request Timeout (seconds)
DEFAULT_AIOHTTP_TIMEOUT = 30
# Basic User-Agent
DEFAULT_HEADERS = {"User-Agent": "Python Sitemap Fetcher (aiohttp)"}


async def _fetch_content_aiohttp(
    url: str, session: aiohttp.ClientSession, timeout: float = DEFAULT_AIOHTTP_TIMEOUT
) -> Optional[Tuple[str, int]]:
    """Helper to fetch content using aiohttp, returning text content
    and status code.
    """
    logger.debug(f"Attempting to fetch content via aiohttp from: {url}")
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=timeout),
            headers=DEFAULT_HEADERS,
            allow_redirects=True,  # Follow redirects for sitemaps/robots
            ssl=False,  # Consider ssl context for production if needed
        ) as response:
            status_code = response.status
            logger.debug(f"Received status {status_code} for {url}")

            if status_code == 200:
                try:
                    # Read text, assuming UTF-8, ignore errors for robustness
                    content = await response.text(encoding="utf-8", errors="ignore")
                    logger.debug(
                        "Successfully fetched content "
                        f"({len(content)} chars) from {url}"
                    )
                    return content, status_code
                except Exception as read_e:
                    logger.error(f"Error reading response text from {url}: {read_e}")
                    return None
            elif status_code == 404:
                logger.info(f"URL not found (404): {url}")
                return None  # Explicitly return None on 404
            else:
                # Log other non-200 statuses but treat as fetch failure
                logger.warning(f"Received non-200/404 status {status_code} for {url}")
                # Consume payload to allow connection reuse, even if discarding
                await response.read()
                return None

    except asyncio.TimeoutError:
        logger.error(f"Timeout ({timeout}s) while fetching: {url}")
        return None
    except aiohttp.ClientError as e:
        # Covers connection errors, invalid URLs, etc.
        logger.error(f"aiohttp client error fetching {url}: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected error during fetching
        logger.exception(f"Unexpected error fetching {url} via aiohttp: {e}")
        return None


# --- _parse_robots_content remains the same ---
def _parse_robots_content(robots_txt_content: str) -> List[str]:
    """Parses robots.txt content to find Sitemap directives."""
    sitemap_urls = []
    if not robots_txt_content:
        return sitemap_urls
    try:
        for line in robots_txt_content.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    sitemap_url = parts[1].strip()
                    if sitemap_url:
                        sitemap_urls.append(sitemap_url)
                        logger.info(
                            f"Found sitemap directive in robots.txt: {sitemap_url}"
                        )
    except Exception as e:
        logger.error(f"Error parsing robots.txt content: {e}")
    return sitemap_urls


# --- _parse_sitemap_content remains the same ---
# It handles both direct XML and HTML-embedded XML (using BeautifulSoup)
def _parse_sitemap_content(
    fetched_content: str, source_url: str
) -> Tuple[List[str], List[str]]:
    """
    Parses fetched content (either raw XML or HTML containing embedded XML)
    to find page URLs or URLs of other sitemaps.

    Args:
        fetched_content: The string content fetched.
        source_url: The URL the content was fetched from (for logging).

    Returns:
        A tuple containing: (list_of_page_urls, list_of_nested_sitemap_urls)
    """
    page_urls: List[str] = []
    nested_sitemap_urls: List[str] = []
    xml_to_parse = None

    if not fetched_content:
        return page_urls, nested_sitemap_urls

    try:
        logger.debug(f"Attempting direct XML parse for {source_url}")
        if fetched_content.startswith("\ufeff"):
            content_to_try = fetched_content[1:]
        else:
            content_to_try = fetched_content
        root = ET.fromstring(content_to_try)
        xml_to_parse = root
    except ET.ParseError:
        logger.warning(
            f"Direct XML parse failed for {source_url}. Attempting HTML extraction."
        )
        try:
            soup = BeautifulSoup(fetched_content, "lxml")
            xml_source_div = soup.find("div", id="webkit-xml-viewer-source-xml")
            if xml_source_div:
                embedded_xml_string = xml_source_div.get_text()
                if embedded_xml_string:
                    logger.info(
                        f"Found embedded XML within HTML for {source_url}. "
                        "Parsing extracted XML."
                    )
                    if embedded_xml_string.startswith("\ufeff"):
                        embedded_xml_string = embedded_xml_string[1:]
                    try:
                        root = ET.fromstring(embedded_xml_string)
                        xml_to_parse = root
                    except ET.ParseError as inner_e:
                        logger.error(
                            "Failed to parse extracted XML from HTML "
                            f"for {source_url}: {inner_e}"
                        )
                else:
                    logger.warning(
                        f"Found XML source div in HTML for {source_url}, "
                        "but it was empty."
                    )
            else:
                logger.warning(
                    "Could not find embedded XML source "
                    f"('#webkit-xml-viewer-source-xml') in HTML from {source_url}."
                )
        except Exception as html_e:
            logger.error(
                f"Error during HTML parsing fallback for {source_url}: {html_e}"
            )

    if xml_to_parse is not None:
        try:
            root_tag = xml_to_parse.tag.lower()
            if "}" in root_tag:
                root_tag_local = root_tag.split("}", 1)[1]
            else:
                root_tag_local = root_tag

            if root_tag_local == "sitemapindex":
                logger.debug(f"Parsing sitemap index file from {source_url}")
                for sitemap_element in xml_to_parse.findall("ns:sitemap", SITEMAP_NS):
                    loc_element = sitemap_element.find("ns:loc", SITEMAP_NS)
                    if loc_element is not None and loc_element.text:
                        nested_sitemap_urls.append(loc_element.text.strip())
                logger.info(
                    f"Found {len(nested_sitemap_urls)} nested sitemaps in "
                    f"index {source_url}"
                )
            elif root_tag_local == "urlset":
                logger.debug(f"Parsing URL set file from {source_url}")
                for url_element in xml_to_parse.findall("ns:url", SITEMAP_NS):
                    loc_element = url_element.find("ns:loc", SITEMAP_NS)
                    if loc_element is not None and loc_element.text:
                        page_urls.append(loc_element.text.strip())
                logger.info(f"Found {len(page_urls)} page URLs in sitemap {source_url}")
            else:
                logger.warning(
                    "Parsed XML root tag is not <sitemapindex> or <urlset>"
                    f" for {source_url}: {xml_to_parse.tag}"
                )
        except Exception as parse_e:
            logger.exception(
                f"Unexpected error parsing XML structure from {source_url}: {parse_e}"
            )

    return page_urls, nested_sitemap_urls


async def find_sitemap(
    start_url: str,
    session: aiohttp.ClientSession,  # Pass the session in
) -> Optional[List[str]]:
    """
    Fetches and parses sitemaps using aiohttp directly.

    Args:
        start_url: The URL of the website (e.g., 'https://www.example.com/page').
        session: An active aiohttp.ClientSession instance.

    Returns:
        A list of unique page URLs found in the sitemap(s), or None if no
        sitemap information could be retrieved or parsed successfully.
    """
    try:
        # 1. Parse the input URL (same as before)
        parsed_start_url = urlparse(start_url)
        if not parsed_start_url.scheme or not parsed_start_url.netloc:
            logger.error(f"Invalid start URL provided: {start_url}")
            return None
        base_site_url = urlunparse(
            (parsed_start_url.scheme, parsed_start_url.netloc, "", "", "", "")
        )

        # --- Initialization (same as before) ---
        sitemaps_to_process: Deque[str] = deque()
        processed_sitemap_urls: Set[str] = set()
        all_found_page_urls: Set[str] = set()
        initial_content_cache: Dict[str, Tuple[str, int]] = {}  # Cache initial fetches

        # --- Strategy 1: Check /sitemap.xml ---
        default_sitemap_url = urljoin(base_site_url, "/sitemap.xml")
        logger.info(
            f"Attempting strategy 1: Fetching default sitemap {default_sitemap_url}"
        )
        # USE AIOHTTP FETCHER
        sitemap_xml_content_tuple = await _fetch_content_aiohttp(
            default_sitemap_url, session
        )

        if sitemap_xml_content_tuple:
            sitemaps_to_process.append(default_sitemap_url)
            initial_content_cache[default_sitemap_url] = sitemap_xml_content_tuple
        else:
            # --- Strategy 2: Check robots.txt ---
            robots_url = urljoin(base_site_url, "/robots.txt")
            logger.info(
                f"Strategy 1 failed. Attempting strategy 2: Fetching {robots_url}"
            )
            # USE AIOHTTP FETCHER
            robots_content_tuple = await _fetch_content_aiohttp(robots_url, session)

            if robots_content_tuple:
                robots_content, _ = robots_content_tuple
                # USE SAME PARSER
                sitemap_urls_from_robots = _parse_robots_content(robots_content)
                if sitemap_urls_from_robots:
                    for s_url in sitemap_urls_from_robots:
                        if (
                            s_url not in processed_sitemap_urls
                            and s_url not in sitemaps_to_process
                        ):
                            sitemaps_to_process.append(s_url)
                    logger.info(
                        f"Found {len(sitemap_urls_from_robots)} sitemap(s) "
                        "via robots.txt"
                    )
                else:
                    logger.info("Found robots.txt, but no Sitemap directives inside.")
                # Cache robots content if needed, although unlikely to be
                # referenced by index
                initial_content_cache[robots_url] = robots_content_tuple
            else:
                logger.warning(
                    f"Failed to fetch both {default_sitemap_url} and {robots_url}. "
                    "Cannot find sitemap info."
                )
                return None

        # --- Process Sitemaps (same logic, uses aiohttp fetcher) ---
        logger.info(f"Starting to process sitemap queue: {list(sitemaps_to_process)}")
        while sitemaps_to_process:
            current_sitemap_url = sitemaps_to_process.popleft()

            if current_sitemap_url in processed_sitemap_urls:
                continue
            logger.info(f"Processing sitemap: {current_sitemap_url}")
            processed_sitemap_urls.add(current_sitemap_url)

            content_tuple = initial_content_cache.get(current_sitemap_url)
            if not content_tuple:
                # USE AIOHTTP FETCHER
                content_tuple = await _fetch_content_aiohttp(
                    current_sitemap_url, session
                )

            if not content_tuple:
                logger.warning(
                    f"Failed to fetch content for sitemap URL: {current_sitemap_url}"
                )
                continue

            fetched_content, _ = content_tuple
            # USE SAME PARSER
            page_urls, nested_sitemap_urls = _parse_sitemap_content(
                fetched_content, current_sitemap_url
            )

            all_found_page_urls.update(page_urls)
            for nested_url in nested_sitemap_urls:
                if (
                    nested_url not in processed_sitemap_urls
                    and nested_url not in sitemaps_to_process
                ):
                    sitemaps_to_process.append(nested_url)

        # --- Final Result (same as before) ---
        if all_found_page_urls:
            logger.info(
                f"Finished processing. Found {len(all_found_page_urls)} unique "
                "page URLs."
            )
            return sorted(list(all_found_page_urls))
        else:
            logger.warning(
                "Processed potential sitemap locations, but found no page URLs "
                f"for {start_url}"
            )
            return None

    except Exception as e:
        logger.exception(f"General error in find_sitemap for {start_url}: {e}")
        return None


async def fetch_sitemap(url: str) -> Optional[List[str]]:
    async with aiohttp.ClientSession() as session:
        return await find_sitemap(url, session)


# --- Example Usage ---
async def main():
    setup_logging()

    target_urls = ["https://docs.pydantic.dev/latest/"]  # Example with index
    # target_urls = ["https://www.google.com"] # Example with robots.txt

    # Create a single ClientSession for efficiency
    async with aiohttp.ClientSession() as session:
        for target_url in target_urls:
            print("-" * 40)
            print(f"Fetching sitemap URLs for: {target_url} (using aiohttp)")

            # Call the aiohttp version, passing the session
            page_urls = await find_sitemap(target_url, session)

            if page_urls:
                print(f"\nFound {len(page_urls)} URLs:")
                if len(page_urls) > 15:
                    for url in page_urls[:10]:
                        print(f"  - {url}")
                    print("  ...")
                    for url in page_urls[-5:]:
                        print(f"  - {url}")
                else:
                    for url in page_urls:
                        print(f"  - {url}")
            else:
                print("\nCould not retrieve or parse any sitemap URLs.")
            print("-" * 40)


if __name__ == "__main__":
    # Ensure you have aiohttp, beautifulsoup4, and lxml installed
    # pip install aiohttp beautifulsoup4 lxml
    asyncio.run(main())
