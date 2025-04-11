import asyncio
import time

from config.logger import get_logger
from scraper.factory import ScraperFactory
from scraper.interface import ScraperInterface

# --- Use existing discovery module ---
from scraper.discovery import get_site_urls

# ------------------------------------
from scraper.utils import html_to_clean_markdown
from processing.chunking import (
    chunk_markdown,
    DEFAULT_OVERLAP_SIZE,
)  # Import overlap default
from processing.metadata import generate_document_metadata, generate_chunk_metadata
from llm.embedding import (
    create_embedding_client,
    AbstractEmbeddingClient,
    EmbeddingError,
    calculate_token_count,
)
from llm.completion import (
    create_completion_client,
    AbstractCompletionClient as AbstractCompletionLLMClient,
    CompletionError,
)
from db import PostgresDBRepository

logger = get_logger(__name__)

# --- Configuration ---
SCRAPE_CONCURRENCY = 10
CHUNK_PROCESSING_CONCURRENCY = 20
# Add chunking config here or pass from CLI later
CHUNK_OVERLAP = DEFAULT_OVERLAP_SIZE  # Use the default from chunking module


async def process_single_url(
    url: str,
    source_id: int,
    scraper: ScraperInterface,
    db_repo: PostgresDBRepository,
    llm_completion: AbstractCompletionLLMClient,
    llm_embedding: AbstractEmbeddingClient,
) -> bool:
    """Processes a single URL: scrape, clean, enrich, chunk, embed, store."""
    logger.info(f"[Doc:{url[:60]}...] Starting processing.")
    start_time = time.monotonic()

    try:
        # --- Check if document already exists ---
        existing_doc = await db_repo.get_document_by_url(source_id=source_id, url=url)
        if existing_doc:
            # For now, skip processing if document URL already exists in this source.
            # Add hash comparison later for re-processing changed content.
            logger.info(
                f"[Doc:{url[:60]}...] Document already exists "
                f"(ID: {existing_doc.document_id}). Skipping."
            )
            return True  # Consider this URL "processed" as it exists
        # ---------------------------------------

        # 1. Scrape URL
        logger.debug(f"[Doc:{url[:60]}...] Scraping content...")
        scrape_result = await scraper.scrape_and_wait(url, config={}, timeout=60.0)
        if (
            not scrape_result
            or "html" not in scrape_result
            or not scrape_result["html"]
        ):
            logger.warning(
                f"[Doc:{url[:60]}...] Scraping failed or returned no HTML content."
            )
            return False
        html_content = scrape_result["html"]
        page_title = scrape_result.get("title")

        # 2. Clean HTML to Markdown
        logger.debug(f"[Doc:{url[:60]}...] Cleaning HTML and converting to Markdown...")
        markdown_content = html_to_clean_markdown(html_content)
        if not markdown_content.strip():
            logger.warning(f"[Doc:{url[:60]}...] Content became empty after cleaning.")
            return False

        # 3. Generate Document Metadata
        logger.debug(f"[Doc:{url[:60]}...] Generating document metadata via LLM...")
        doc_metadata = await generate_document_metadata(
            markdown_content, llm_completion
        )
        doc_title = doc_metadata.get("title") if doc_metadata else None
        doc_summary = doc_metadata.get("summary") if doc_metadata else None
        doc_title = doc_title or page_title
        logger.info(
            f"[Doc:{url[:60]}...] Doc Title='{doc_title}', "
            f"Summary='{doc_summary[:50] if doc_summary else 'N/A'}...'"
        )

        # 4. Add Document to DB
        logger.debug(f"[Doc:{url[:60]}...] Storing new document record...")

        document = await db_repo.add_document(
            source_id=source_id,
            url=url,
            title=doc_title,
            summary=doc_summary,
            markdown_content=markdown_content,
            content_hash=None,  # TODO: Calculate hash
            metadata_={"scraper_title": page_title} if page_title else None,
        )
        doc_id = document.document_id

        # Delete existing chunks before adding new ones to handle updates
        logger.debug(
            f"[Doc:{url[:60]}...] Deleting existing chunks for document ID "
            f"{doc_id} before adding new ones."
        )
        await db_repo.delete_chunks_by_document(
            doc_id
        )  # Need to add this method to repo

        # 5. Chunk Markdown Document (with overlap)
        logger.debug(
            f"[Doc:{url[:60]}...] Chunking Markdown content with "
            f"overlap {CHUNK_OVERLAP}..."
        )
        chunks = chunk_markdown(
            markdown_content, overlap_size=CHUNK_OVERLAP
        )  # Pass overlap
        if not chunks:
            logger.warning(f"[Doc:{url[:60]}...] No chunks generated from content.")
            return True  # Document exists or was added, but no chunks

        # 6. Process Chunks (Metadata + Embedding)
        # (Rest of the logic for processing chunks remains largely the same as before)
        logger.info(
            f"[Doc:{url[:60]}...] Processing {len(chunks)} chunks concurrently "
            f"(batch size: {CHUNK_PROCESSING_CONCURRENCY})..."
        )
        processed_chunk_data = []
        tasks = []
        chunk_texts_for_embedding = [chunk["text"] for chunk in chunks]

        chunk_embeddings = await llm_embedding.generate_embeddings(
            chunk_texts_for_embedding
        )
        if chunk_embeddings is None or len(chunk_embeddings) != len(
            chunks
        ):  # Basic check, might need refinement if provider skips
            logger.error(
                f"[Doc:{url[:60]}...] Failed to generate embeddings or "
                "embedding count mismatch."
            )
            return False

        async def _process_single_chunk(chunk_dict, embedding):
            # (Code inside _process_single_chunk remains the same as previous version)
            chunk_text = chunk_dict["text"]
            chunk_order = chunk_dict["order"]
            logger.debug(
                f"[Doc:{url[:60]}... Chunk:{chunk_order}] Generating metadata..."
            )
            metadata = await generate_chunk_metadata(chunk_text, llm_completion)
            token_count = calculate_token_count(chunk_text)
            return {
                "document_id": doc_id,
                "chunk_text": chunk_text,
                "chunk_order": chunk_order,
                "title": metadata.get("title") if metadata else None,
                "summary": metadata.get("summary") if metadata else None,
                "embedding": embedding,
                "embedding_model": llm_embedding.get_model_name(),
                "token_count": token_count,
                "metadata_": None,
            }

        # Create tasks only for chunks that got an embedding
        embedding_idx = 0
        for chunk_data in chunks:
            if (
                embedding_idx < len(chunk_embeddings)
                and chunk_embeddings[embedding_idx] is not None
            ):
                tasks.append(
                    _process_single_chunk(chunk_data, chunk_embeddings[embedding_idx])
                )
                embedding_idx += 1
            else:
                logger.warning(
                    f"[Doc:{url[:60]}... Chunk:{chunk_data['order']}] Skipping "
                    "processing due to missing embedding."
                )
                # Ensure embedding_idx still advances if the embedding list truly is
                # shorter
                if embedding_idx < len(chunk_embeddings):
                    embedding_idx += 1

        # Run metadata generation tasks concurrently
        results = []
        for i in range(0, len(tasks), CHUNK_PROCESSING_CONCURRENCY):
            batch = tasks[i : i + CHUNK_PROCESSING_CONCURRENCY]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)

        # Filter out errors and collect valid chunk data
        task_idx = 0
        for res in results:
            # Retrieve original chunk order reliably if needed (more complex)
            # For now, assume order corresponds to successful tasks
            if isinstance(res, Exception):
                logger.error(
                    f"[Doc:{url[:60]}...] Failed to process a chunk task: {res}"
                )
            elif res:
                processed_chunk_data.append(res)
            task_idx += 1

        # 7. Ingest Chunks into DB
        if processed_chunk_data:
            logger.debug(
                f"[Doc:{url[:60]}...] Storing {len(processed_chunk_data)} "
                "processed chunks..."
            )
            try:
                await db_repo.add_document_chunks(processed_chunk_data)
            except Exception as db_err:
                logger.error(
                    f"[Doc:{url[:60]}...] Failed to store chunks in DB: {db_err}",
                    exc_info=True,
                )
                return False
        else:
            logger.warning(f"[Doc:{url[:60]}...] No valid processed chunks to store.")

        duration = time.monotonic() - start_time
        logger.info(
            f"[Doc:{url[:60]}...] Processing completed successfully in {duration:.2f}s."
        )
        return True

    # --- Keep the rest of the exception handling as before ---
    except (CompletionError, EmbeddingError) as llm_err:
        logger.error(
            f"[Doc:{url[:60]}...] Pipeline error (LLM): {llm_err}", exc_info=True
        )
        return False
    except Exception as e:
        logger.exception(f"[Doc:{url[:60]}...] Unexpected error during processing: {e}")
        return False


