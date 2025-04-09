from typing import Dict, Any, Optional

from config.settings import settings
from .interface import ScraperInterface
from .crawl4ai_client import AsyncCrawl4AIClient


class ScraperFactory:
    """
    Factory class for creating scraper instances based on configuration.
    """

    @staticmethod
    def create_scraper(
        scraper_type: str = None, config: Optional[Dict[str, Any]] = None
    ) -> ScraperInterface:
        """
        Creates a scraper instance of the specified type with the given config.

        Args:
            scraper_type: The type of scraper to create (e.g., 'crawl4ai').
            config: A dictionary containing configuration specific to the scraper type.
                    Keys needed depend on the scraper implementation.

        Returns:
            An instance implementing the ScraperInterface.

        Raises:
            ValueError: If the scraper_type is unknown or required config is missing.
        """
        scraper_settings = settings.scraper
        if scraper_type is None:
            scraper_type = scraper_settings.provider
        if scraper_type is None:
            raise ValueError("Scraper type is required")

        if config is None:
            config = {}

        if scraper_type.lower() == "crawl4ai":
            # Provide defaults or raise errors if required keys are missing
            base_url = config.get("base_url", str(scraper_settings.api_host))

            # Can be None
            api_token = config.get(
                "api_token", scraper_settings.api_key.get_secret_value()
            )

            # Add other relevant config keys: polling_interval, request_timeout, etc.
            polling_interval = config.get(
                "polling_interval", scraper_settings.polling_interval
            )
            request_timeout = config.get(
                "request_timeout", scraper_settings.request_timeout
            )
            default_job_timeout = config.get(
                "default_job_timeout", scraper_settings.default_job_timeout
            )
            max_concurrent_override = config.get(
                "max_concurrent_jobs_override",
                scraper_settings.max_concurrent_jobs_override,
            )

            return AsyncCrawl4AIClient(
                base_url=base_url,
                api_token=api_token,
                polling_interval=polling_interval,
                request_timeout=request_timeout,
                default_job_timeout=default_job_timeout,
                max_concurrent_jobs_override=max_concurrent_override,
            )
        # Example for a future scraper type
        # elif scraper_type.lower() == 'local_bs4':
        #     timeout = config.get('request_timeout', 30.0)
        #     user_agent = config.get('user_agent')
        #     return LocalBeautifulSoupScraper(timeout=timeout, user_agent=user_agent)

        else:
            raise ValueError(f"Unknown scraper type: {scraper_type}")


# --- Example Usage ---
# import asyncio
# from scraper_factory import ScraperFactory
#
# async def main():
#     # Option 1: Explicit type and config
#     # config = {"api_token": "my_secret", "base_url": "http://192.168.1.100:11235"}
#     # scraper = ScraperFactory.create_scraper('crawl4ai', config)
#
#     # Option 2: Create from environment variables
#     # (Assumes CRAWL4AI_API_TOKEN might be set in the environment)
#     scraper = ScraperFactory.create_scraper()
#
#     async with scraper:
#         health = await scraper.check_health()
#         print(f"Health from factory-created scraper: {health}")
#         # ... use scraper as before ...
#
# if __name__ == "__main__":
#    asyncio.run(main())
