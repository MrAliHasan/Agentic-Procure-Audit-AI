"""
FastAPI Server - RESTful API for Agentic Procure-Audit AI
"""
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from src.config import settings, get_settings
from src.graphs.order_intelligence import analyze_query
from src.processors.vendor_grader import VendorGrader
from src.processors.document_processor import DocumentProcessor
from src.processors.report_generator import ReportGenerator
from src.storage.chroma_store import get_vector_store
from src.llm.ollama_client import OllamaClient
from src.tools.tavily_search import TavilySearchTool


# ============== Lifespan ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Check Ollama connection
    client = OllamaClient()
    if await client.health_check():
        print(f"✅ Connected to Ollama ({settings.ollama_model})")
    else:
        print(f"⚠️ Ollama not available - some features may not work")
    await client.close()
    
    # Initialize vector store
    store = get_vector_store()
    stats = await store.get_stats()
    print(f"✅ Vector store initialized ({stats})")
    
    yield
    
    # Shutdown
    print("Shutting down...")


# ============== App ==============

PUBLIC_PATHS = {"/", "/health"}
ALLOWED_UPLOAD_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".txt"}

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(request: Request, api_key: Optional[str] = Depends(api_key_header)):
    """Require X-API-Key on every non-public route when API_KEY is configured."""
    if not settings.api_key or request.url.path in PUBLIC_PATHS:
        return
    if not api_key or not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


app = FastAPI(
    title="Agentic Procure-Audit AI API",
    description="AI-powered procurement intelligence: vendor grading, bid extraction and market research",
    version=settings.app_version,
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

# CORS - only the origins listed in CORS_ORIGINS may call the API from a browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ============== Models ==============

class QueryRequest(BaseModel):
    query: str
    criteria: list[str] = ["price", "quality", "reliability", "risk"]


class VendorRequest(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    products: list[str] = []


class AnalyzeVendorRequest(BaseModel):
    vendor_name: str
    criteria: list[str] = ["price", "quality", "reliability", "risk"]
    include_web_research: bool = True


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    collection: str = "vendors"


# ============== Health Endpoints ==============

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "health": "/health",
            "analyze": "POST /analyze",
            "vendors": "/vendors",
            "documents": "/documents"
        }
    }


@app.get("/health")
async def health_check():
    """Complete health check."""
    # Check Ollama
    client = OllamaClient()
    ollama_ok = await client.health_check()
    await client.close()
    
    # Check Tavily
    tavily_ok = bool(settings.tavily_api_key)
    
    # Check vector store
    try:
        store = get_vector_store()
        stats = await store.get_stats()
        vector_ok = True
    except Exception:
        vector_ok = False
        stats = {}
    
    return {
        "status": "healthy" if (ollama_ok and vector_ok) else "degraded",
        "components": {
            "ollama": {"status": "ok" if ollama_ok else "error", "model": settings.ollama_model},
            "tavily": {"status": "ok" if tavily_ok else "missing"},
            "vector_store": {"status": "ok" if vector_ok else "error", "stats": stats}
        }
    }


# ============== Analysis Endpoints ==============

@app.post("/analyze")
async def analyze(request: QueryRequest):
    """
    Analyze a query using the Order Intelligence workflow.
    Implements Retrieve-Grade-Search-Generate loop.
    """
    try:
        result = await analyze_query(request.query, request.criteria)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze/vendor")
async def analyze_vendor(request: AnalyzeVendorRequest):
    """
    Analyze a specific vendor with optional web research.
    """
    grader = VendorGrader()
    
    # Get vendor data from store if exists
    store = get_vector_store()
    vendor_data = await store.similarity_search(
        request.vendor_name, k=1, collection="vendors"
    )
    
    vendor_info = vendor_data[0] if vendor_data else {"name": request.vendor_name}
    
    # Web research if requested
    web_research = []
    if request.include_web_research:
        try:
            search_tool = TavilySearchTool()
            research = await search_tool.search_vendor_info(request.vendor_name)
            web_research = research.get("results", {})
        except Exception:
            pass
    
    analysis = await grader.grade(
        request.vendor_name,
        vendor_info,
        request.criteria,
        web_research if web_research else None
    )
    
    # Generate report
    reporter = ReportGenerator()
    report = await reporter.vendor_report(analysis)
    
    return {
        "analysis": analysis.model_dump(),
        "report": report
    }


