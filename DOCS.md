# Sovereign Order Intelligence - Complete Documentation

> **AI-Powered Supply Chain & Vendor Management**
> 100% Python • Local LLM Deployment • Zero Cloud Dependency

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Quick Start](#quick-start)
6. [API Reference](#api-reference)
7. [CLI Reference](#cli-reference)
8. [Web UI Guide](#web-ui-guide)
9. [Core Modules](#core-modules)
10. [LangGraph Workflow](#langgraph-workflow)
11. [Document Processing](#document-processing)
12. [Vendor Grading](#vendor-grading)
13. [Web Research](#web-research)
14. [Testing](#testing)
15. [Docker Deployment](#docker-deployment)
16. [Troubleshooting](#troubleshooting)

---

## Overview

Sovereign Order Intelligence (SOI) is a production-ready supply chain AI platform that provides:

- **🔒 AI Sovereignty**: All data stays local, GDPR compliant by design
- **🧠 Agentic RAG**: Retrieve → Grade → Search → Generate workflow
- **📊 Explainable AI**: Full reasoning traces for every decision
- **🌐 Real-Time Intel**: Live market research via Tavily search
- **📄 Document Processing**: Invoices, contracts, bids extraction
- **⚖️ Vendor Grading**: Multi-criteria scoring with recommendations

### Why SOI vs Competitors?

| Feature          | SAP Ariba | Coupa   | Jaggaer    | **SOI**        |
| ---------------- | --------- | ------- | ---------- | -------------------- |
| Annual Cost      | 50k+      | 100k+   | Enterprise | **$0**         |
| Data Location    | Cloud     | Cloud   | Cloud      | **100% Local** |
| Setup Time       | Months    | Weeks   | Months     | **Hours**      |
| Reasoning Traces | ❌        | ❌      | ❌         | **✅**         |
| Customizable     | ❌        | Limited | Limited    | **100%**       |
| Web Search       | ❌        | ❌      | ❌         | **✅ Tavily**  |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   Streamlit UI  │   REST API      │   CLI (soi)                 │
│   (Port 8501)   │   (Port 8000)   │                             │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         └─────────────────┴───────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │      LangGraph Workflow           │
         │   ┌─────────────────────────┐     │
         │   │ 1. RETRIEVE (ChromaDB)  │     │
         │   │ 2. GRADE (LLM)          │     │
         │   │ 3. SEARCH (Tavily)      │     │
         │   │ 4. GENERATE (LLM)       │     │
         │   └─────────────────────────┘     │
         └─────────────────┬─────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
┌───▼───┐            ┌─────▼─────┐          ┌─────▼─────┐
│Ollama │            │ ChromaDB  │          │  Tavily   │
│LLM    │            │ Vectors   │          │  Search   │
│Qwen2.5│            │ (Local)   │          │  (API)    │
└───────┘            └───────────┘          └───────────┘
```

### Tech Stack

| Layer                | Technology            | Purpose             |
| -------------------- | --------------------- | ------------------- |
| **LLM**        | Ollama + Qwen2.5:7b   | Local inference     |
| **Embeddings** | Sentence Transformers | Vector embeddings   |
| **Vector DB**  | ChromaDB              | Semantic search     |
| **Web Search** | Tavily API            | Real-time research  |
| **OCR**        | Pytesseract           | Document extraction |
| **Workflow**   | LangGraph             | Agentic RAG loop    |
| **API**        | FastAPI               | REST endpoints      |
| **UI**         | Streamlit             | Web dashboard       |
| **CLI**        | Click + Rich          | Command-line        |

---

## 🔐 AI Sovereignty: Your Private Knowledge Base

> **The core differentiator**: Your sensitive data stays on your machine. Web search is only used for **public** information when local data isn't sufficient.

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       YOUR QUERY                                  │
│    "What's our negotiated price with Supplier X?"                │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 1: VECTOR STORE (100% LOCAL - ChromaDB)                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │ Your Contracts │  │ Your Vendors   │  │ Your Documents │      │
│  │ (Confidential) │  │ (Private List) │  │ (Sensitive)    │      │
│  └────────────────┘  └────────────────┘  └────────────────┘      │
│                                                                   │
│  ✅ Found locally? → Use it → NEVER touches internet             │
│  ❌ Not found? → Continue to Step 2                              │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (Only if not found locally)
┌──────────────────────────────────────────────────────────────────┐
│  STEP 2: WEB SEARCH (Public Information Only)                    │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │
│  │ Serper/Google  │  │ Tavily Search  │  │ Page Scraping  │      │
│  │ (Public Web)   │  │ (AI Search)    │  │ (Product Info) │      │
│  └────────────────┘  └────────────────┘  └────────────────┘      │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  STEP 3: LOCAL LLM ANALYSIS (Ollama - DeepSeek/Qwen)             │
│  All processing happens on YOUR machine. No cloud LLM APIs.       │
└──────────────────────────────────────────────────────────────────┘
```

### Why This Matters for Enterprise

| Scenario | Without Sovereignty | With SOI |
|----------|-------------------|-----------------|
| **Vendor contract analysis** | Data sent to OpenAI/Claude | Stays on your laptop |
| **Pricing negotiations** | Competitors could intercept | Never leaves your network |
| **Supplier performance data** | Exposed to third parties | 100% private |
| **Compliance documents** | Cloud storage risks | Air-gapped if needed |
| **Internal vendor ratings** | Visible to cloud providers | Completely local |

### Building Your Private Knowledge Base

```bash
# Add vendors to your private database
soi vendors add "My Exclusive Supplier" \
  --description "Contract price $2.50/unit, exclusive until 2027" \
  --industry "Electronics"

# Add confidential documents (with OCR extraction)
soi docs process ./contracts/supplier_agreement.pdf --type contract
soi docs process ./pricing/2026_catalog.pdf --type catalog

# Bulk import from CSV
soi import vendors ./approved_vendors.csv

# Search ONLY your private data (never uses web search)
soi vendors search "exclusive pricing" --local-only
soi analyze "supplier renewal terms" --local-only
```

### Data Storage Structure

```
./data/
├── chroma_db/                    # Vector database (your private knowledge)
│   ├── vendor_intelligence/      # Vendor profiles, capabilities, contracts
│   └── document_store/           # Ingested documents (OCR extracted text)
├── downloads/                    # Downloaded PDFs, datasheets from web
│   └── query_docs/               # Documents found via web search
└── reports/                      # Saved analysis reports (JSON)
    └── YYYYMMDD_query_name.json  # Timestamped report files
```

### Privacy Guarantees

| Component | Data Location | Cloud Exposure |
|-----------|--------------|----------------|
| **LLM** | Local Ollama | ❌ None |
| **Embeddings** | Local Sentence Transformers | ❌ None |
| **Vector Store** | Local ChromaDB | ❌ None |
| **Documents** | Local filesystem | ❌ None |
| **Web Search** | Serper/Tavily API | ⚠️ Only query sent (no private data) |

### Save & Export Reports

```bash
# Analyze with verbose output and save report
soi analyze "ATmega328P pricing comparison" -v -s

# Report saved to: ./data/reports/20260207_ATmega328P_pricing_.json
```

Report contains:
```json
{
  "query": "ATmega328P pricing comparison",
  "criteria": ["price", "quality", "reliability", "risk"],
  "timestamp": "2026-02-07T01:45:00",
  "result": {
    "overall_score": 82,
    "recommendation": "APPROVED",
    "breakdown": {...},
    "sources": {...}
  }
}
```

---

## Installation

### Prerequisites

- **Python**: 3.11 or higher
- **RAM**: 16GB+ recommended
- **Ollama**: For local LLM inference
- **Tesseract**: For OCR (system dependency)

### Step 1: Install System Dependencies

```bash
# macOS
brew install tesseract poppler

# Ubuntu/Debian
sudo apt-get install tesseract-ocr poppler-utils

# Windows (via Chocolatey)
choco install tesseract poppler
```

### Step 2: Install Ollama and Model

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama server
ollama serve

# Pull the model (in another terminal)
ollama pull qwen2.5:7b
```

### Step 3: Install SOI

```bash
cd sovereign-order-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install the package
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy example env
cp .env.example .env

# Edit with your Tavily API key
nano .env
```

---

## Configuration

All configuration is done via environment variables in `.env`:

### Core Settings

```env
# Application
DEBUG=false
LOG_LEVEL=INFO

# Ollama LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120

# Tavily Web Search
TAVILY_API_KEY=your-api-key-here
TAVILY_MAX_RESULTS=5
```

### Grading Thresholds

```env
# RAG Loop Control
RELEVANCE_THRESHOLD=0.7      # Min relevance to skip web search
CONFIDENCE_THRESHOLD=0.8     # Min confidence for auto-approval
MAX_WEB_SEARCHES=3           # Max search iterations

# Vendor Scoring Weights (must sum to 1.0)
WEIGHT_PRICE=0.30
WEIGHT_QUALITY=0.25
WEIGHT_RELIABILITY=0.25
WEIGHT_RISK=0.20
```

### Storage Settings

```env
# ChromaDB
CHROMA_PERSIST_DIR=./data/chroma_db
CHROMA_COLLECTION_NAME=vendor_intelligence

# Cache
CACHE_TTL_SECONDS=3600
BATCH_SIZE=10
```

### API Settings

```env
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Quick Start

### Option 1: CLI

```bash
# Check system status
soi status

# Analyze a query
soi analyze "Find reliable electronic component suppliers under $10k"

# Grade a specific vendor
soi grade "Acme Corp" --web

# Add a vendor to knowledge base
soi vendors add "Acme Corp" -d "Electronic components supplier" -w "https://acme.com"

# Search vendors
soi vendors search "electronics supplier"

# Process a document
soi docs process invoice.pdf --type invoice

# Start the API server
soi serve
```

### Option 2: API

```bash
# Start server
python -m src.api.server

# Test health
curl http://localhost:8000/health

# Analyze query
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Compare top suppliers for reliability"}'

# Add vendor
curl -X POST http://localhost:8000/vendors \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Corp", "description": "Electronics supplier"}'
```

### Option 3: Streamlit UI

```bash
streamlit run src/ui/app.py
# Opens at http://localhost:8501
```

---

## API Reference

### Base URL

```
http://localhost:8000
```

### Health Endpoints

#### `GET /`

Returns API info and available endpoints.

#### `GET /health`

System health check including Ollama, ChromaDB, and Tavily status.

**Response:**

```json
{
  "status": "healthy",
  "components": {
    "ollama": {"status": "ok", "model": "qwen2.5:7b"},
    "tavily": {"status": "ok"},
    "vector_store": {"status": "ok", "stats": {...}}
  }
}
```

### Analysis Endpoints

#### `POST /analyze`

Run the full Order Intelligence workflow.

**Request:**

```json
{
  "query": "Compare electronic suppliers for price and reliability",
  "criteria": ["price", "quality", "reliability", "risk"]
}
```

**Response:**

```json
{
  "query": "...",
  "analysis": {...},
  "final_answer": "Based on analysis...",
  "reasoning_chain": ["Step 1...", "Step 2..."],
  "sources": {
    "vendors": 3,
    "documents": 2,
    "web_results": 5
  }
}
```

#### `POST /analyze/vendor`

Analyze a specific vendor.

**Request:**

```json
{
  "vendor_name": "Acme Corp",
  "criteria": ["price", "quality", "reliability", "risk"],
  "include_web_research": true
}
```

### Vendor Endpoints

#### `GET /vendors`

List all vendors in knowledge base.

#### `POST /vendors`

Add a new vendor.

**Request:**

```json
{
  "name": "Acme Corp",
  "description": "Leading electronics supplier",
  "website": "https://acme.com",
  "industry": "Electronics",
  "products": ["Capacitors", "Resistors", "ICs"]
}
```

#### `GET /vendors/{vendor_id}`

Get vendor by ID.

#### `POST /vendors/search`

Semantic search for vendors.

**Request:**

```json
{
  "query": "reliable electronics supplier",
  "limit": 10
}
```

### Document Endpoints

#### `POST /documents/process`

Upload and process a document.

**Request:** `multipart/form-data`

- `file`: PDF, PNG, JPG file
- `doc_type`: `auto`, `invoice`, `contract`, `bid`

**Response:**

```json
{
  "document": {
    "id": "doc_abc123",
    "type": "invoice",
    "extracted_fields": {
      "vendor_name": {"value": "Acme Corp", "confidence": 0.95},
      "total_amount": {"value": 1500.00, "confidence": 0.92}
    },
    "confidence": 0.87,
    "validation_status": "valid"
  },
  "processing_time_ms": 1250
}
```

#### `GET /documents`

List processed documents.

### Research Endpoints

#### `POST /research/market`

Market research using web search.

#### `POST /research/vendor/{vendor_name}`

Research a vendor online.

### Stats Endpoint

#### `GET /stats`

System statistics.

---

## CLI Reference

### Global Commands

```bash
soi --help              # Show help
soi --version           # Show version
soi status              # Check system status
soi serve               # Start API server
```

### Analyze Commands

```bash
# Basic analysis
soi analyze "your query here"

# With specific criteria
soi analyze "query" -c price -c quality -c reliability

# JSON output
soi analyze "query" -j
```

### Grade Commands

```bash
# Grade with web research
soi grade "Vendor Name" --web

# Grade without web research
soi grade "Vendor Name" --no-web

# Custom criteria
soi grade "Vendor Name" -c price -c quality
```

### Vendor Commands

```bash
# List vendors
soi vendors list
soi vendors list --limit 50

# Add vendor
soi vendors add "Name" -d "Description" -w "https://website.com" -i "Industry" -p "Product1" -p "Product2"

# Search
soi vendors search "query"
```

### Document Commands

```bash
# Process with auto-detection
soi docs process document.pdf

# Specify type
soi docs process invoice.pdf --type invoice
soi docs process contract.pdf --type contract
```

### Research Commands

```bash
# Research a vendor
soi research vendor "Vendor Name"

# Market research
soi research market "category"

# 🏢 Deep Company Research (Enhanced)
# Includes: executives, funding, market data, hiring, competitors
soi research company "Salesforce" -o salesforce.json -m salesforce_report.md
```

**Company Research Output:**
- 20 Serper queries for maximum coverage
- Executives with LinkedIn URLs
- Financials: funding, valuation, investors
- Market data: market share, TAM/SAM
- Hiring: open roles, tech stack, locations
- News tagged by type (funding/product/partnership)
- Data sources with real-time search proof

### Server Command

```bash
# Default settings
soi serve

# Custom host/port
soi serve -h 0.0.0.0 -p 8080

# With auto-reload (development)
soi serve --reload
```

---

## Web UI Guide

Access the Streamlit UI at `http://localhost:8501`

### Pages

1. **🏠 Dashboard**: Overview and quick actions
2. **🔍 Analyze Query**: Full RAG workflow analysis
3. **📊 Vendor Grading**: Grade and compare vendors
4. **📄 Document Processing**: Upload and extract documents
5. **🌐 Web Research**: Online vendor/market research
6. **⚙️ Settings**: System status and configuration

### Features

- **Real-time Analysis**: See reasoning chains as they happen
- **Visual Scores**: Progress bars and charts for scores
- **Export Options**: Download reports as JSON
- **Dark Mode**: Automatic theme support

---

## Core Modules

### `src/llm/` - LLM Infrastructure

#### `ollama_client.py`

Async Ollama client with:

- Retry logic (3 attempts with exponential backoff)
- Streaming support
- Chat and generate modes
- Health checks

```python
from src.llm.ollama_client import OllamaClient

client = OllamaClient()
response = await client.generate("Your prompt here")
await client.close()
```

#### `embeddings.py`

Local embeddings using Sentence Transformers:

- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Async support
- Cosine similarity utilities

```python
from src.llm.embeddings import get_embeddings

embeddings = get_embeddings()
vector = embeddings.embed_query("search text")
```

#### `prompts.py`

Specialized system prompts:

- `VENDOR_ANALYST_PROMPT`: Vendor analysis
- `DOCUMENT_EXTRACTOR_PROMPT`: Document extraction
- `GRADING_PROMPT`: Scoring and recommendations
- `RELEVANCE_GRADER_PROMPT`: RAG relevance grading
- `HALLUCINATION_DETECTOR_PROMPT`: Grounding checks

### `src/storage/` - Data Layer

#### `chroma_store.py`

ChromaDB vector store with:

- Multiple collections (vendors, documents, market_intel)
- Async CRUD operations
- Metadata filtering
- Similarity search

```python
from src.storage.chroma_store import get_vector_store

store = get_vector_store()
results = await store.similarity_search("query", k=5, collection="vendors")
```

#### `cache.py`

TTL-based query cache:

- File + memory hybrid caching
- Configurable TTL
- Auto-expiration

```python
from src.storage.cache import get_cache

cache = get_cache()
result = await cache.get_or_compute("key", compute_fn, ttl=3600)
```

### `src/tools/` - Agent Tools

#### `tavily_search.py`

Web search integration:

- Vendor research
- Market trends
- Risk analysis

#### `ocr.py`

Document text extraction:

- Pytesseract (CPU-optimized)
- PDF and image support
- Confidence scoring

#### `scraper.py`

Website scraping:

- Email/phone extraction
- Social link discovery
- Playwright fallback for JS sites

### `src/models/` - Data Models

#### `vendor.py`

Vendor entity models:

- `Vendor`: Core vendor data
- `VendorProfile`: Extended profile
- `VendorContact`: Contact info

#### `document.py`

Document models:

- `Document`: Base document
- `InvoiceData`: Invoice fields
- `ContractData`: Contract fields
- `ExtractedField`: Field with confidence

#### `analysis.py`

Analysis models:

- `VendorAnalysis`: Grading results
- `ScoreDetail`: Per-criterion scores
- `MarketIntelligence`: Research results

---

## LangGraph Workflow

The core Order Intelligence workflow implements an **agentic RAG loop**:

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │RETRIEVE │ ← Query ChromaDB for relevant data
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │  GRADE  │ ← LLM evaluates relevance
                    └────┬────┘
                         │
              ┌──────────┴──────────┐
              │                     │
         score >= 0.7          score < 0.7
              │                     │
              │               ┌─────▼─────┐
              │               │WEB SEARCH │ ← Tavily API
              │               └─────┬─────┘
              │                     │
              └──────────┬──────────┘
                         │
                    ┌────▼────┐
                    │GENERATE │ ← Final analysis with reasoning
                    └────┬────┘
                         │
                    ┌────▼────┐
                    │   END   │
                    └─────────┘
```

### Usage

```python
from src.graphs.order_intelligence import analyze_query

result = await analyze_query(
    query="Compare top 3 suppliers for quality",
    criteria=["price", "quality", "reliability", "risk"]
)

print(result["final_answer"])
print(result["reasoning_chain"])
```

### State Fields

```python
class OrderIntelligenceState(TypedDict):
    query: str                      # User query
    criteria: list[str]             # Evaluation criteria
    vendors: list[dict]             # Retrieved vendors
    documents: list[dict]           # Retrieved documents
    web_results: list[dict]         # Web search results
    reasoning_steps: list[str]      # Accumulated reasoning
    analysis: Optional[dict]        # Final analysis
    final_answer: str               # Generated response
    iteration: int                  # Search iteration count
```

---

## Document Processing

### Supported Formats

- **PDF**: Digital and scanned
- **Images**: PNG, JPG, JPEG

### Document Types

- **Invoice**: Vendor, amounts, line items, dates
- **Contract**: Parties, terms, obligations
- **Bid**: Pricing, specifications, delivery

### Processing Pipeline

```
Document → OCR (Pytesseract) → Type Detection → LLM Extraction → Validation → Storage
```

### Usage

```python
from src.processors.document_processor import DocumentProcessor

processor = DocumentProcessor()
result = await processor.process("invoice.pdf", doc_type="auto")

print(result.document.extracted_fields)
print(result.document.confidence)
```

### Field Extraction

The LLM extracts structured fields with confidence scores:

```json
{
  "vendor_name": {"value": "Acme Corp", "confidence": 0.95},
  "total_amount": {"value": 1500.00, "confidence": 0.92},
  "due_date": {"value": "2025-03-01", "confidence": 0.88}
}
```

---

## Vendor Grading

### Scoring Criteria

| Criterion   | Weight | Description                  |
| ----------- | ------ | ---------------------------- |
| Price       | 30%    | Cost competitiveness         |
| Quality     | 25%    | Product/service quality      |
| Reliability | 25%    | Delivery, consistency        |
| Risk        | 20%    | Financial, operational risks |

### Recommendations

| Score Range | Recommendation |
| ----------- | -------------- |
| 70-100      | ✅ APPROVED    |
| 50-69       | ⚠️ REVIEW    |
| 0-49        | ❌ REJECTED    |

### Usage

```python
from src.processors.vendor_grader import VendorGrader

grader = VendorGrader()
analysis = await grader.grade(
    vendor_name="Acme Corp",
    vendor_data={"name": "Acme Corp"},
    criteria=["price", "quality", "reliability", "risk"],
    web_research=None  # Optional web research data
)

print(f"Score: {analysis.overall_score}")
print(f"Recommendation: {analysis.recommendation}")
```

### Explainability

Every analysis includes a reasoning chain:

```python
analysis.reasoning_chain = [
    "Step 1: Analyzed pricing data from 3 sources",
    "Step 2: Found 95% on-time delivery rate",
    "Step 3: No significant risk factors identified",
    "Step 4: Overall assessment: Strong vendor with competitive pricing"
]
```

---

## Web Research

### Tavily Integration

SOI uses Tavily API for real-time web search:

```python
from src.tools.tavily_search import TavilySearchTool

search = TavilySearchTool()

# General search
results = await search.search("electronic component suppliers 2025")

# Vendor research
info = await search.search_vendor_info("Acme Corp")

# Market trends
trends = await search.search_market_trends("semiconductors")

# Risk analysis
risks = await search.search_vendor_risks("Acme Corp")
```

### Search Types

1. **General Search**: Any query
2. **Vendor Research**: Company overview, reviews, pricing
3. **Market Trends**: Industry outlook, pricing trends
4. **Risk Analysis**: Legal issues, complaints, financial problems

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Tests

```bash
# Test grader
pytest tests/test_grader.py -v

# Test graph
pytest tests/test_graph.py -v

# Test API
pytest tests/test_api.py -v
```

### Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py       # Fixtures
├── test_grader.py    # Vendor grading tests
├── test_graph.py     # LangGraph workflow tests
└── test_api.py       # API endpoint tests
```

---

## Docker Deployment

### Quick Start

```bash
docker-compose up -d
```

### Services

| Service    | Port  | Description  |
| ---------- | ----- | ------------ |
| `ollama` | 11434 | Local LLM    |
| `api`    | 8000  | REST API     |
| `ui`     | 8501  | Streamlit UI |

### Build Only API

```bash
docker build -t soi:latest .
docker run -p 8000:8000 -v $(pwd)/data:/app/data soi:latest
```

### With GPU (NVIDIA)

```bash
docker-compose up -d ollama  # Uses GPU for Ollama
```

### Health Checks

All services have health checks configured:

- Ollama: `/api/tags`
- API: `/health`

---

## Troubleshooting

### Ollama Not Connecting

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
ollama serve

# Check model is downloaded
ollama list
```

### OCR Not Working

```bash
# Check Tesseract installation
tesseract --version

# macOS
brew install tesseract

# Linux
sudo apt-get install tesseract-ocr
```

### ChromaDB Errors

```bash
# Reset ChromaDB
rm -rf data/chroma_db

# Restart application
```

### Memory Issues

With 16GB RAM:

- Use `qwen2.5:7b` (recommended)
- Avoid larger models (14b, 32b)
- Limit batch sizes in config

### API Timeout

```bash
# Increase timeout in .env
OLLAMA_TIMEOUT=180
```

---

## Support

For issues and feature requests, please open an issue on GitHub.

**Built with ❤️ for supply chain professionals who value data sovereignty.**
