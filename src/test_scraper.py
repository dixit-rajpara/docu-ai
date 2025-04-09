import time
import asyncio

from scraper.factory import ScraperFactory
from scraper.interface import ScraperInterface
from scraper.crawl4ai_client import (
    JobTimeoutError,
    JobFailedError,
    ConnectionError,
    APIError,
)

from config.logger import get_logger

logger = get_logger("ScraperExample")


async def run_scraper_tasks(scraper: ScraperInterface):
    """Runs example tasks using the scraper interface"""
    try:
        # 1. Test Health Check
        print("--- Testing Health Check ---")
        health = await scraper.check_health()
        print(f"Health Status: {health}")
        # Assert based on expected Crawl4AI output (adapt if interface is more generic)
        assert (
            health.get("status") == "healthy"
            or health.get("status") == "unauthorized_health_check"
        )

        # 2. Basic Scrape using scrape_and_wait
        print("\n--- Testing Basic Scrape (scrape_and_wait) ---")
        basic_url = "https://httpbin.org/html"
        # Config is empty for basic Crawl4AI usage
        result = await scraper.scrape_and_wait(basic_url, config={})
        print(f"Basic Scrape Result Keys: {result.keys()}")
        print(f"Markdown length: {len(result.get('markdown', ''))}")
        assert "markdown" in result

        # 3. Scrape with Crawl4AI-specific Config
        print("\n--- Testing Scrape with Config ---")
        advanced_url = "https://news.ycombinator.com"
        # Pass Crawl4AI parameters within the config dictionary
        crawl4ai_config = {
            "priority": 8,
            "crawler_params": {
                "headless": True,
                "page_timeout": 20000,  # 20 seconds
            },
            "extra": {"word_count_threshold": 10},
        }
        adv_result = await scraper.scrape_and_wait(
            advanced_url,
            config=crawl4ai_config,
            timeout=45.0,  # Overall job timeout
        )
        print(f"Advanced Scrape Result Keys: {adv_result.keys()}")
        assert "markdown" in adv_result

        # 4. Test Timeout Scenario using scrape_and_wait
        print("\n--- Testing Job Timeout ---")
        try:
            timeout_url = "https://httpbin.org/delay/10"  # 10 second delay
            timeout_config = {
                "crawler_params": {"page_timeout": 15000}  # Browser timeout > delay
            }
            # Short overall job timeout for the client
            await scraper.scrape_and_wait(timeout_url, timeout_config, timeout=3.0)
        except JobTimeoutError as e:
            print(f"Successfully caught expected timeout: {e}")
        except (ConnectionError, APIError) as e:
            print(f"Could not test timeout due to connection/API issue: {e}")

        # 5. Test Concurrent Submissions
        print("\n--- Testing Concurrent Submissions (Rate Limiting) ---")
        concurrent_urls = [f"https://httpbin.org/delay/{i}" for i in range(1, 4)]
        tasks = [
            scraper.scrape_and_wait(url, config={}, timeout=15.0)
            for url in concurrent_urls
        ]
        start_time = time.monotonic()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.monotonic()
        print(f"Concurrent submissions completed in {end_time - start_time:.2f}s")
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                print(f"Job {i + 1} failed: {res}")
            else:
                print(
                    f"Job {i + 1} success. Markdown length: {len(res.get('markdown', ''))}"
                )

        # 6. Using Crawl4AI-specific helper (optional)
        # print("\n--- Testing Crawl4AI Specific Helper (crawl_and_yield) ---")
        # if isinstance(scraper, AsyncCrawl4AIClient): # Check type if needed
        #     yield_url = "https://httpbin.org/links/10/0"
        #     yield_request = {"urls": yield_url}
        #     async for result_payload in scraper.crawl_and_yield(yield_request):
        #          print(f"Yielded Result Keys: {result_payload.keys()}")
        #          assert "markdown" in result_payload
        # else:
        #      print("Skipping crawl_and_yield test (not available on generic interface)")

    except (JobFailedError, JobTimeoutError, ConnectionError, APIError) as e:
        logger.exception(f"A scraper error occurred: {e}")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")


async def main():
    # Instantiate the concrete implementation
    # Use the interface type hint for variables where possible
    scraper_client: ScraperInterface = ScraperFactory.create_scraper()

    async with scraper_client:
        await run_scraper_tasks(scraper_client)


if __name__ == "__main__":
    asyncio.run(main())
