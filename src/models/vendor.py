"""
Vendor Data Models
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
import uuid


class VendorContact(BaseModel):
    """Contact information for a vendor."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None


class VendorAddress(BaseModel):
    """Physical address of a vendor."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None


class Vendor(BaseModel):
    """Core vendor entity."""
    id: str = Field(default_factory=lambda: f"v_{uuid.uuid4().hex[:12]}")
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    
    # Categorization
    industry: Optional[str] = None
    categories: list[str] = Field(default_factory=list)
    products: list[str] = Field(default_factory=list)
    
    # Pricing
    pricing_tier: Optional[Literal["budget", "mid", "premium", "enterprise"]] = None
    currency: str = "USD"
    
    # Performance
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    total_reviews: int = 0
    
    # Risk
    risk_score: Optional[float] = Field(default=None, ge=0, le=100)
    risk_factors: list[str] = Field(default_factory=list)
    
    # Contact
    contacts: list[VendorContact] = Field(default_factory=list)
    address: Optional[VendorAddress] = None
    
    # Certifications
    certifications: list[str] = Field(default_factory=list)
    
    # Metadata
    source: Optional[str] = None  # Where this data came from
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class VendorProfile(BaseModel):
    """Extended vendor profile with rich intelligence."""
    vendor: Vendor
    
    # Financial info
    annual_revenue: Optional[float] = None
    employee_count: Optional[int] = None
    year_founded: Optional[int] = None
    
    # Performance history
    on_time_delivery_rate: Optional[float] = None
    quality_score: Optional[float] = None
    response_time_hours: Optional[float] = None
    
    # Competitive position
    market_share: Optional[float] = None
    competitors: list[str] = Field(default_factory=list)
    
    # News and updates
    recent_news: list[dict] = Field(default_factory=list)
    
    # Web research
    web_presence: dict = Field(default_factory=dict)


class VendorSearchResult(BaseModel):
    """Result from vendor search."""
    vendor: Vendor
    relevance_score: float = Field(ge=0, le=1)
    match_reasons: list[str] = Field(default_factory=list)


class VendorComparison(BaseModel):
    """Comparison between multiple vendors."""
    vendors: list[Vendor]
    comparison_criteria: list[str]
    rankings: dict[str, list[str]]  # criterion -> ordered list of vendor IDs
    winner: Optional[str] = None
    summary: str
