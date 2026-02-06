"""
OCR Tool - Document text extraction using Pytesseract
Optimized for CPU with 16GB RAM

Reference implementation from bestkaam-resume-parsing
"""
import asyncio
import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from src.models.document import Table


class DocumentOCR:
    """
    OCR engine for extracting text from documents.
    Uses Pytesseract for CPU-optimized text recognition.
    
    Pattern:
    1. For PDFs: Try native text extraction first (faster)
    2. Fall back to OCR if scanned/image-based PDF
    3. For images: Direct pytesseract
    """
    
    def __init__(self, lang: str = "eng", dpi: int = 300):
        """
        Initialize the OCR engine.
        
        Args:
            lang: Language for OCR (eng, deu, fra, etc.)
            dpi: DPI for PDF rendering (higher = better quality, slower)
        """
        self.lang = lang
        self.dpi = dpi
    
    async def extract_text(self, file_path: str) -> str:
        """
        Extract all text from a document.
        
        Args:
            file_path: Path to PDF or image file
            
        Returns:
            Extracted text as string
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = file_path.suffix.lower()
        
        # Handle PDF
        if ext == ".pdf":
            return await self._extract_from_pdf(file_path)
        
        # Handle images
        if ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            return await self._extract_from_image(str(file_path))
        
        # Handle text files
        if ext == ".txt":
            return file_path.read_text(encoding="utf-8", errors="ignore")
        
        raise ValueError(f"Unsupported file type: {ext}")
    
    async def _extract_from_image(self, image_path: str) -> str:
        """Extract text from an image file using pytesseract."""
        loop = asyncio.get_event_loop()
        
        def do_ocr():
            image = Image.open(image_path)
            # Convert to RGB if needed (e.g., RGBA PNGs)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            text = pytesseract.image_to_string(
                image,
                lang=self.lang,
                config='--psm 6'  # Assume uniform block of text
            )
            return text.strip()
        
        return await loop.run_in_executor(None, do_ocr)
    
    async def _extract_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file.
        - Native text extraction first (for digital PDFs)
        - OCR fallback for scanned PDFs
        """
        loop = asyncio.get_event_loop()
        
        def extract_pdf():
            doc = fitz.open(str(pdf_path))
            
            # Step 1: Try native text extraction
            native_text = ""
            for page in doc:
                native_text += page.get_text()
            
            # If substantial text found, return it (much faster)
            if len(native_text.strip()) > 100:
                doc.close()
                return native_text.strip()
            
            # Step 2: OCR fallback (scanned PDF)
            ocr_text_parts = []
            for page_num, page in enumerate(doc):
                # Render page to image at configured DPI
                pix = page.get_pixmap(dpi=self.dpi)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # OCR the image
                page_text = pytesseract.image_to_string(img, lang=self.lang)
                
                if page_text.strip():
                    ocr_text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
            
            doc.close()
            return "\n\n".join(ocr_text_parts).strip()
        
        return await loop.run_in_executor(None, extract_pdf)
    
    async def extract_with_confidence(self, file_path: str) -> dict:
        """
        Extract text with confidence scores.
        
        Args:
            file_path: Path to document
            
        Returns:
            Dict with text, confidence, and word-level data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"text": "", "confidence": 0.0, "words": []}
        
        loop = asyncio.get_event_loop()
        
        def do_ocr_with_confidence():
            ext = file_path.suffix.lower()
            
            # Get image to process
            if ext == ".pdf":
                doc = fitz.open(str(file_path))
                if not doc.page_count:
                    return {"text": "", "confidence": 0.0, "words": []}
                
                # Use first page for confidence check
                pix = doc[0].get_pixmap(dpi=self.dpi)
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            else:
                image = Image.open(str(file_path))
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
            
            # Get detailed OCR data
            data = pytesseract.image_to_data(
                image,
                lang=self.lang,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence (filter out -1 which means no text)
            confidences = [int(c) for c in data['conf'] if int(c) >= 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Get full text
            text = pytesseract.image_to_string(image, lang=self.lang)
            
            # Extract word-level data
            words = []
            for i, word in enumerate(data['text']):
                conf = int(data['conf'][i])
                if word.strip() and conf >= 0:
                    words.append({
                        'text': word,
                        'confidence': conf / 100,
                        'left': data['left'][i],
                        'top': data['top'][i],
                        'width': data['width'][i],
                        'height': data['height'][i]
                    })
            
            return {
                "text": text.strip(),
                "confidence": avg_confidence / 100,  # Convert to 0-1 scale
                "words": words
            }
        
        return await loop.run_in_executor(None, do_ocr_with_confidence)
    
    async def extract_tables(self, file_path: str) -> list[Table]:
        """
        Extract tables from a document.
        Note: For advanced table extraction, consider camelot-py or tabula-py.
        
        Args:
            file_path: Path to PDF or image file
            
        Returns:
            List of extracted tables
        """
        # Basic implementation - for full table support integrate camelot/tabula
        return []
    
    async def get_ocr_quality(self, file_path: str) -> float:
        """
        Estimate OCR quality/confidence for a document.
        
        Args:
            file_path: Path to document
            
        Returns:
            Quality score 0.0 to 1.0
        """
        result = await self.extract_with_confidence(file_path)
        return result.get("confidence", 0.0)


async def extract_document_text(file_path: str) -> str:
    """
    Convenience function to extract text from a document.
    
    Args:
        file_path: Path to document
        
    Returns:
        Extracted text
    """
    ocr = DocumentOCR()
    return await ocr.extract_text(file_path)
