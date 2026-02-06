"""
LangGraph State Definitions
"""
from typing import TypedDict, Optional, Annotated, Sequence
from operator import add

from src.models.vendor import Vendor
from src.models.document import Document
from src.models.analysis import VendorAnalysis, MarketIntelligence


class OrderIntelligenceState(TypedDict):
    """
    State for the main Order Intelligence workflow.
    Implements the Retrieve-Grade-Search-Generate loop.
    """
    # Input
    query: str
    criteria: list[str]
    
    # Retrieved data
    vendors: list[dict]
    documents: list[dict]
    
    # Web search results (if needed)
    web_results: list[dict]
    web_search_queries: Annotated[list[str], add]  # Accumulated
    
    # Grading
    relevance_scores: list[float]
    grade_decision: str  # "sufficient" or "needs_search"
    
    # LLM reasoning
    reasoning_steps: Annotated[list[str], add]  # Accumulated
    
    # Final output
    analysis: Optional[dict]
    bid_variables: Optional[dict]  # Structured bid data (vendor, price, currency, etc.)
    final_answer: str
    
    # Control flow
    iteration: int
    max_iterations: int
    error: Optional[str]


class VendorAnalysisState(TypedDict):
    """State for vendor analysis workflow."""
    # Input
    vendor_name: str
    vendor_id: Optional[str]
    criteria: list[str]
    include_web_research: bool
    
    # Data collection
    vendor_data: Optional[dict]
    web_research: list[dict]
    document_data: list[dict]
    
    # Analysis
    scores: dict  # criterion -> score
    reasoning: Annotated[list[str], add]
    
    # Output
    overall_score: int
    recommendation: str  # APPROVED, REVIEW, REJECTED
    confidence: float
    sources: list[str]
    
    # Control
    current_step: str
    error: Optional[str]


class DocumentProcessingState(TypedDict):
    """State for document processing workflow."""
    # Input
    file_path: str
    doc_type: str  # invoice, contract, bid, auto
    
    # Processing
    raw_text: str
    ocr_confidence: float
    tables: list[dict]
    
    # Extraction
    extracted_fields: dict
    extraction_confidence: float
    
    # Validation
    validation_status: str
    validation_errors: list[str]
    
    # Output
    document: Optional[dict]
    
    # Control
    current_step: str
    error: Optional[str]


class MarketResearchState(TypedDict):
    """State for market research workflow."""
    # Input
    query: str
    category: Optional[str]
    vendor_name: Optional[str]
    
    # Research
    search_queries: Annotated[list[str], add]
    search_results: list[dict]
    
    # Analysis
    findings: list[dict]
    trends: list[str]
    risks: list[str]
    opportunities: list[str]
    
    # Output
    summary: str
    intelligence: Optional[dict]
    
    # Control
    current_step: str
    error: Optional[str]


class AgentMessage(TypedDict):
    """Message format for agent communication."""
    role: str  # system, user, assistant, tool
    content: str
    tool_calls: Optional[list[dict]]
    tool_results: Optional[list[dict]]
