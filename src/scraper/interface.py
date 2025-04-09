from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union


class ScraperInterface(ABC):
    """
    Abstract Base Class defining the interface for a generic asynchronous
    scraper service.
    """

    @abstractmethod
    async def __aenter__(self) -> "ScraperInterface":
        """Async context manager entry."""
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        raise NotImplementedError

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """
        Checks the health/status of the underlying scraper service.

        Returns:
            A dictionary containing status information. Structure may vary
            depending on the implementation.
        """
        raise NotImplementedError

    @abstractmethod
    async def submit_scrape_job(
        self, urls: Union[str, List[str]], config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submits a new scrape job to the service.

        Args:
            urls: A single URL string or a list of URL strings to scrape.
            config: An optional dictionary containing configuration specific
                    to the scraping task and backend (e.g., extraction rules,
                    rendering options, priority).

        Returns:
            A unique identifier (job ID) for the submitted job.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_scrape_result(
        self,
        job_id: str,
        timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Waits for a scrape job to complete and retrieves its results.

        This method should handle polling or waiting until the job is
        finished (completed or failed).

        Args:
            job_id: The unique identifier of the job.
            timeout: Maximum time (in seconds) to wait for completion.
                     Implementation should define a default if None.
            polling_interval: How often (in seconds) to check the status if polling.
                              Implementation should define a default if None.

        Returns:
            A dictionary containing the results of the scrape job.
            The exact structure depends on the job and implementation.

        Raises:
            JobTimeoutError: If the job doesn't complete within the timeout.
            JobFailedError: If the job execution fails.
            ConnectionError: If connection to the service fails.
            APIError: For other API-related errors.
            # Specific exception types may vary by implementation
        """
        raise NotImplementedError

    @abstractmethod
    async def scrape_and_wait(
        self,
        urls: Union[str, List[str]],
        config: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Convenience method to submit a job, wait for completion, and return results.

        Args:
            urls: A single URL string or a list of URL strings to scrape.
            config: An optional dictionary containing configuration for the job.
            timeout: Maximum time (in seconds) to wait for completion.
            polling_interval: How often (in seconds) to check the status if polling.

        Returns:
            A dictionary containing the results of the scrape job.

        Raises:
            JobTimeoutError, JobFailedError, ConnectionError, APIError etc.
            (as defined by the implementation of get_scrape_result)
        """
        raise NotImplementedError

    # Optional: Keep yield-based helper if desired, but maybe implementation-specific
    # @abstractmethod
    # async def scrape_and_yield(
    #     self,
    #     urls: Union[str, List[str]],
    #     config: Optional[Dict[str, Any]] = None,
    #     timeout: Optional[float] = None,
    #     polling_interval: Optional[float] = None,
    # ) -> AsyncGenerator[Dict[str, Any], None]:
    #     """ Submits, waits, and yields results upon successful completion. """
    #     raise NotImplementedError
