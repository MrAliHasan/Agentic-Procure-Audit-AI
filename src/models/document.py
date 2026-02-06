"""
Document Data Models
"""
from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field
import uuid


class ExtractedField(BaseModel):
    """A single extracted field with confidence."""
    value: Any
    confidence: float = Field(ge=0, le=1)
    source_text: Optional[str] = None


class LineItem(BaseModel):
    """Line item from an invoice or order."""
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None
    sku: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class InvoiceData(BaseModel):
    """Extracted invoice data."""
    vendor_name: Optional[ExtractedField] = None
    vendor_address: Optional[ExtractedField] = None
    
    invoice_number: Optional[ExtractedField] = None
    invoice_date: Optional[ExtractedField] = None
    due_date: Optional[ExtractedField] = None
    
    subtotal: Optional[ExtractedField] = None
    tax: Optional[ExtractedField] = None
    total_amount: Optional[ExtractedField] = None
    currency: Optional[ExtractedField] = None
    
    payment_terms: Optional[ExtractedField] = None
    payment_method: Optional[ExtractedField] = None
    
    line_items: list[LineItem] = Field(default_factory=list)
    
    # Overall confidence for the extraction
    overall_confidence: float = Field(default=0.0, ge=0, le=1)


class ContractData(BaseModel):
    """Extracted contract data."""
    parties: list[ExtractedField] = Field(default_factory=list)
    effective_date: Optional[ExtractedField] = None
    expiration_date: Optional[ExtractedField] = None
    
    contract_value: Optional[ExtractedField] = None
    payment_terms: Optional[ExtractedField] = None
    
    key_terms: list[ExtractedField] = Field(default_factory=list)
    obligations: list[ExtractedField] = Field(default_factory=list)
    termination_clause: Optional[ExtractedField] = None
    
    overall_confidence: float = Field(default=0.0, ge=0, le=1)


class BidData(BaseModel):
    """Extracted bid/proposal data."""
    vendor_name: Optional[ExtractedField] = None
    bid_date: Optional[ExtractedField] = None
    valid_until: Optional[ExtractedField] = None
    
    total_price: Optional[ExtractedField] = None
    currency: Optional[ExtractedField] = None
    
    specifications: list[ExtractedField] = Field(default_factory=list)
    delivery_terms: Optional[ExtractedField] = None
    warranty: Optional[ExtractedField] = None
    
    line_items: list[LineItem] = Field(default_factory=list)
    
    overall_confidence: float = Field(default=0.0, ge=0, le=1)


class Table(BaseModel):
    """Extracted table from a document."""
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    page: Optional[int] = None
    confidence: float = Field(default=0.0, ge=0, le=1)


class Document(BaseModel):
    """Core document entity."""
    id: str = Field(default_factory=lambda: f"doc_{uuid.uuid4().hex[:12]}")
    type: Literal["invoice", "contract", "bid", "catalog", "other"]
    
    # File info
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    
    # Extracted content
    extracted_text: str = ""
    extracted_tables: list[Table] = Field(default_factory=list)
    page_count: int = 1
    
    # Structured extraction based on type
    extracted_fields: dict = Field(default_factory=dict)
    
    # Quality metrics
    confidence: float = Field(default=0.0, ge=0, le=1)
    ocr_quality: Optional[float] = None
    
    # Validation
    validation_status: Literal["pending", "valid", "invalid", "needs_review"] = "pending"
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    
    # Provenance
    source: Optional[str] = None
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[int] = None
    
    # Metadata
    metadata: dict = Field(default_factory=dict)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class DocumentProcessingRequest(BaseModel):
    """Request to process a document."""
    file_path: str
    document_type: Literal["invoice", "contract", "bid", "catalog", "auto"] = "auto"
    extract_tables: bool = True
    run_validation: bool = True  # Renamed from 'validate' to avoid shadowing BaseModel
    custom_fields: list[str] = Field(default_factory=list)


class DocumentProcessingResult(BaseModel):
    """Result of document processing."""
    document: Document
    processing_time_ms: int
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
