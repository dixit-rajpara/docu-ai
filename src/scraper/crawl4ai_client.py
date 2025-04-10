import asyncio
import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

import aiohttp

from config.logger import get_logger
from .interface import ScraperInterface

logger = get_logger("AsyncCrawl4AIClient")


# --- Custom Exceptions (Map generic names if needed, or reuse) ---
class Crawl4AIError(Exception):
    """Base exception for Crawl4AI client errors."""

    pass


class ConnectionError(Crawl4AIError):
    """Raised when connection to the Crawl4AI service fails."""

    pass


class APIError(Crawl4AIError):
    """Raised for API-level errors (e.g., bad request, auth failure)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = f"API Error {status_code}: {message}"
        super().__init__(self.message)


# Map interface exception concepts to Crawl4AI specifics
# These could be subclasses of generic exceptions if needed
class JobTimeoutError(Crawl4AIError):  # Renamed from TaskTimeoutError
    """Raised when waiting for a task result times out."""

    pass


class JobFailedError(Crawl4AIError):  # Renamed from TaskFailedError
    """Raised when a crawl task fails on the server."""

    def __init__(self, job_id: str, error_info: Any):
        self.job_id = job_id  # Use generic term
        self.error_info = error_info
        message = f"Job {job_id} failed. Error info: {error_info}"
        super().__init__(message)


# --- The Client Class Implementing ScraperInterface ---
class AsyncCrawl4AIClient(ScraperInterface):  # Inherit from the interface
    """
    An asynchronous Python client for Crawl4AI, implementing ScraperInterface.

    Handles rate limiting, authentication, task submission, status polling,
    and result retrieval for a Crawl4AI service.
    """

    DEFAULT_BASE_URL = "http://localhost:11235"
    DEFAULT_POLLING_INTERVAL = 2.0  # seconds
    DEFAULT_REQUEST_TIMEOUT = 60.0  # seconds for individual HTTP requests
    DEFAULT_JOB_TIMEOUT = 300.0  # seconds for overall job completion

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_token: Optional[str] = None,
        polling_interval: float = DEFAULT_POLLING_INTERVAL,
        request_timeout: float = DEFAULT_REQUEST_TIMEOUT,
        default_job_timeout: float = DEFAULT_JOB_TIMEOUT,  # Renamed parameter
        max_concurrent_jobs_override: Optional[int] = None,  # Renamed parameter
        session: Optional[aiohttp.ClientSession] = None,
    ):
        """
        Initializes the AsyncCrawl4AIClient.

        Args:
            base_url: The base URL of the Crawl4AI service.
            api_token: Optional API token for authentication.
            polling_interval: Default interval (in seconds) for checking job status.
            request_timeout: Default timeout (in seconds) for individual HTTP requests.
            default_job_timeout: Default timeout (in seconds) for waiting for a
                                    job to complete.
            max_concurrent_jobs_override: Manually set max concurrent jobs.
                                          If None, fetched from /health endpoint.
            session: Optional external aiohttp.ClientSession to use.
                     If None, a new session is created internally.
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.polling_interval = polling_interval
        self.request_timeout = request_timeout
        self.default_job_timeout = default_job_timeout  # Use renamed attribute
        self._max_concurrent_jobs_override = (
            max_concurrent_jobs_override  # Use renamed attribute
        )

        self._headers = {"Accept": "application/json"}
        if self.api_token:
            self._headers["Authorization"] = f"Bearer {self.api_token}"

        self._external_session = session is not None
        self._session = session
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._semaphore_limit: Optional[int] = None
        self._initialized = False

    # --- Context Management (Implements Interface) ---
    async def __aenter__(self) -> "AsyncCrawl4AIClient":
        """Async context manager entry."""
        await self._get_session()
        await self._initialize_semaphore()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit. Closes session if internally managed."""
        if self._session and not self._external_session:
            logger.info("Closing internal aiohttp ClientSession.")
            await self._session.close()
            self._session = None
        self._initialized = False

    # --- Internal Helpers (Mostly unchanged) ---
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            logger.info("Creating new aiohttp ClientSession.")
            self._session = aiohttp.ClientSession(headers=self._headers)
        return self._session

    async def _initialize_semaphore(self) -> None:
        """Fetches server capacity and initializes the semaphore."""
        if self._initialized:
            return

        if self._max_concurrent_jobs_override is not None:
            concurrency = self._max_concurrent_jobs_override
            logger.info(f"Using overridden max concurrent jobs: {concurrency}")
        else:
            try:
                logger.info("Fetching server capacity from /health endpoint...")
                health_data = await self.check_health()  # Use the interface method
                # Adapt key name if needed, Crawl4AI uses 'max_concurrent_tasks'
                concurrency = health_data.get("max_concurrent_tasks", 1)
                if not isinstance(concurrency, int) or concurrency <= 0:
                    logger.warning(
                        "Invalid 'max_concurrent_tasks' from /health. Defaulting to 1."
                    )
                    concurrency = 1
                else:
                    logger.info(f"Server max concurrent jobs (tasks): {concurrency}")
            except (ConnectionError, APIError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"Failed to fetch server capacity: {e}. "
                    "Defaulting max concurrent jobs to 1. "
                    "Rate limiting may be inaccurate."
                )
                concurrency = 1

        self._semaphore = asyncio.Semaphore(concurrency)
        self._semaphore_limit = concurrency
        self._initialized = True
        logger.info(
            f"Rate limiting semaphore initialized with limit: {self._semaphore_limit}"
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Internal request helper (unchanged logic, uses internal exceptions)"""
        url = f"{self.base_url}{endpoint}"
        request_timeout = timeout if timeout is not None else self.request_timeout
        session = await self._get_session()
        try:
            logger.debug(
                f"Request: {method} {url} | Params: {params} | JSON: {json_data}"
            )
            async with session.request(
                method,
                url,
                params=params,
                json=json_data,
                timeout=aiohttp.ClientTimeout(total=request_timeout),
            ) as response:
                logger.debug(f"Response Status: {response.status} for {method} {url}")
                # Handle potential non-json responses better
                try:
                    response_data = await response.json()
                except aiohttp.ContentTypeError:
                    # If response is not JSON, use text
                    response_text = await response.text()
                    response_data = {
                        "detail": response_text
                    }  # Structure for error handling

                if response.status >= 400:
                    error_message = response_data.get("detail", "Unknown API error")
                    raise APIError(response.status, error_message)
                return response_data
        except aiohttp.ClientConnectorError as e:
            raise ConnectionError(f"Could not connect to {self.base_url}: {e}") from e
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {method} {url} after {request_timeout}s")
            raise  # Re-raise asyncio.TimeoutError, could wrap if needed
        except Exception as e:
            logger.exception(f"Unexpected error during request to {url}: {e}")
            raise Crawl4AIError(f"Unexpected error: {e}") from e

    # --- Interface Method Implementations ---

    async def check_health(self) -> Dict[str, Any]:
        """Checks the health of the Crawl4AI service."""
        try:
            # Crawl4AI /health doesn't require auth by default
            return await self._request("GET", "/health")
        except APIError as e:
            if e.status_code == 401 or e.status_code == 403:
                logger.warning(
                    "Auth error on /health endpoint. Service might be secured."
                )
                # Return minimal info, semaphore init handles default
                return {"status": "unauthorized_health_check"}
            raise  # Re-raise other API errors

    async def submit_scrape_job(
        self, urls: Union[str, List[str]], config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submits a Crawl4AI task using the /crawl endpoint.

        Args:
            urls: URL(s) to crawl.
            config: Dictionary mapping to Crawl4AI request payload fields
                    (e.g., 'priority', 'extraction_config', 'crawler_params', 'extra',
                     'js_code', 'wait_for', 'css_selector', 'screenshot', 'ttl').

        Returns:
            The Crawl4AI task ID.
        """
        if not self._initialized or not self._semaphore:
            raise Crawl4AIError(
                "Client not initialized. Use 'async with' context manager."
            )
        if config is None:
            config = {}

        # Construct the Crawl4AI payload from urls and config
        payload: Dict[str, Any] = {"urls": urls}
        payload.update(config)  # Merge config dict directly

        # Default priority if not in config
        if "priority" not in payload:
            payload["priority"] = 5  # Crawl4AI default seems to vary, let's set one

        # --- Rate Limiting ---
        logger.debug("Waiting for semaphore slot...")
        await self._semaphore.acquire()
        acquired_semaphore = True  # Flag to track if we acquired it
        busy_slots = self._semaphore_limit - self._semaphore._value
        logger.debug(
            f"Semaphore acquired. Current busy: {busy_slots}/{self._semaphore_limit}"
        )

        try:
            logger.info(f"Submitting crawl job (task) for: {urls}")
            response_data = await self._request("POST", "/crawl", json_data=payload)
            task_id = response_data.get("task_id")
            if not task_id:
                raise Crawl4AIError(
                    "Crawl4AI API did not return a task_id on submission."
                )
            logger.info(
                f"Job (task) submitted successfully. Job ID (Task ID): {task_id}"
            )
            # Semaphore released by get_scrape_result (wait_for_task_completion)
            acquired_semaphore = False  # Prevent release in finally block here
            return task_id
        finally:
            # Release semaphore ONLY if submission failed before waiting started
            if acquired_semaphore and self._semaphore:
                logger.error("Job submission failed, releasing semaphore immediately.")
                self._semaphore.release()

    async def get_scrape_result(
        self,
        job_id: str,  # job_id is the task_id for Crawl4AI
        timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Waits for a Crawl4AI task to complete and returns its result payload.

        Handles polling, timeouts, and failure cases. Releases the semaphore
        associated with this job upon completion/failure/timeout.

        Args:
            job_id: The Crawl4AI task ID.
            timeout: Max seconds to wait. Uses `self.default_job_timeout` if None.
            polling_interval: Seconds between status checks.
                                Uses `self.polling_interval` if None.

        Returns:
            The 'result' dictionary from the completed task status.

        Raises:
            JobTimeoutError: If the task times out.
            JobFailedError: If the task fails.
            ConnectionError, APIError, Crawl4AIError: For other errors.
        """
        if not self._semaphore:
            raise Crawl4AIError("Client not initialized correctly (no semaphore).")

        start_time = time.monotonic()
        wait_timeout = timeout if timeout is not None else self.default_job_timeout
        check_interval = (
            polling_interval if polling_interval is not None else self.polling_interval
        )
        task_id = job_id  # Use Crawl4AI terminology internally

        logger.info(f"Waiting for job {job_id} completion (timeout: {wait_timeout}s)")
        try:
            while True:
                elapsed_time = time.monotonic() - start_time
                if elapsed_time >= wait_timeout:
                    logger.error(
                        f"Timeout waiting for job {job_id} after {elapsed_time:.2f}s"
                    )
                    # Raise the interface-compatible exception
                    raise JobTimeoutError(
                        f"Job {job_id} did not complete within {wait_timeout}s"
                    )

                try:
                    # Use internal _request to fetch status
                    status_data = await self._request("GET", f"/task/{task_id}")
                    current_status = status_data.get("status")
                    logger.debug(f"Job {job_id} status: {current_status}")

                    if current_status == "completed":
                        logger.info(
                            f"Job {job_id} completed successfully after "
                            f"{elapsed_time:.2f}s."
                        )
                        # Return only the 'result' part as per interface contract
                        # (or adjust if needed)
                        return status_data.get("result", {})
                    elif current_status == "failed":
                        error_info = status_data.get(
                            "error", "No error details provided."
                        )
                        logger.error(
                            f"Job {job_id} failed after {elapsed_time:.2f}s. "
                            f"Error: {error_info}"
                        )
                        # Raise the interface-compatible exception
                        raise JobFailedError(job_id, error_info)
                    elif current_status in ["pending", "processing"]:
                        await asyncio.sleep(check_interval)
                    else:
                        logger.warning(
                            f"Job {job_id} reported unexpected status: {current_status}"
                        )
                        raise Crawl4AIError(
                            f"Job {job_id} has unexpected status: {current_status}"
                        )

                except (ConnectionError, APIError, JobFailedError, Crawl4AIError) as e:
                    # Catch errors during polling or failure detection
                    logger.error(f"Error while waiting for job {job_id}: {e}")
                    raise  # Propagate the error upwards

        finally:
            # --- Crucial: Release semaphore regardless of outcome ---
            if self._semaphore:
                self._semaphore.release()
                busy_slots = self._semaphore_limit - self._semaphore._value
                logger.debug(
                    f"Semaphore released for job {job_id}. Current busy: "
                    f"{busy_slots}/{self._semaphore_limit}"
                )

    async def scrape_and_wait(
        self,
        urls: Union[str, List[str]],
        config: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Submits a Crawl4AI job, waits for completion, and returns the result payload.
        """
        job_id = await self.submit_scrape_job(urls, config)
        # get_scrape_result handles waiting, exceptions, and semaphore release
        result_payload = await self.get_scrape_result(job_id, timeout, polling_interval)
        return result_payload

    # --- Optional: Keep Crawl4AI-specific helpers if desired ---
    # These are not part of the ScraperInterface but provide convenience for
    # Crawl4AI users

    async def crawl_simple(
        self,
        urls: Union[str, List[str]],
        priority: int = 5,
        task_timeout: Optional[float] = None,  # Use task_timeout for clarity here
        polling_interval: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Crawl4AI Specific Helper: Basic crawl, waits, returns result dict."""
        logger.warning(
            "Using Crawl4AI-specific helper 'crawl_simple'. Consider 'scrape_and_wait'."
        )
        config = {"priority": priority}
        return await self.scrape_and_wait(urls, config, task_timeout, polling_interval)

    async def submit_and_wait_full_status(
        self,
        crawl_request: Dict[str, Any],
        task_timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Crawl4AI Specific Helper: Submits using full request dict, waits,
        and returns the *entire final status dictionary* (status, result/error).
        """
        logger.warning(
            "Using Crawl4AI-specific helper 'submit_and_wait_full_status'. "
            "Consider 'scrape_and_wait'."
        )
        # This logic is slightly different from get_scrape_result as it returns the
        # full status We need to reimplement the waiting logic here
        # or call get_scrape_result and fetch status again (less efficient)
        # Let's reuse the waiting logic but return the full status at the end

        job_id = await self.submit_scrape_job(crawl_request.get("urls"), crawl_request)

        # Re-implement wait loop to get full status (similar to get_scrape_result)
        if not self._semaphore:
            raise Crawl4AIError("Client not initialized correctly (no semaphore).")

        start_time = time.monotonic()
        wait_timeout = (
            task_timeout if task_timeout is not None else self.default_job_timeout
        )
        check_interval = (
            polling_interval if polling_interval is not None else self.polling_interval
        )
        task_id = job_id

        logger.info(
            f"Waiting for job {job_id} completion (for full status) "
            f"(timeout: {wait_timeout}s)"
        )
        final_status_data = None
        try:
            while True:
                elapsed_time = time.monotonic() - start_time
                if elapsed_time >= wait_timeout:
                    logger.error(
                        f"Timeout waiting for job {job_id} after {elapsed_time:.2f}s"
                    )
                    raise JobTimeoutError(
                        f"Job {job_id} did not complete within {wait_timeout}s"
                    )

                try:
                    status_data = await self._request("GET", f"/task/{task_id}")
                    current_status = status_data.get("status")
                    logger.debug(f"Job {job_id} status: {current_status}")

                    if current_status == "completed":
                        logger.info(
                            f"Job {job_id} completed successfully after "
                            f"{elapsed_time:.2f}s."
                        )
                        final_status_data = status_data
                        break  # Exit loop
                    elif current_status == "failed":
                        error_info = status_data.get(
                            "error", "No error details provided."
                        )
                        logger.error(
                            f"Job {job_id} failed after {elapsed_time:.2f}s. "
                            f"Error: {error_info}"
                        )
                        final_status_data = status_data  # Store failed status
                        raise JobFailedError(job_id, error_info)  # Raise immediately
                    elif current_status in ["pending", "processing"]:
                        await asyncio.sleep(check_interval)
                    else:
                        logger.warning(
                            f"Job {job_id} reported unexpected status: {current_status}"
                        )
                        raise Crawl4AIError(
                            f"Job {job_id} has unexpected status: {current_status}"
                        )

                except (ConnectionError, APIError, JobFailedError, Crawl4AIError) as e:
                    logger.error(f"Error while waiting for job {job_id}: {e}")
                    # Try to get final status before re-raising if possible (might fail)
                    try:
                        final_status_data = await self._request(
                            "GET", f"/task/{task_id}"
                        )
                    except Exception:
                        pass  # Ignore errors getting final status here
                    raise  # Propagate the original error

            # Should only reach here on successful completion
            return final_status_data

        finally:
            # Release semaphore regardless of outcome
            if self._semaphore:
                self._semaphore.release()
                busy_slots = self._semaphore_limit - self._semaphore._value
                logger.debug(
                    f"Semaphore released for job {job_id}. Current busy: "
                    f"{busy_slots}/{self._semaphore_limit}"
                )
            # If an exception occurred and we have status data, return it?
            # No, exception should propagate.

    async def crawl_and_yield(
        self,
        crawl_request: Dict[str, Any],
        task_timeout: Optional[float] = None,
        polling_interval: Optional[float] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Crawl4AI Specific Helper: Submits, waits, yields result dict on success."""
        logger.warning("Using Crawl4AI-specific helper 'crawl_and_yield'.")
        # Use the interface method scrape_and_wait which handles submission and waiting
        # It raises JobFailedError on failure, so we only yield if it succeeds.
        result_payload = await self.scrape_and_wait(
            crawl_request.get("urls"), crawl_request, task_timeout, polling_interval
        )
        # If scrape_and_wait succeeded, result_payload contains the result
        yield result_payload
