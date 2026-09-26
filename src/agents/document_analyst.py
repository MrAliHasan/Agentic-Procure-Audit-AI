"""
Document Analyst Agent - Specialized for document understanding
"""
import json
from src.llm.json_utils import loads_llm_json
from typing import Optional
from pathlib import Path

from src.agents.base import BaseAgent
from src.llm.prompts import DOCUMENT_EXTRACTOR_PROMPT
from src.tools.ocr import DocumentOCR
from src.models.document import Document


class DocumentAnalystAgent(BaseAgent):
    """
    Agent specialized in document analysis and extraction.
    
    Capabilities:
    - Extract structured data from documents
    - Compare documents
    - Identify discrepancies
    - Summarize document contents
    """
    
    INVOICE_FIELDS = [
        "vendor_name", "vendor_address", "invoice_number",
        "invoice_date", "due_date", "line_items",
        "subtotal", "tax", "total_amount", "payment_terms"
    ]
    
    CONTRACT_FIELDS = [
        "parties", "effective_date", "expiration_date",
        "contract_value", "payment_terms", "key_terms",
        "obligations", "termination_clause"
    ]
    
    BID_FIELDS = [
        "vendor_name", "bid_date", "valid_until",
        "total_price", "specifications", "delivery_terms",
        "warranty", "payment_terms"
    ]
    
    def __init__(self):
        """Initialize the Document Analyst."""
        super().__init__(
            name="Document Analyst",
            system_prompt=DOCUMENT_EXTRACTOR_PROMPT,
            temperature=0.1  # Very focused for extraction
        )
        self._ocr: Optional[DocumentOCR] = None
    
    def _get_ocr(self) -> DocumentOCR:
        """Get or create OCR engine."""
        if self._ocr is None:
            self._ocr = DocumentOCR()
        return self._ocr
    
    async def run(self, input_data: dict) -> dict:
        """
        Execute document analysis.
        
        Args:
            input_data: {
                "task": "extract" | "compare" | "summarize",
                "file_path": str,
                "doc_type": str,
                ...
            }
            
        Returns:
            Analysis results
        """
        task = input_data.get("task", "extract")
        
        if task == "extract":
            return await self.extract_document(
                input_data.get("file_path", ""),
                input_data.get("doc_type", "auto")
            )
        elif task == "compare":
            return await self.compare_documents(
                input_data.get("file_paths", [])
            )
        elif task == "summarize":
            return await self.summarize_document(
                input_data.get("file_path", "")
            )
        else:
            raise ValueError(f"Unknown task: {task}")
    
    async def extract_document(
        self,
        file_path: str,
        doc_type: str = "auto"
    ) -> dict:
        """
        Extract structured data from a document.
        
        Args:
            file_path: Path to document
            doc_type: Document type or "auto"
            
        Returns:
            Extracted data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        # OCR extraction
        ocr = self._get_ocr()
        text = await ocr.extract_text(str(file_path))
        confidence = await ocr.get_ocr_quality(str(file_path))
        
        if not text.strip():
            return {"error": "No text extracted from document"}
        
        # Auto-detect type if needed
        if doc_type == "auto":
            doc_type = self._detect_type(text)
        
        # Get fields for this type
        fields = self._get_fields(doc_type)
        
        # Extract with LLM
        prompt = f"""
        Extract the following fields from this {doc_type}:
        Fields: {', '.join(fields)}
        
        Document text:
        {text[:4000]}
        
        Return as JSON with each field as a key.
        For each field, provide the value and a confidence score (0-1).
        Example: {{"vendor_name": {{"value": "Acme Corp", "confidence": 0.95}}}}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                extracted = loads_llm_json(response)
            else:
                extracted = {}
        except json.JSONDecodeError:
            extracted = {}
        
        await self.close()
        
        return {
            "file_name": file_path.name,
            "doc_type": doc_type,
            "extracted_fields": extracted,
            "ocr_confidence": confidence,
            "text_length": len(text)
        }
    
    async def compare_documents(self, file_paths: list[str]) -> dict:
        """
        Compare multiple documents.
        
        Args:
            file_paths: Paths to documents
            
        Returns:
            Comparison results
        """
        extractions = []
        
        for path in file_paths:
            extraction = await self.extract_document(path)
            extraction["file_path"] = path
            extractions.append(extraction)
        
        # Compare with LLM
        prompt = f"""
        Compare these documents:
        
        {json.dumps(extractions, indent=2, default=str)}
        
        Identify:
        1. Common fields across all documents
        2. Discrepancies in values
        3. Missing information
        4. Recommendations
        
        Return as JSON: {{
            "common_fields": [...],
            "discrepancies": [...],
            "missing": [...],
            "recommendations": [...]
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                comparison = loads_llm_json(response)
            else:
                comparison = {"raw_comparison": response}
        except json.JSONDecodeError:
            comparison = {"raw_comparison": response}
        
        await self.close()
        
        return {
            "documents_compared": len(file_paths),
            "extractions": extractions,
            "comparison": comparison
        }
    
    async def summarize_document(self, file_path: str) -> dict:
        """
        Generate a summary of a document.
        
        Args:
            file_path: Path to document
            
        Returns:
            Document summary
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        ocr = self._get_ocr()
        text = await ocr.extract_text(str(file_path))
        
        if not text.strip():
            return {"error": "No text extracted"}
        
        prompt = f"""
        Summarize this document:
        
        {text[:4000]}
        
        Provide:
        1. Brief summary (2-3 sentences)
        2. Key points (bullet list)
        3. Document type
        4. Important dates/numbers
        
        Return as JSON: {{
            "summary": "...",
            "key_points": [...],
            "doc_type": "...",
            "important_data": {{}}
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                summary = loads_llm_json(response)
            else:
                summary = {"summary": response}
        except json.JSONDecodeError:
            summary = {"summary": response}
        
        await self.close()
        
        return {
            "file_name": file_path.name,
            **summary
        }
    
    def _detect_type(self, text: str) -> str:
        """Auto-detect document type from content."""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ["invoice", "bill to", "amount due"]):
            return "invoice"
        elif any(kw in text_lower for kw in ["contract", "agreement", "whereas"]):
            return "contract"
        elif any(kw in text_lower for kw in ["proposal", "quotation", "bid", "quote"]):
            return "bid"
        else:
            return "document"
    
    def _get_fields(self, doc_type: str) -> list[str]:
        """Get extraction fields for document type."""
        fields_map = {
            "invoice": self.INVOICE_FIELDS,
            "contract": self.CONTRACT_FIELDS,
            "bid": self.BID_FIELDS,
            "document": ["title", "date", "parties", "summary", "key_points"]
        }
        return fields_map.get(doc_type, fields_map["document"])
