# Project Tasks: Documentation Scraper with Vector DB & MCP Server

## 🚧 Phase 1: Project Setup

### 1. Initialize Python Project
- [x] Set up virtual environment
- [x] Create `requirements.txt` or `pyproject.toml`
- [x] Install base dependencies: `requests`, `beautifulsoup4`, `openai`, `langchain`, etc.

### 2. Set Up Docker Environment
- [ ] Write a `Dockerfile` for the Python app
- [ ] Create `docker-compose.yml` for:
  - App container
- [ ] Add `.env` support for secrets/configuration

---

## 🔸 Phase 2: Documentation Scraper

### 3. Web Scraper Module
- [ ] Input: Framework docs base URL
- [ ] Output: List of (URL, cleaned HTML/text) pairs
- [ ] Add crawling limits, deduplication, retries

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
- [ ] Create schema: `documents`, `chunks`, `vectors`
- [ ] Enable extension: `CREATE EXTENSION vector;`
- [ ] Write script to insert metadata + embeddings

### 8. Similarity Search
- [ ] SQL query for top-k similar vectors
- [ ] Add filtering support (by doc/meta)

---

## 🧰 Phase 5: API Server (MCP)

### 9. FastMCP Server

### 10. (Optional) LLM Response Generation
- [ ] Use OpenAI or local LLM to synthesize answers

---

## 🧪 Phase 6: Testing & Developer Experience

### 11. Testing
- [ ] Add unit tests for each module

### 12. CLI Interface
- [ ] Basic CLI for local testing and usage

### 13. Logging/Error Handling
- [ ] Add structured logging
- [ ] Add try/except error handling across modules

### 14. Documentation
- [ ] Write README with setup and usage instructions
