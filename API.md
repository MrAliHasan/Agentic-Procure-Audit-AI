# Sovereign Order Intelligence - API Documentation

> OpenAPI-compatible REST API for supply chain AI

## Base URL

```
http://localhost:8000
```

---

## Authentication

Currently no authentication required (add JWT/API key in production).

---

## Endpoints

### Health & Info

#### `GET /`

Root endpoint with API info.

**Response** `200 OK`
```json
{
  "name": "Sovereign Order Intelligence",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "analyze": "POST /analyze",
    "vendors": "/vendors",
    "documents": "/documents"
  }
}
```

---

#### `GET /health`

System health check.

**Response** `200 OK`
```json
{
  "status": "healthy",
  "components": {
    "ollama": {
      "status": "ok",
      "model": "qwen2.5:7b"
    },
    "tavily": {
      "status": "ok"
    },
    "vector_store": {
      "status": "ok",
      "stats": {
        "vendors": {"count": 15},
        "documents": {"count": 8}
      }
    }
  }
}
```

---

### Analysis

#### `POST /analyze`

Run the full Order Intelligence RAG workflow.

**Request Body**
```json
{
  "query": "Compare electronic suppliers for reliability",
  "criteria": ["price", "quality", "reliability", "risk"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Analysis query |
| `criteria` | array | No | Scoring criteria (default: price, quality, reliability, risk) |

**Response** `200 OK`
```json
{
  "query": "Compare electronic suppliers for reliability",
  "analysis": {
    "recommendations": [...],
    "scores": {...}
  },
  "final_answer": "Based on the analysis of 3 vendors...",
  "reasoning_chain": [
    "Retrieved 3 vendors from knowledge base",
    "Graded relevance: 0.85 - sufficient",
    "Generated comparative analysis"
  ],
  "sources": {
    "vendors": 3,
    "documents": 2,
    "web_results": 0
  }
}
```

---

#### `POST /analyze/vendor`

Analyze a specific vendor.

**Request Body**
```json
{
  "vendor_name": "Acme Corp",
  "criteria": ["price", "quality", "reliability", "risk"],
  "include_web_research": true
}
```

**Response** `200 OK`
```json
{
  "analysis": {
    "vendor_id": "v_abc123",
    "vendor_name": "Acme Corp",
    "overall_score": 82,
    "recommendation": "APPROVED",
    "breakdown": {
      "price": {"score": 85, "reasoning": "Competitive pricing"},
      "quality": {"score": 90, "reasoning": "High product quality"},
      "reliability": {"score": 75, "reasoning": "Good track record"},
      "risk": {"score": 80, "reasoning": "Low risk profile"}
    },
    "confidence": 0.87,
    "reasoning_chain": ["..."],
    "sources": ["..."]
  },
  "report": "# Vendor Analysis Report\n..."
}
```

---

### Vendors

#### `GET /vendors`

List all vendors in knowledge base.

**Query Parameters**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max vendors to return |

**Response** `200 OK`
```json
{
  "vendors": [
    {
      "id": "v_abc123",
      "text": "Acme Corp. Electronic components supplier...",
      "score": 0.95,
      "metadata": {
        "name": "Acme Corp",
        "website": "https://acme.com",
        "industry": "Electronics"
      }
    }
  ],
  "count": 15
}
```

---

#### `POST /vendors`

Add a new vendor.

**Request Body**
```json
{
  "name": "Acme Corp",
  "description": "Leading electronic components supplier",
  "website": "https://acme.com",
  "industry": "Electronics",
  "products": ["Capacitors", "Resistors", "ICs"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Vendor name |
| `description` | string | No | Description |
| `website` | string | No | Website URL |
| `industry` | string | No | Industry category |
| `products` | array | No | Products/services offered |

**Response** `200 OK`
```json
{
  "success": true,
  "vendor_id": "v_abc123def456"
}
```

---

#### `GET /vendors/{vendor_id}`

Get vendor by ID.

**Response** `200 OK`
```json
{
  "id": "v_abc123",
  "text": "Acme Corp...",
  "metadata": {
    "name": "Acme Corp",
    "website": "https://acme.com"
  }
}
```

**Response** `404 Not Found`
```json
{
  "detail": "Vendor not found"
}
```

---

#### `POST /vendors/search`

Semantic search for vendors.

**Request Body**
```json
{
  "query": "reliable electronics supplier",
  "limit": 10,
  "collection": "vendors"
}
```

**Response** `200 OK`
```json
{
  "results": [
    {
      "id": "v_abc123",
      "text": "Acme Corp...",
      "score": 0.92,
      "metadata": {...}
    }
  ],
  "count": 3
}
```

---

### Documents

#### `POST /documents/process`

Upload and process a document.

**Request** `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF, PNG, or JPG file |
| `doc_type` | string | No | `auto`, `invoice`, `contract`, `bid` |

**Response** `200 OK`
```json
{
  "document": {
    "id": "doc_xyz789",
    "type": "invoice",
    "file_name": "invoice_001.pdf",
    "extracted_text": "INVOICE\nFrom: Acme Corp...",
    "extracted_fields": {
      "vendor_name": "Acme Corp",
      "invoice_number": "INV-2025-001",
      "total_amount": 1500.00,
      "due_date": "2025-03-01"
    },
    "confidence": 0.87,
    "ocr_quality": 0.92,
    "validation_status": "valid",
    "validation_errors": []
  },
  "processing_time_ms": 1250,
  "warnings": [],
  "errors": []
}
```

---

#### `GET /documents`

List processed documents.

**Query Parameters**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 20 | Max documents |
| `doc_type` | string | null | Filter by type |

**Response** `200 OK`
```json
{
  "documents": [...],
  "count": 8
}
```

---

### Research

#### `POST /research/market`

Market research using web search.

**Query Parameters**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `category` | string | No | Market category |

**Response** `200 OK`
```json
{
  "query": "semiconductor market trends 2025",
  "results": [
    {
      "title": "Semiconductor Market Forecast 2025",
      "content": "The global semiconductor market...",
      "url": "https://example.com/article",
      "score": 0.95
    }
  ]
}
```

---

#### `POST /research/vendor/{vendor_name}`

Research a vendor online.

**Response** `200 OK`
```json
{
  "vendor_name": "Acme Corp",
  "information": {
    "company overview": [...],
    "reviews": [...],
    "pricing": [...]
  },
  "risks": {
    "risk_level": "low",
    "risk_factors_found": 0,
    "findings": []
  }
}
```

---

### Stats

#### `GET /stats`

System statistics.

**Response** `200 OK`
```json
{
  "knowledge_base": {
    "vendors": {"count": 15},
    "documents": {"count": 8},
    "market_intel": {"count": 25}
  },
  "config": {
    "model": "qwen2.5:7b",
    "relevance_threshold": 0.7,
    "max_web_searches": 3
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request body"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error processing request: ..."
}
```

---

## Rate Limits

No rate limits in local deployment. For production, consider adding:
- Request throttling
- API key authentication
- Usage quotas

---

## WebSocket (Future)

Streaming analysis via WebSocket planned for v2.0:
```
ws://localhost:8000/ws/analyze
```
