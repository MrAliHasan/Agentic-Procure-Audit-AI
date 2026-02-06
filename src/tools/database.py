"""
Database Tools - LangGraph-compatible tools for vector store operations
"""
from langchain_core.tools import tool
from typing import Optional

from src.storage.chroma_store import get_vector_store
from src.models.vendor import Vendor


@tool
async def search_vendors(query: str, limit: int = 5) -> str:
    """
    Search for vendors in the knowledge base using semantic search.
    
    Args:
        query: Natural language search query
        limit: Maximum number of results to return
        
    Returns:
        JSON string with matching vendors and relevance scores
    """
    import json
    
    store = get_vector_store()
    results = await store.similarity_search(query, k=limit, collection="vendors")
    
    return json.dumps({
        "query": query,
        "count": len(results),
        "vendors": results
    }, indent=2)


@tool
async def get_vendor_by_id(vendor_id: str) -> str:
    """
    Retrieve a specific vendor by ID from the knowledge base.
    
    Args:
        vendor_id: The unique vendor identifier
        
    Returns:
        JSON string with vendor details or error message
    """
    import json
    
    store = get_vector_store()
    result = await store.get_by_id(vendor_id, collection="vendors")
    
    if result:
        return json.dumps(result, indent=2)
    else:
        return json.dumps({"error": f"Vendor {vendor_id} not found"})


@tool
async def save_vendor(
    name: str,
    description: str,
    website: str = None,
    industry: str = None,
    products: str = None
) -> str:
    """
    Save a new vendor to the knowledge base.
    
    Args:
        name: Vendor company name
        description: Description of the vendor and their offerings
        website: Vendor website URL
        industry: Industry category
        products: Comma-separated list of products/services
        
    Returns:
        JSON string with saved vendor ID
    """
    import json
    import uuid
    
    vendor_id = f"v_{uuid.uuid4().hex[:12]}"
    
    # Create searchable text
    text = f"{name}. {description}"
    if products:
        text += f" Products: {products}"
    
    # Metadata
    metadata = {
        "vendor_id": vendor_id,
        "name": name,
        "website": website or "",
        "industry": industry or "",
        "products": products or ""
    }
    
    store = get_vector_store()
    await store.add_documents(
        texts=[text],
        metadatas=[metadata],
        ids=[vendor_id],
        collection="vendors"
    )
    
    return json.dumps({
        "success": True,
        "vendor_id": vendor_id,
        "message": f"Vendor '{name}' saved successfully"
    })


@tool
async def search_documents(query: str, doc_type: str = None, limit: int = 5) -> str:
    """
    Search for documents in the knowledge base.
    
    Args:
        query: Search query
        doc_type: Optional filter by document type (invoice, contract, bid)
        limit: Maximum results
        
    Returns:
        JSON string with matching documents
    """
    import json
    
    store = get_vector_store()
    
    filter_metadata = None
    if doc_type:
        filter_metadata = {"type": doc_type}
    
    results = await store.similarity_search(
        query, 
        k=limit, 
        collection="documents",
        filter_metadata=filter_metadata
    )
    
    return json.dumps({
        "query": query,
        "doc_type_filter": doc_type,
        "count": len(results),
        "documents": results
    }, indent=2)


@tool
async def save_document(
    content: str,
    doc_type: str,
    source_file: str = None,
    vendor_name: str = None
) -> str:
    """
    Save a processed document to the knowledge base.
    
    Args:
        content: Extracted document text/content
        doc_type: Document type (invoice, contract, bid, catalog)
        source_file: Original file name
        vendor_name: Associated vendor if known
        
    Returns:
        JSON string with saved document ID
    """
    import json
    import uuid
    
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    metadata = {
        "doc_id": doc_id,
        "type": doc_type,
        "source_file": source_file or "",
        "vendor_name": vendor_name or ""
    }
    
    store = get_vector_store()
    await store.add_documents(
        texts=[content],
        metadatas=[metadata],
        ids=[doc_id],
        collection="documents"
    )
    
    return json.dumps({
        "success": True,
        "doc_id": doc_id,
        "message": f"Document saved successfully"
    })


@tool
async def get_knowledge_stats() -> str:
    """
    Get statistics about the knowledge base.
    
    Returns:
        JSON string with collection statistics
    """
    import json
    
    store = get_vector_store()
    stats = await store.get_stats()
    
    return json.dumps(stats, indent=2)