async def process_data_source(
    source_url: str,
    db_repo: PostgresDBRepository,
):
    """
    Main pipeline to process a data source: discover, scrape, process, ingest.
    """
    logger.info(f"Starting ingestion pipeline for data source: {source_url}")
    start_time_all = time.monotonic()

    scraper = ScraperFactory.create_scraper()
    llm_completion = create_completion_client()
    llm_embedding = create_embedding_client()

    processed_count = 0
    failed_count = 0
    total_urls = 0
    urls_to_process = []  # Initialize

    try:
        # 1. Discover URLs (using get_site_urls with fallback)
        logger.info(
            f"Discovering URLs for {source_url} "
            "(sitemap preferred, fallback to crawl)..."
        )
        # Set fallback depth or use default from get_site_urls if desired
        urls_to_process = await get_site_urls(source_url, fallback_max_depth=1)
        total_urls = len(urls_to_process)

        if not urls_to_process:
            logger.error(
                f"Pipeline failed: Could not discover any URLs for {source_url} "
                "using sitemap or link crawling."
            )
            return  # Stop processing if no URLs found

        logger.info(f"Found {total_urls} URLs to process.")

        # 2. Get or Create DataSource in DB
        source_name = f"Source: {source_url}"
        data_source = await db_repo.get_or_create_data_source(
            name=source_name, base_url=source_url
        )
        source_id = data_source.source_id
        logger.info(f"Using DataSource ID: {source_id} for '{source_name}'")

        # --- Optional: Clear previous data for this source? ---
        # logger.warning(f"Deleting existing documents and chunks for source ID
        # {source_id} before processing...")
        # deleted_doc_count = await db_repo.delete_documents_by_source(source_id)
        # logger.info(f"Deleted {deleted_doc_count} existing documents.")
        # ----------------------------------------------------

        # 3. Process URLs Concurrently
        logger.info(
            f"Processing {total_urls} URLs with concurrency {SCRAPE_CONCURRENCY}..."
        )
        tasks = []
        async with scraper:
            semaphore = asyncio.Semaphore(SCRAPE_CONCURRENCY)

            async def _scrape_with_semaphore(url):
                async with semaphore:
                    return await process_single_url(
                        url, source_id, scraper, db_repo, llm_completion, llm_embedding
                    )

            for url in urls_to_process:
                tasks.append(_scrape_with_semaphore(url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Tally results
        for i, res in enumerate(results):
            url = urls_to_process[i]
            if isinstance(res, Exception):
                logger.error(
                    f"Task for URL {url} failed unexpectedly: {res}", exc_info=res
                )
                failed_count += 1
            elif res is True:
                processed_count += 1
            else:  # res is False
                logger.warning(f"Processing flagged as failed for URL: {url}")
                failed_count += 1

        # 4. Update DataSource timestamp
        await db_repo.update_data_source_processed_time(source_id)

    except Exception as e:
        logger.critical(
            f"Critical error during pipeline execution for {source_url}: {e}",
            exc_info=True,
        )
    finally:
        duration_all = time.monotonic() - start_time_all
        logger.info(
            f"Ingestion pipeline finished for {source_url} in {duration_all:.2f}s."
        )
        logger.info(
            f"Summary: Total URLs Attempted={total_urls}, "
            f"Successfully Processed={processed_count}, Failed/Skipped={failed_count}"
        )
