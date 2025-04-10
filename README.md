# Documentation Scraper with Vector DB & MCP Server

A powerful documentation scraping and search system that uses vector embeddings to enable semantic search capabilities across framework documentation.

## 🕷️ **Advanced Web Scraping**: 
  - Rate-limited crawling with Crawl4AI
  - Sitemap-based discovery
  - Link crawling with deduplication
  - Support for JavaScript-rendered content
  - Concurrent scraping with proper throttling
- 🧹 **Text Processing**: Cleans and normalizes HTML content while preserving semantic structure
- 🧩 **Smart Chunking**: Splits documentation into meaningful, context-aware chunks
- 🧠 **Vector Embeddings**: Generates embeddings using state-of-the-art models
- 🗄️ **Vector Database**: Stores and indexes embeddings for fast similarity search
- 🔌 **MCP Integration**: Seamless integration with MCP server for documentation search
- 📊 **CLI Interface**: Enables easy local testing and usage
- 📝 **Structured Logging**: Comprehensive logging system with error tracking

## 🗄️ Vector DB Integration

The project uses PostgreSQL with pgvector for efficient vector storage and similarity search:

- **Schema Design**:
  - `data_sources`: Tracks documentation sources and processing status
  - `documents`: Stores individual documentation pages/files
  - `document_chunks`: Contains text chunks with vector embeddings
- **Features**:
  - HNSW indexing for fast similarity search
  - Cosine similarity distance metrics
  - Bulk document chunk insertion
  - Async SQLAlchemy ORM with type hints
  - JSONB metadata support
  - Cascading deletes
  - Proper indexing on frequently queried fields

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Package Management**: uv (Modern Python package installer)
- **Web Scraping**: Crawl4AI with rate limiting
- **Vector Embeddings**: OpenAI/HuggingFace (planned)
- **Database**: PostgreSQL 15+ with pgvector extension
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic with async and pgvector support
- **Testing**: Pytest with comprehensive test suite
- **Containerization**: Docker (planned)
- **Configuration**: python-dotenv
- **Logging**: Structured logging with custom handlers

## 📋 Prerequisites

- Python 3.11 or higher
- PostgreSQL 15+ with pgvector extension installed
- Docker (optional, for containerized deployment)
- OpenAI API key (or alternative embedding provider)
- uv package installer (recommended)

## 🚀 Getting Started

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd docu_ai
   ```

2. Set up the virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies using uv (recommended):
   ```bash
   pip install uv
   uv pip install -r requirements.txt
   ```
   Or using pip:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   # Create database and enable pgvector extension
   psql -U postgres -c "CREATE DATABASE docuai;"
   psql -U postgres -d docuai -c "CREATE EXTENSION vector;"
   
   # Run database migrations
   uv run alembic upgrade head
   ```

6. Run the CLI:
   ```bash
   python -m src.cli.main
   ```

## 🏗️ Project Structure

```
docu_ai/
├── src/
│   ├── scraper/          # Web scraping and HTML processing
│   │   ├── interface.py  # Scraper interface definition
│   │   ├── crawl4ai_client.py  # Main scraper implementation
│   │   ├── discovery.py  # URL discovery
│   │   ├── sitemap_finder.py  # Sitemap parsing
│   │   ├── link_crawler.py  # Link extraction
│   │   ├── factory.py    # Scraper factory
│   │   └── utils.py      # Shared utilities
│   ├── db/              # Database operations and vector storage
│   ├── cli/             # Command-line interface
│   ├── config/          # Configuration management
│   └── main.py          # Application entry point
├── migrations/         # Database migration scripts
│   ├── versions/      # Migration version files
│   └── env.py        # Migration environment config
├── tests/             # Test suites mirroring src structure
├── docker/           # Docker configuration files
├── docs/            # Additional documentation
├── logs/            # Application logs
├── alembic.ini      # Alembic configuration
└── .env.sample      # Environment variables template
```

## 🔧 Configuration

The project uses environment variables for configuration. Copy `.env.sample` to `.env` and configure:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=docuai
DB_USER=postgres
DB_PASSWORD=your_password

# Vector Configuration
EMBEDDING_DIMENSION=1536  # OpenAI ada-002 default
HNSW_M=16                # HNSW graph M parameter
HNSW_EF_CONSTRUCTION=64  # HNSW graph ef_construction parameter

# OpenAI Configuration (for embeddings)
OPENAI_API_KEY=your_api_key

# Scraping Configuration
CRAWL4AI_BASE_URL=http://localhost:11235
CRAWL4AI_API_TOKEN=your_token
MAX_CONCURRENT_JOBS=5
POLLING_INTERVAL=2.0
REQUEST_TIMEOUT=60.0
JOB_TIMEOUT=300.0
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_scraper.py

# Run with coverage
pytest --cov=src tests/
```

## 📝 Logging

The project uses a structured logging system with the following organization:
- `logs/app.log`: General application logs
- `logs/error.log`: Error-specific logs
- `logs/scraper.log`: Scraping-specific logs with detailed crawling information

Log levels:
- DEBUG: Detailed debugging information
- INFO: General operational information
- WARNING: Warning messages for non-critical issues
- ERROR: Error messages for critical issues
- CRITICAL: Critical errors that require immediate attention

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Crawl4AI team for the powerful web scraping capabilities
- OpenAI for embedding models
- pgvector contributors
- uv team for the modern Python package installer
