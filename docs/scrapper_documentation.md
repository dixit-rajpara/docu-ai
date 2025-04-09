# Scraper Module Documentation

This document provides documentation for the generic `ScraperInterface`, the `ScraperFactory` used to create scraper instances, and the concrete implementation `AsyncCrawl4AIClient`.

## Table of Contents

1.  [Overview](#1-overview)
2.  [`scraper/interface.py`](#2-scraper/interfacepy)
    *   [`ScraperInterface`](#scraperinterface-abstract-base-class)
3.  [`scraper/factory.py`](#3-scraper/factorypy)
    *   [`ScraperFactory`](#scraperfactory-class)
4.  [`scraper/crawl4ai_client.py`](#4-crawl4ai_clientpy)
    *   [Exceptions](#exceptions)
    *   [`AsyncCrawl4AIClient`](#asynccrawl4aiclient-class)
5.  [Example Usage (with Factory)](#5-example-usage-with-factory)

---

## 1. Overview

This module provides a flexible and extensible system for asynchronous web scraping. It consists of:

*   **`ScraperInterface`**: An abstract base class defining a standard contract for scrapers.
*   **`ScraperFactory`**: A factory class responsible for creating specific scraper instances based on configuration (e.g., type string, environment variables).
*   **`AsyncCrawl4AIClient`**: A concrete implementation of `ScraperInterface` that interacts with a Crawl4AI service backend.

Using the factory and interface allows application code to remain decoupled from specific scraper implementations.

---

## 2. `scraper/interface.py`

This module defines the abstract base class (`ScraperInterface`) that outlines the contract for any asynchronous scraper client.

### `ScraperInterface` (Abstract Base Class)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

class ScraperInterface(ABC):
    # ... (methods defined below)
```

**Description:**

An abstract base class defining the standard methods required for an asynchronous web scraping client. Implementations of this interface should handle connecting to a scraping service, submitting jobs, monitoring their progress, and retrieving results.

**Methods:**

*   **`async def __aenter__(self) -> "ScraperInterface":`**
    *   **Description:** Asynchronous context manager entry point. Implementations should perform necessary setup, like initializing network connections or fetching initial configuration (e.g., rate limits).
    *   **Returns:** The initialized scraper instance (`self`).
    *   **Abstract:** Must be implemented by subclasses.

*   **`async def __aexit__(self, exc_type, exc_val, exc_tb):`**
    *   **Description:** Asynchronous context manager exit point. Implementations should perform necessary cleanup, such as closing network connections or releasing resources.
    *   **Parameters:**
        *   `exc_type`: Exception type if an exception occurred within the `async with` block.
        *   `exc_val`: Exception value.
        *   `exc_tb`: Exception traceback.
    *   **Abstract:** Must be implemented by subclasses.

*   **`async def check_health(self) -> Dict[str, Any]:`**
    *   **Description:** Checks the operational status or health of the underlying scraper service or backend.
    *   **Returns:** A dictionary containing status information. The exact structure is implementation-dependent but should indicate if the service is operational.
    *   **Abstract:** Must be implemented by subclasses.

*   **`async def submit_scrape_job(self, urls: Union[str, List[str]], config: Optional[Dict[str, Any]] = None) -> str:`**
    *   **Description:** Submits a new scraping job to the service for the given URL(s).
    *   **Parameters:**
        *   `urls`: A single URL string or a list of URL strings to be scraped.
        *   `config` (Optional): A dictionary containing configuration parameters specific to the scraping task and the backend implementation (e.g., extraction rules, rendering options, priorities, user agents). Defaults to `None`.
    *   **Returns:** A unique string identifier representing the submitted job (job ID).
    *   **Abstract:** Must be implemented by subclasses.

*   **`async def get_scrape_result(self, job_id: str, timeout: Optional[float] = None, polling_interval: Optional[float] = None) -> Dict[str, Any]:`**
    *   **Description:** Waits for a previously submitted scrape job to complete (successfully or with failure) and retrieves its results. Implementations typically involve polling the job status until a terminal state is reached or a timeout occurs.
    *   **Parameters:**
        *   `job_id`: The unique identifier of the job whose results are requested.
        *   `timeout` (Optional): The maximum time in seconds to wait for the job to complete. If `None`, the implementation should use a reasonable default.
        *   `polling_interval` (Optional): The interval in seconds between status checks if polling is used. If `None`, the implementation should use a reasonable default.
    *   **Returns:** A dictionary containing the results of the scrape job. The structure depends heavily on the specific job configuration and the scraper implementation (e.g., it might contain extracted text, structured data, screenshots).
    *   **Raises:**
        *   `JobTimeoutError`: If the job does not reach a terminal state within the specified `timeout`.
        *   `JobFailedError`: If the scraper service reports that the job failed during execution.
        *   Other implementation-specific exceptions (e.g., `ConnectionError`, `APIError`).
    *   **Abstract:** Must be implemented by subclasses.

*   **`async def scrape_and_wait(self, urls: Union[str, List[str]], config: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, polling_interval: Optional[float] = None) -> Dict[str, Any]:`**
    *   **Description:** A convenience method that combines submitting a job and waiting for its result. It calls `submit_scrape_job` followed by `get_scrape_result`.
    *   **Parameters:**
        *   `urls`: A single URL string or a list of URL strings to scrape.
        *   `config` (Optional): Configuration dictionary for the job.
        *   `timeout` (Optional): Maximum time in seconds to wait for completion.
        *   `polling_interval` (Optional): Interval in seconds for status checks if polling.
    *   **Returns:** A dictionary containing the results of the scrape job, identical to the return value of `get_scrape_result`.
    *   **Raises:** Exceptions raised by `submit_scrape_job` or `get_scrape_result`.
    *   **Abstract:** Must be implemented by subclasses.

---

## 3. `scraper/factory.py`

This module provides a factory class to centralize the creation of scraper instances that implement the `ScraperInterface`. It decouples the application logic from specific scraper implementations.

### `ScraperFactory` (Class)

```python
import os
from typing import Dict, Any, Optional

from scraper_interface import ScraperInterface
from crawl4ai_client import AsyncCrawl4AIClient
# from other_scraper import OtherScraper # Example

class ScraperFactory:
    # ... (methods defined below)
```

**Description:**

A factory class responsible for instantiating concrete scraper objects based on provided type information and configuration. It allows creating different scraper backends (like `AsyncCrawl4AIClient`) through a unified interface.

**Static Methods:**

*   **`create_scraper(scraper_type: str, config: Optional[Dict[str, Any]] = None) -> ScraperInterface:`**
    *   **Description:** Creates and returns a scraper instance of the specified type, configured using the provided dictionary.
    *   **Parameters:**
        *   `scraper_type` (str): A string identifying the type of scraper to create (e.g., `'crawl4ai'`, `'local_bs4'`). Case-insensitive.
        *   `config` (Optional\[Dict\[str, Any]]): A dictionary containing configuration key-value pairs necessary for initializing the chosen scraper type. Required keys depend on the implementation (e.g., `base_url`, `api_token` for `crawl4ai`).
    *   **Returns:** An initialized instance of a class that implements `ScraperInterface`.
    *   **Raises:**
        *   `ValueError`: If `scraper_type` is not recognized or if required configuration keys are missing in the `config` dictionary for the requested type.

*   **`create_scraper_from_env(default_type: str = 'crawl4ai') -> ScraperInterface:`**
    *   **Description:** Creates and returns a scraper instance based on configuration loaded from environment variables. This method determines the scraper type and its settings by reading predefined environment variables.
    *   **Parameters:**
        *   `default_type` (str): The scraper type identifier to use if the `SCRAPER_TYPE` environment variable is not set. Defaults to `'crawl4ai'`.
    *   **Environment Variables Read (Example for `crawl4ai`):**
        *   `SCRAPER_TYPE`: Specifies the type (e.g., `'crawl4ai'`). Uses `default_type` if not set.
        *   `CRAWL4AI_BASE_URL`: The base URL for the Crawl4AI service.
        *   `CRAWL4AI_API_TOKEN`: The API token for authentication.
        *   `CRAWL4AI_POLLING_INTERVAL`: (Optional) Polling interval override.
        *   `CRAWL4AI_REQUEST_TIMEOUT`: (Optional) Request timeout override.
        *   `CRAWL4AI_JOB_TIMEOUT`: (Optional) Default job timeout override.
        *   `CRAWL4AI_MAX_CONCURRENT`: (Optional) Max concurrent jobs override.
        *   *(Note: The factory needs to be updated if other scraper types reading different environment variables are added.)*
    *   **Returns:** An initialized instance of a class that implements `ScraperInterface`.
    *   **Raises:**
        *   `ValueError`: If the configuration derived from environment variables is invalid (e.g., unknown type, missing required values for the determined type, invalid numeric values).

---

## 4. `scraper/crawl4ai_client.py`

This module provides a concrete implementation of the `ScraperInterface` using the Crawl4AI service. It handles communication with a running Crawl4AI instance.

### Exceptions

*   **`Crawl4AIError(Exception)`**: Base class for errors specific to this client.
*   **`ConnectionError(Crawl4AIError)`**: Raised when the client fails to connect to the Crawl4AI service URL.
*   **`APIError(Crawl4AIError)`**: Raised when the Crawl4AI API returns an HTTP error status code (>= 400). Contains `status_code` and `message` attributes.
*   **`JobTimeoutError(Crawl4AIError)`**: Raised when waiting for a Crawl4AI task (`job`) to complete exceeds the specified timeout. Inherits from `Crawl4AIError`.
*   **`JobFailedError(Crawl4AIError)`**: Raised when a Crawl4AI task (`job`) finishes with a 'failed' status. Contains `job_id` and `error_info` attributes. Inherits from `Crawl4AIError`.

### `AsyncCrawl4AIClient` (Class)

```python
# Inherits from ScraperInterface
class AsyncCrawl4AIClient(ScraperInterface):
    # ... (constants and methods defined below)
```

**Description:**

An asynchronous Python client for interacting with a Crawl4AI service backend. It implements the `ScraperInterface`, providing methods to submit crawl tasks, check status, and retrieve results, while handling rate limiting and optional API token authentication. Typically instantiated via the `ScraperFactory`.

**Constants:**

*   `DEFAULT_BASE_URL`: Default URL for the Crawl4AI service (`"http://localhost:11235"`).
*   `DEFAULT_POLLING_INTERVAL`: Default time in seconds between task status checks (`2.0`).
*   `DEFAULT_REQUEST_TIMEOUT`: Default timeout in seconds for individual HTTP requests (`60.0`).
*   `DEFAULT_JOB_TIMEOUT`: Default timeout in seconds for waiting for a job (task) to complete (`300.0`).

**Initialization (`__init__`)**

```python
def __init__(
    self,
    base_url: str = DEFAULT_BASE_URL,
    api_token: Optional[str] = None,
    # ... other parameters ...
):
    # ... implementation ...
```

*   **Parameters:** (See `ScraperFactory.create_scraper` for how these are typically passed via the `config` dict).
    *   `base_url` (str): The base URL of the running Crawl4AI service.
    *   `api_token` (Optional\[str]): API token for authentication.
    *   `polling_interval` (float): Default polling interval.
    *   `request_timeout` (float): Default timeout for HTTP requests.
    *   `default_job_timeout` (float): Default timeout for job completion.
    *   `max_concurrent_jobs_override` (Optional\[int]): Override for concurrent task limit.
    *   `session` (Optional\[aiohttp.ClientSession]): Optional external `aiohttp` session.

**Interface Methods Implementation:**

*   **`async def __aenter__(self) -> "AsyncCrawl4AIClient":`**
    *   Initializes the `aiohttp` session and the rate-limiting semaphore based on `/health` check or override.

*   **`async def __aexit__(self, exc_type, exc_val, exc_tb):`**
    *   Closes the internally managed `aiohttp` session.

*   **`async def check_health(self) -> Dict[str, Any]:`**
    *   Calls the Crawl4AI `/health` endpoint.

*   **`async def submit_scrape_job(self, urls: Union[str, List[str]], config: Optional[Dict[str, Any]] = None) -> str:`**
    *   Acquires semaphore, calls the Crawl4AI `/crawl` endpoint with `urls` and parameters extracted from `config`.
    *   Returns the `task_id`. Semaphore released upon job completion via `get_scrape_result`.

*   **`async def get_scrape_result(self, job_id: str, timeout: Optional[float] = None, polling_interval: Optional[float] = None) -> Dict[str, Any]:`**
    *   Polls the Crawl4AI `/task/{job_id}` endpoint. Releases semaphore.
    *   Returns the `result` dictionary on success. Raises `JobTimeoutError` or `JobFailedError` otherwise.

*   **`async def scrape_and_wait(self, urls: Union[str, List[str]], config: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, polling_interval: Optional[float] = None) -> Dict[str, Any]:`**
    *   Combines `submit_scrape_job` and `get_scrape_result`.

**Crawl4AI-Specific Helper Methods (Not part of `ScraperInterface`):**

*   These methods (`crawl_simple`, `submit_and_wait_full_status`, `crawl_and_yield`) provide convenient ways to interact specifically with the Crawl4AI client, sometimes offering slightly different return values (like full status) than the generic interface methods. Use them if you need Crawl4AI-specific behavior and aren't concerned about strict interface adherence in that part of your code. *(See source code for details)*.

---

## 5. Example Usage (with Factory)

```python
import asyncio
import os
from scraper_factory import ScraperFactory
from scraper_interface import ScraperInterface # Use interface type hint

async def main():
    # Recommended: Create scraper using the factory, potentially from environment variables
    # Example: Set environment variables before running if needed
    # os.environ['SCRAPER_TYPE'] = 'crawl4ai'
    # os.environ['CRAWL4AI_BASE_URL'] = 'http://localhost:11235'
    # os.environ['CRAWL4AI_API_TOKEN'] = 'your_secret_token_here' # Optional

    try:
        scraper: ScraperInterface = ScraperFactory.create_scraper_from_env()

        # Use the scraper via the interface methods
        async with scraper:
            print("Checking health...")
            health = await scraper.check_health()
            print(f"Scraper health: {health}")

            print("\nSubmitting simple scrape job...")
            urls_to_scrape = "https://httpbin.org/html"
            # Pass any config specific to the scraper type (crawl4ai needs none for basic)
            result = await scraper.scrape_and_wait(urls_to_scrape, config={})
            print(f"Scrape successful! Result keys: {result.keys()}")
            # print(f"Markdown Content:\n{result.get('markdown', '')[:200]}...") # Print snippet

            print("\nSubmitting job with config...")
            adv_urls = "https://news.ycombinator.com/"
            adv_config = {
                "priority": 7, # Crawl4AI specific config
                "crawler_params": { "page_timeout": 15000 }, # Crawl4AI specific config
                "extra": { "word_count_threshold": 5 } # Crawl4AI specific config
            }
            adv_result = await scraper.scrape_and_wait(adv_urls, config=adv_config, timeout=30.0)
            print(f"Advanced scrape successful! Result keys: {adv_result.keys()}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

This structure allows for easy extension with new scraper types while keeping the core application logic consistent.