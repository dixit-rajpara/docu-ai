# Documentation Scraper with Vector DB & MCP Server

A powerful documentation scraping and search system that uses vector embeddings to enable semantic search capabilities across framework documentation.

## 🌟 Features

- 🕷️ **Web Scraping**: Efficiently crawls and extracts content from framework documentation
- 🧹 **Text Processing**: Cleans and normalizes HTML content while preserving semantic structure
- 🧩 **Smart Chunking**: Splits documentation into meaningful, context-aware chunks
- 🧠 **Vector Embeddings**: Generates embeddings using state-of-the-art models
- 🗄️ **Vector Database**: Stores and indexes embeddings for fast similarity search
- 🔌 **MCP Integration**: Seamless integration with MCP server for documentation search
- 📊 **CLI Interface**: Enables easy local testing and usage

## 🛠️ Technology Stack

- **Language**: Python 3.11+
- **Web Scraping**: BeautifulSoup4, Requests
- **Vector Embeddings**: OpenAI/HuggingFace
- **Database**: PostgreSQL with pgvector
- **Testing**: Pytest
- **Containerization**: Docker

## 📋 Prerequisites

- Python 3.11 or higher
- PostgreSQL with pgvector extension
- Docker (optional)
- OpenAI API key (or alternative embedding provider)

## 🚀 Getting Started

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd docs_mcp
   ```

2. Set up the virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Run the CLI:
   ```bash
   python -m src.cli.main
   ```

## 🏗️ Project Structure

```
docs_mcp/
├── src/
│   ├── scraper/      # Web scraping and HTML processing
│   ├── chunking/     # Text chunking and preprocessing
│   ├── embedding/    # Vector embedding generation
│   ├── db/          # Database operations and vector storage
│   ├── mcp/         # MCP server integration
│   └── cli/         # Command-line interface
├── tests/           # Test suites mirroring src structure
├── docker/          # Docker configuration files
└── docs/           # Additional documentation
```

## 🧪 Running Tests

```bash
pytest
```

## 🐳 Docker Deployment

1. Build the Docker image:
   ```bash
   docker-compose build
   ```

2. Run the services:
   ```bash
   docker-compose up -d
   ```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- OpenAI for embedding models
- pgvector contributors
