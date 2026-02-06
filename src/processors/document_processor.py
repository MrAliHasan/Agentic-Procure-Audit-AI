"""
Document Processor - Ingestion pipeline for invoices, contracts, bids
"""
import json
import time
from pathlib import Path
from typing import Optional

from src.tools.ocr import DocumentOCR
from src.llm.ollama_client import OllamaClient
from src.llm.prompts import DOCUMENT_EXTRACTOR_PROMPT, get_extraction_prompt
from src.models.document import (
    Document, DocumentProcessingResult,
    InvoiceData, ContractData, BidData, ExtractedField
)


class DocumentProcessor:
    """
    Document processing pipeline for extracting structured data.
    Combines OCR with LLM for accurate field extraction.
    """
    
    INVOICE_FIELDS = [
        "vendor_name", "vendor_address", "invoice_number", "invoice_date",
        "due_date", "subtotal", "tax", "total_amount", "currency",
        "payment_terms", "line_items"
    ]
    
    CONTRACT_FIELDS = [
        "parties", "effective_date", "expiration_date", "contract_value",
        "payment_terms", "key_terms", "termination_clause"
    ]
    
    BID_FIELDS = [
        "vendor_name", "bid_date", "valid_until", "total_price",
        "currency", "specifications", "delivery_terms", "warranty"
    ]
    
    def __init__(self):
        self.ocr = DocumentOCR()
    
    async def process(
        self,
        file_path: str,
        doc_type: str = "auto",
        custom_fields: list[str] = None
    ) -> DocumentProcessingResult:
        """
        Process a document and extract structured data.
        
        Args:
            file_path: Path to the document
            doc_type: Document type or "auto" for detection
            custom_fields: Optional custom fields to extract
            
        Returns:
            DocumentProcessingResult with extracted data
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        if not file_path.exists():
            return DocumentProcessingResult(
                document=Document(
                    type="other",
                    file_path=str(file_path),
                    validation_status="invalid"
                ),
                processing_time_ms=0,
                errors=[f"File not found: {file_path}"]
            )
        
        warnings = []
        errors = []
        
        # Step 1: OCR extraction
        try:
            raw_text = await self.ocr.extract_text(str(file_path))
            ocr_quality = await self.ocr.get_ocr_quality(str(file_path))
        except Exception as e:
            errors.append(f"OCR failed: {str(e)}")
            raw_text = ""
            ocr_quality = 0.0
        
        if not raw_text.strip():
            errors.append("No text could be extracted from document")
            return DocumentProcessingResult(
                document=Document(
                    type=doc_type if doc_type != "auto" else "other",
                    file_path=str(file_path),
                    file_name=file_path.name,
                    extracted_text="",
                    validation_status="invalid"
                ),
                processing_time_ms=int((time.time() - start_time) * 1000),
                errors=errors
            )
        
        # Step 2: Auto-detect document type if needed
        if doc_type == "auto":
            doc_type = await self._detect_document_type(raw_text)
        
        # Step 3: Extract fields based on type
        fields_to_extract = custom_fields or self._get_fields_for_type(doc_type)
        
        try:
            extracted_fields = await self._extract_fields(raw_text, fields_to_extract)
        except Exception as e:
            warnings.append(f"Field extraction warning: {str(e)}")
            extracted_fields = {}
        
        # Step 4: Validate extraction
        validation_status, validation_errors = self._validate_extraction(
            doc_type, extracted_fields
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(extracted_fields, ocr_quality)
        
        # Build document
        document = Document(
            type=doc_type,
            file_path=str(file_path),
            file_name=file_path.name,
            file_size_bytes=file_path.stat().st_size,
            extracted_text=raw_text,
            extracted_fields=extracted_fields,
            confidence=confidence,
            ocr_quality=ocr_quality,
            validation_status=validation_status,
            validation_errors=validation_errors,
            validation_warnings=warnings
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return DocumentProcessingResult(
            document=document,
            processing_time_ms=processing_time,
            warnings=warnings,
            errors=errors
        )
    
    async def _detect_document_type(self, text: str) -> str:
        """Detect document type from content."""
        text_lower = text.lower()
        
        # Simple keyword-based detection
        if any(kw in text_lower for kw in ["invoice", "bill to", "due date", "amount due"]):
            return "invoice"
        elif any(kw in text_lower for kw in ["contract", "agreement", "party", "whereas"]):
            return "contract"
        elif any(kw in text_lower for kw in ["proposal", "quotation", "bid", "quote"]):
            return "bid"
        else:
            return "other"
    
    def _get_fields_for_type(self, doc_type: str) -> list[str]:
        """Get extraction fields for document type."""
        fields_map = {
            "invoice": self.INVOICE_FIELDS,
            "contract": self.CONTRACT_FIELDS,
            "bid": self.BID_FIELDS,
            "other": ["title", "date", "parties", "summary"]
        }
        return fields_map.get(doc_type, fields_map["other"])
    
    async def _extract_fields(
        self,
        text: str,
        fields: list[str]
    ) -> dict:
        """Use LLM to extract structured fields."""
        # Use longer timeout for document extraction (can be slow for large docs)
        llm = OllamaClient(timeout=1000)
        
        prompt = get_extraction_prompt(fields, text[:4000])  # Limit text length
        
        try:
            response = await llm.generate(
                prompt,
                system=DOCUMENT_EXTRACTOR_PROMPT,
                temperature=0.1
            )
            await llm.close()
            
            # Parse JSON from response
            if "{" in response and "}" in response:
                json_str = response[response.find("{"):response.rfind("}")+1]
                return json.loads(json_str)
            
            return {}
            
        except Exception as e:
            await llm.close()
            raise e
    
    def _validate_extraction(
        self,
        doc_type: str,
        fields: dict
    ) -> tuple[str, list[str]]:
        """Validate extracted fields."""
        errors = []
        
        # Check for required fields based on type
        required = {
            "invoice": ["vendor_name", "total_amount"],
            "contract": ["parties"],
            "bid": ["vendor_name", "total_price"]
        }
        
        req_fields = required.get(doc_type, [])
        for field in req_fields:
            if field not in fields or not fields[field]:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return "needs_review", errors
        
        return "valid", []
    
    def _calculate_confidence(
        self,
        fields: dict,
        ocr_quality: float
    ) -> float:
        """Calculate overall extraction confidence."""
        if not fields:
            return 0.0
        
        # Average field confidences
        field_confidences = []
        for field_data in fields.values():
            if isinstance(field_data, dict) and "confidence" in field_data:
                field_confidences.append(field_data["confidence"])
        
        avg_field_conf = sum(field_confidences) / len(field_confidences) if field_confidences else 0.5
        
        # Combine with OCR quality
        return (avg_field_conf * 0.7) + (ocr_quality * 0.3)


async def process_document(file_path: str, doc_type: str = "auto") -> Document:
    """Convenience function to process a document."""
    processor = DocumentProcessor()
    result = await processor.process(file_path, doc_type)
    return result.document
