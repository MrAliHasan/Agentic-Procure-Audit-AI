# Changelog

All notable changes to Sovereign Order Intelligence will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-06

### Added

#### Core Infrastructure
- **Ollama Client** (`src/llm/ollama_client.py`): Async LLM client with retry logic, streaming, and health checks
- **Embeddings** (`src/llm/embeddings.py`): Local sentence transformers for vector embeddings
- **Prompts** (`src/llm/prompts.py`): 7 specialized agent prompts for different tasks
- **Config** (`src/config.py`): Centralized Pydantic settings with environment variable support

#### Data Layer
- **ChromaDB Store** (`src/storage/chroma_store.py`): Vector database with async CRUD and similarity search
- **Cache** (`src/storage/cache.py`): File-based query cache with TTL

#### Tools
- **Tavily Search** (`src/tools/tavily_search.py`): Web search for vendor research and market intelligence
- **OCR** (`src/tools/ocr.py`): Pytesseract-based document extraction (CPU-optimized)
- **Scraper** (`src/tools/scraper.py`): Website scraper with Playwright support
- **Database Tools** (`src/tools/database.py`): LangGraph-compatible vector DB tools

#### Data Models
- **Vendor** (`src/models/vendor.py`): Vendor entity, profile, and contact models
- **Document** (`src/models/document.py`): Invoice, contract, bid document models
- **Analysis** (`src/models/analysis.py`): Scoring and analysis result models

#### LangGraph Workflows
- **States** (`src/graphs/states.py`): TypedDict definitions for 4 workflow types
- **Order Intelligence** (`src/graphs/order_intelligence.py`): Main RAG workflow (Retrieve→Grade→Search→Generate)

#### Business Logic
- **Vendor Grader** (`src/processors/vendor_grader.py`): Multi-criteria weighted scoring with explainability
- **Document Processor** (`src/processors/document_processor.py`): OCR + LLM field extraction pipeline
- **Report Generator** (`src/processors/report_generator.py`): Markdown/JSON report generation

#### Interfaces
- **FastAPI Server** (`src/api/server.py`): REST API with 15+ endpoints
- **CLI** (`src/cli.py`): Rich-formatted command-line tool with 10+ commands
- **Streamlit UI** (`src/ui/app.py`): 6-page web dashboard

#### Testing
- Test fixtures and conftest
- Vendor grader unit tests
- LangGraph workflow tests
- API endpoint tests

#### Documentation
- `README.md`: Project overview
- `DOCS.md`: Comprehensive documentation
- `API.md`: API endpoint reference
- `CONTRIBUTING.md`: Contributor guide

#### DevOps
- `Dockerfile`: Python 3.11 with tesseract
- `docker-compose.yml`: Ollama + API + UI services
- `pyproject.toml`: Modern Python packaging
- `requirements.txt`: Dependency list

### Technical Decisions
- **OCR**: Pytesseract (CPU-optimized, ~200MB RAM) instead of PaddleOCR
- **LLM**: Qwen2.5:7b via Ollama for 16GB RAM systems
- **Embeddings**: all-MiniLM-L6-v2 (384 dimensions)
- **Framework**: LangGraph for agentic workflows

---

## [Unreleased]

### Planned
- WebSocket streaming for real-time analysis
- Multi-language OCR support
- Advanced table extraction with camelot
- Batch document processing
- API key authentication
- Rate limiting
