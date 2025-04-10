-- Ensure the pgvector extension is enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Table to store information about the data sources being processed
CREATE TABLE data_sources (
    source_id SERIAL PRIMARY KEY,           -- Unique identifier for the data source
    name TEXT NOT NULL UNIQUE,              -- Human-readable name (e.g., 'Python 3.12 Docs', 'Project Wiki')
    base_url TEXT UNIQUE,                   -- Base URL of the source (e.g., 'https://docs.python.org/3/'), can be NULL if not URL-based
    identifier VARCHAR(100),                -- Optional identifier (e.g., version '3.12.4', dataset name), nullable
    last_processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- When this source was last processed
    metadata JSONB                          -- Store extra info (e.g., scraping config, source type details)
);

COMMENT ON TABLE data_sources IS 'Stores metadata about distinct sources of data being processed (e.g., a specific website, a dataset).';
COMMENT ON COLUMN data_sources.name IS 'Unique human-readable name for the data source.';
COMMENT ON COLUMN data_sources.base_url IS 'The root URL if the source is web-based.';
COMMENT ON COLUMN data_sources.identifier IS 'An optional string identifier, like a version number or dataset tag.';
COMMENT ON COLUMN data_sources.last_processed_at IS 'Timestamp of the last successful processing run for this entire source.';
COMMENT ON COLUMN data_sources.metadata IS 'Flexible JSON field for additional source-level metadata (type, credentials, config).';


-- Table to store information about individual documents/items retrieved from a source
CREATE TABLE documents (
    document_id SERIAL PRIMARY KEY,         -- Unique identifier for the document/item
    source_id INTEGER NOT NULL REFERENCES data_sources(source_id) ON DELETE CASCADE, -- Link to the data source
    url TEXT NOT NULL,                      -- The specific URL or unique identifier of the retrieved item within the source
    title TEXT,                             -- Title of the document (often from <title> or <h1>, or filename)
    last_modified TIMESTAMPTZ,              -- Last-Modified timestamp from source, if available
    processed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- When this specific document was processed/retrieved
    content_hash VARCHAR(64),               -- Optional: SHA-256 hash of the raw content to detect changes
    metadata JSONB                          -- Item-specific metadata (e.g., language, content type, author)
);

-- Add index for faster lookups by URL/identifier within a source
CREATE INDEX idx_documents_source_url ON documents(source_id, url);
-- Add index on foreign key for better join performance
CREATE INDEX idx_documents_source_id ON documents(source_id);

COMMENT ON TABLE documents IS 'Represents individual items (pages, files, records) retrieved from a data source.';
COMMENT ON COLUMN documents.source_id IS 'Foreign key linking to the data_sources table.';
COMMENT ON COLUMN documents.url IS 'The unique locator (e.g., URL, file path, record ID) of the item within its source.';
COMMENT ON COLUMN documents.title IS 'The extracted title or name of the item.';
COMMENT ON COLUMN documents.last_modified IS 'Timestamp indicating when the item content was last modified at the source.';
COMMENT ON COLUMN documents.processed_at IS 'Timestamp indicating when this specific item was successfully retrieved/processed.';
COMMENT ON COLUMN documents.content_hash IS 'Optional SHA-256 hash of the raw item content to quickly check for modifications.';
COMMENT ON COLUMN documents.metadata IS 'Flexible JSON field for additional document-level metadata.';


-- Table to store the text chunks and their vector embeddings
CREATE TABLE document_chunks (
    chunk_id BIGSERIAL PRIMARY KEY,         -- Unique identifier for the chunk (use BIGSERIAL for potentially many chunks)
    document_id INTEGER NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE, -- Link to the parent document/item
    chunk_text TEXT NOT NULL,               -- The actual text content of the chunk
    chunk_order INTEGER NOT NULL,           -- The sequential order of this chunk within the document (0, 1, 2...)
    embedding VECTOR(1536),                 -- The vector embedding for this chunk. ADJUST 1536 TO YOUR MODEL'S DIMENSION!
    embedding_model VARCHAR(100),           -- Identifier for the model used to generate the embedding (e.g., 'text-embedding-ada-002')
    token_count INTEGER,                    -- Optional: Number of tokens in the chunk (useful for context limits)
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP, -- When the chunk record was created
    metadata JSONB                          -- Chunk-specific metadata (e.g., source tags, section headings, positional info)
);

-- Add index on foreign key for better join performance
CREATE INDEX idx_document_chunks_document_id ON document_chunks(document_id);

-- !! CRITICAL INDEX FOR VECTOR SEARCH !!
-- Choose ONE appropriate index type based on your expected usage and data size.
-- HNSW is generally a good default for high performance and recall.
-- Replace 'vector_cosine_ops' with 'vector_l2_ops' (Euclidean) or 'vector_ip_ops' (Inner Product)
-- if your embedding model and similarity metric require it. Cosine is common for text embeddings.
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Alternatively, for IVFFlat (might be better for very large datasets, requires tuning):
-- CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100); -- Adjust 'lists' based on dataset size

COMMENT ON TABLE document_chunks IS 'Stores text chunks extracted from documents/items and their corresponding vector embeddings.';
COMMENT ON COLUMN document_chunks.document_id IS 'Foreign key linking to the documents table.';
COMMENT ON COLUMN document_chunks.chunk_text IS 'The actual text content of the chunk.';
COMMENT ON COLUMN document_chunks.chunk_order IS 'The 0-based index representing the sequence of this chunk within its parent document.';
COMMENT ON COLUMN document_chunks.embedding IS 'The vector embedding generated for the chunk_text. Dimension must match the embedding model.';
COMMENT ON COLUMN document_chunks.embedding_model IS 'Name/identifier of the embedding model used (e.g., text-embedding-ada-002).';
COMMENT ON COLUMN document_chunks.token_count IS 'Optional count of tokens for this chunk, useful for context window management.';
COMMENT ON COLUMN document_chunks.created_at IS 'Timestamp indicating when this chunk record was inserted.';
COMMENT ON COLUMN document_chunks.metadata IS 'Flexible JSON field for additional chunk-level metadata (e.g., originating element/path, section info).';