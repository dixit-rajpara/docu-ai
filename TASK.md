# Project Tasks: Documentation Scraper with Vector DB & MCP Server

## 🚧 Phase 1: Project Setup

### 1. Initialize Python Project
- [x] Set up virtual environment
- [x] Create `pyproject.toml` with dependencies
- [x] Install base dependencies
- [x] Set up basic project structure with src/ and tests/ directories
- [x] Create configuration management system with pydantic-settings

### 2. Set Up Docker Environment
- [x] Create docker/ directory structure
- [ ] Write a `Dockerfile` for the Python app
- [ ] Create `docker-compose.yml` for:
  - App container
  - PostgreSQL with pgvector
- [x] Add `.env` support for secrets/configuration

---

## 🔸 Phase 2: Documentation Scraper

### 3. Web Scraper Module
- [x] Create basic scraper module structure
- [x] Set up initial test framework for scraper
- [x] Input: Framework docs base URL
- [x] Output: List of (URL, cleaned HTML/text) pairs
- [x] Add crawling limits, deduplication, retries
- [x] Implement Crawl4AI client with rate limiting
- [x] Add sitemap discovery and parsing
- [x] Add link crawling capabilities

### 4. Text Processing Module
- [x] Create processing module structure
- [ ] Strip unwanted HTML tags
- [ ] Normalize whitespace
- [ ] Preserve heading hierarchy for chunking
- [ ] Add support for code block preservation
- [ ] Implement metadata extraction

---

## 🧠 Phase 3: Chunking & Embedding

### 5. Chunking Module
- [x] Create ingestion pipeline structure
- [ ] Split docs by heading/semantic boundary
- [ ] Implement token-aware chunking
- [ ] Add overlap configuration
- [ ] Preserve metadata in chunks
- [ ] Add chunk validation

### 6. Embedding Module
- [x] Set up multiple embedding providers
- [x] Implement OpenAI embeddings
- [x] Add SentenceTransformers support
- [x] Add Ollama integration
- [ ] Add embedding caching
- [ ] Implement batch processing
- [ ] Add fallback mechanisms

---

## 🗃️ Phase 4: Vector DB Integration

### 7. PostgreSQL with pgvector
- [x] Initial database module setup
- [x] Create schema: `documents`, `chunks`, `vectors`
- [x] Enable extension: `CREATE EXTENSION vector;`
- [x] Write script to insert metadata + embeddings
- [x] Implement async SQLAlchemy models
- [x] Add proper indexing and constraints
- [x] Implement bulk document chunk insertion
- [x] Add HNSW indexing for vector similarity search
- [x] Set up Alembic migrations
- [x] Create initial migration script
- [ ] Add database health check endpoint
- [ ] Add monitoring for query performance

### 8. Similarity Search
- [x] SQL query for top-k similar vectors
- [x] Add filtering support (by doc/meta)
- [x] Implement cosine similarity search
- [ ] Add support for other distance metrics
- [ ] Implement caching for frequent queries
- [ ] Add pagination support for search results
- [ ] Add hybrid search capabilities

---

## 🧰 Phase 5: LLM Integration

### 9. LLM Module
- [x] Set up LLM module structure
- [x] Implement litellm integration
- [x] Add OpenAI support
- [x] Add Ollama integration
- [ ] Implement response streaming
- [ ] Add response caching
- [ ] Implement fallback mechanisms
- [ ] Add cost tracking

### 10. MCP Server Integration
- [ ] Set up FastAPI server structure
- [ ] Implement health check endpoints
- [ ] Add documentation search endpoints
- [ ] Add streaming response support
- [ ] Implement rate limiting
- [ ] Add authentication/authorization

---

## 🧪 Phase 6: Testing & Developer Experience

### 11. Testing
- [x] Set up pytest framework
- [x] Add initial test cases for scraper module
- [x] Add tests for processing module
- [ ] Add tests for embedding module
- [ ] Add tests for LLM module
- [ ] Add integration tests
- [ ] Add performance tests

### 12. Documentation
- [x] Write initial README with setup instructions
- [ ] Add API documentation
- [ ] Add developer guide
- [ ] Add deployment guide
- [ ] Add architecture diagrams
- [ ] Document configuration options

### 13. Monitoring & Observability
- [x] Set up logging directory and configuration
- [x] Add structured logging across modules
- [x] Add error handling and reporting
- [ ] Set up metrics collection
- [ ] Add performance monitoring
- [ ] Implement cost tracking
- [ ] Add usage analytics

### Discovered During Work
- [x] Add rate limiting for web scraping
- [x] Add support for multiple embedding providers
- [x] Create database migration system
- [ ] Add database backup/restore scripts
- [ ] Add migration testing
- [ ] Create database seeding scripts
- [ ] Add support for batch operations
- [ ] Implement document versioning
- [ ] Add support for incremental updates
- [ ] Implement document expiration
- [ ] Add support for custom chunking strategies