# ============== Vendor Endpoints ==============

@app.get("/vendors")
async def list_vendors(limit: int = 20):
    """List all vendors in the knowledge base."""
    store = get_vector_store()
    # Use empty query to get all
    results = await store.similarity_search("vendor supplier company", k=limit, collection="vendors")
    return {"vendors": results, "count": len(results)}


@app.post("/vendors")
async def add_vendor(vendor: VendorRequest):
    """Add a new vendor to the knowledge base."""
    import uuid
    
    store = get_vector_store()
    vendor_id = f"v_{uuid.uuid4().hex[:12]}"
    
    # Create searchable text
    text = f"{vendor.name}. {vendor.description or 'Vendor'}"
    if vendor.products:
        text += f" Products: {', '.join(vendor.products)}"
    
    metadata = {
        "vendor_id": vendor_id,
        "name": vendor.name,
        "website": vendor.website or "",
        "industry": vendor.industry or "",
        "products": ", ".join(vendor.products)
    }
    
    await store.add_documents(
        texts=[text],
        metadatas=[metadata],
        ids=[vendor_id],
        collection="vendors"
    )
    
    return {"success": True, "vendor_id": vendor_id}


@app.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: str):
    """Get a specific vendor by ID."""
    store = get_vector_store()
    result = await store.get_by_id(vendor_id, collection="vendors")
    
    if not result:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return result


@app.post("/vendors/search")
async def search_vendors(request: SearchRequest):
    """Search vendors by semantic similarity."""
    store = get_vector_store()
    results = await store.similarity_search(
        request.query, k=request.limit, collection="vendors"
    )
    return {"results": results, "count": len(results)}


# ============== Document Endpoints ==============

@app.post("/documents/process")
async def process_document(
    file: UploadFile = File(...),
    doc_type: str = Form("auto")
):
    """
    Upload and process a document (invoice, contract, bid).
    Extracts structured data using OCR and LLM.
    """
    import tempfile
    
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix or 'none'}")
    
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
    
    # Save uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        processor = DocumentProcessor()
        result = await processor.process(tmp_path, doc_type)
        
        # Save to vector store if valid
        if result.document.validation_status == "valid":
            store = get_vector_store()
            await store.add_documents(
                texts=[result.document.extracted_text],
                metadatas=[{
                    "type": result.document.type,
                    "file_name": file.filename,
                    "extracted_fields": str(result.document.extracted_fields)
                }],
                ids=[result.document.id],
                collection="documents"
            )
        
        return {
            "document": result.document.model_dump(),
            "processing_time_ms": result.processing_time_ms,
            "warnings": result.warnings,
            "errors": result.errors
        }
        
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/documents")
async def list_documents(limit: int = 20, doc_type: str = None):
    """List processed documents."""
    store = get_vector_store()
    
    filter_metadata = {"type": doc_type} if doc_type else None
    
    results = await store.similarity_search(
        "document invoice contract bid",
        k=limit,
        collection="documents",
        filter_metadata=filter_metadata
    )
    
    return {"documents": results, "count": len(results)}


# ============== Web Research Endpoints ==============

@app.post("/research/market")
async def market_research(query: str, category: str = None):
    """Perform market research using web search."""
    try:
        search_tool = TavilySearchTool()
        
        if category:
            results = await search_tool.search_market_trends(category)
        else:
            results = await search_tool.search(query, max_results=10)
            results = {"query": query, "results": [r.model_dump() for r in results]}
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/research/vendor/{vendor_name}")
async def vendor_research(vendor_name: str):
    """Research a vendor using web search."""
    try:
        search_tool = TavilySearchTool()
        
        # Get comprehensive vendor info
        info = await search_tool.search_vendor_info(vendor_name)
        risks = await search_tool.search_vendor_risks(vendor_name)
        
        return {
            "vendor_name": vendor_name,
            "information": info,
            "risks": risks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Stats Endpoints ==============

@app.get("/stats")
async def get_stats():
    """Get system statistics."""
    store = get_vector_store()
    stats = await store.get_stats()
    
    return {
        "knowledge_base": stats,
        "config": {
            "model": settings.ollama_model,
            "relevance_threshold": settings.relevance_threshold,
            "max_web_searches": settings.max_web_searches
        }
    }


# ============== Run ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
