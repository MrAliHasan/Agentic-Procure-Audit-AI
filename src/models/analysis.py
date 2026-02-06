"""
Analysis and Grading Models
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
import uuid


class ScoreDetail(BaseModel):
    """Detailed score for a single criterion."""
    score: int = Field(ge=0, le=100)
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0, le=1)


class VendorAnalysis(BaseModel):
    """Complete vendor analysis result."""
    id: str = Field(default_factory=lambda: f"analysis_{uuid.uuid4().hex[:12]}")
    vendor_id: str
    vendor_name: str
    
    # Overall assessment
    overall_score: int = Field(ge=0, le=100)
    recommendation: Literal["APPROVED", "REVIEW", "REJECTED"]
    
    # Score breakdown by criterion
    breakdown: dict[str, ScoreDetail] = Field(default_factory=dict)
    
    # Reasoning trace (for explainable AI)
    reasoning_chain: list[str] = Field(default_factory=list)
    
    # Sources used
    sources: list[str] = Field(default_factory=list)
    
    # Confidence in the analysis
    confidence: float = Field(ge=0, le=1)
    
    # Web research included
    web_research_used: bool = False
    web_sources: list[str] = Field(default_factory=list)
    
    # Metadata
    criteria_used: list[str] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_time_ms: Optional[int] = None
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class ComparisonReport(BaseModel):
    """Comparison report for multiple vendors."""
    id: str = Field(default_factory=lambda: f"comparison_{uuid.uuid4().hex[:12]}")
    
    # Vendors being compared
    vendor_analyses: list[VendorAnalysis] = Field(default_factory=list)
    
    # Rankings
    overall_ranking: list[str]  # Ordered list of vendor_ids
    criterion_rankings: dict[str, list[str]] = Field(default_factory=dict)
    
    # Winner
    recommended_vendor_id: Optional[str] = None
    recommendation_reasoning: str = ""
    
    # Summary
    summary: str = ""
    key_differences: list[str] = Field(default_factory=list)
    
    # Metadata
    criteria_used: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class MarketIntelligence(BaseModel):
    """Market intelligence report."""
    id: str = Field(default_factory=lambda: f"intel_{uuid.uuid4().hex[:12]}")
    query: str
    
    # Executive summary
    summary: str
    
    # Key findings
    findings: list[dict] = Field(default_factory=list)
    
    # Market trends
    trends: list[str] = Field(default_factory=list)
    
    # Pricing insights
    price_range: Optional[dict] = None
    price_trend: Optional[Literal["rising", "stable", "falling"]] = None
    
    # Risk factors
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    
    # Sources
    sources: list[dict] = Field(default_factory=list)
    
    # Metadata
    search_queries_used: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class RelevanceGrade(BaseModel):
    """Result of relevance grading."""
    score: float = Field(ge=0, le=1)
    reasoning: str
    decision: Literal["relevant", "not_relevant"]


class HallucinationCheck(BaseModel):
    """Result of hallucination detection."""
    is_grounded: bool
    issues: list[dict] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AnalysisRequest(BaseModel):
    """Request to analyze a vendor."""
    vendor_name: str
    vendor_id: Optional[str] = None
    criteria: list[str] = Field(default=["price", "quality", "reliability", "risk"])
    include_web_research: bool = True
    max_web_searches: int = 3


class SearchRequest(BaseModel):
    """Request to search for vendors."""
    query: str
    filters: dict = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=50)
    include_web_search: bool = False
