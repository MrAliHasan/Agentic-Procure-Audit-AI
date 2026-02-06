# Contributing to Sovereign Order Intelligence

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.11+
- Ollama with qwen2.5:7b
- Tesseract OCR
- Git

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/alihassan/sovereign-order-intelligence.git
cd sovereign-order-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_grader.py -v
```

### Code Formatting

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
src/
├── llm/           # LLM client, embeddings, prompts
├── storage/       # ChromaDB, caching
├── tools/         # Tavily, OCR, scraper
├── models/        # Pydantic data models
├── graphs/        # LangGraph workflows
├── processors/    # Business logic (grader, document)
├── api/           # FastAPI server
├── ui/            # Streamlit UI
└── cli.py         # CLI entry point
```

## Contribution Guidelines

### Code Style

- Use Black for formatting (line length: 100)
- Follow PEP 8
- Use type hints everywhere
- Write docstrings for all public functions

### Commit Messages

Use conventional commits format:

```
feat: add vendor comparison feature
fix: correct OCR text extraction for PDFs
docs: update API documentation
test: add tests for grading workflow
refactor: simplify document processor
```

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v`)
5. Run linting (`ruff check src/`)
6. Commit your changes
7. Push to your fork
8. Open a Pull Request

### PR Requirements

- [ ] Tests pass
- [ ] Linting passes
- [ ] Documentation updated (if applicable)
- [ ] Type hints added
- [ ] Docstrings added

## Adding New Features

### Adding a New Tool

1. Create file in `src/tools/`
2. Implement async functions
3. Add LangGraph-compatible wrapper if needed
4. Add tests in `tests/`
5. Update `DOCS.md`

### Adding a New Endpoint

1. Add route in `src/api/server.py`
2. Add request/response models
3. Update `API.md`
4. Add tests in `tests/test_api.py`

### Adding a New Graph Node

1. Add node function in `src/graphs/`
2. Update state definition if needed
3. Wire into graph with edges
4. Add tests

## Architecture Decisions

### Why Ollama?
- Local deployment for data sovereignty
- Easy model switching
- GPU/CPU flexibility

### Why ChromaDB?
- Embedded vector database
- No external service needed
- Persistent storage

### Why LangGraph?
- Cyclic graph support (RAG loops)
- State management
- Easy debugging

### Why Pytesseract?
- CPU-optimized (no GPU required)
- Low memory footprint (~200MB)
- Well-established and reliable

## Getting Help

- Open an issue for bugs
- Start a discussion for feature requests
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
