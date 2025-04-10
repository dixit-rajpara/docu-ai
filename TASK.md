# Project Tasks: Documentation Scraper with Vector DB & MCP Server

## 🚧 Phase 1: Project Setup

### 1. Initialize Python Project
- [x] Set up virtual environment
- [x] Create `requirements.txt` or `pyproject.toml`
- [x] Install base dependencies: `requests`, `beautifulsoup4`, `openai`, `langchain`, etc.
- [x] Set up basic project structure with src/ and tests/ directories
- [x] Create configuration management system

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

### 4. Text Cleaner Module
- [ ] Strip unwanted HTML tags
- [ ] Normalize whitespace
- [ ] Preserve heading hierarchy for chunking

---

## 🧠 Phase 3: Chunking & Embedding

### 5. Chunking Module
- [ ] Split docs by heading/semantic boundary
- [ ] Limit to max token length (e.g., 512 tokens)

### 6. Embedding Module
- [ ] Generate vector embeddings (OpenAI or HuggingFace)
- [ ] Normalize and store vector representations

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
- [ ] Add support for other distance metrics (L2, inner product)
- [ ] Implement caching for frequent queries
- [ ] Add pagination support for search results

---

## 🧰 Phase 5: API Server (MCP)

### 9. FastMCP Server
- [ ] Set up FastAPI server structure
- [ ] Implement basic health check endpoints
- [ ] Add documentation search endpoints

### 10. (Optional) LLM Response Generation
- [ ] Use OpenAI or local LLM to synthesize answers
- [ ] Add response caching mechanism

---

## 🧪 Phase 6: Testing & Developer Experience

### 11. Testing
- [x] Set up pytest framework
- [x] Add initial test cases for scraper module
- [ ] Add unit tests for each remaining module
- [ ] Add integration tests

### 12. CLI Interface
- [x] Set up basic CLI structure
- [ ] Add command for running scraper
- [ ] Add command for search operations
- [ ] Add utility commands (db setup, etc.)

### 13. Logging/Error Handling
- [x] Set up logging directory and basic configuration
- [x] Add structured logging across all modules
- [x] Add try/except error handling across modules
- [ ] Add error reporting and monitoring

### 14. Documentation
- [x] Write initial README with setup instructions
- [ ] Add API documentation
- [ ] Add developer guide
- [ ] Add deployment guide

### Discovered During Work
- [x] Add rate limiting for web scraping
- [ ] Implement caching mechanism for scraped content
- [ ] Add support for multiple embedding providers
- [x] Create database migration system using Alembic
- [ ] Add database health check endpoint
- [ ] Create database backup/restore scripts
- [ ] Add monitoring for query performance
- [ ] Implement rate limiting for vector searches
- [ ] Add support for batch vector operations
- [ ] Add migration testing to CI/CD pipeline
- [ ] Create database seeding scripts
- [ ] Add migration rollback procedures
