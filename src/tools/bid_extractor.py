"""
Bid Extractor - Extract structured variables from tender/bid documents and analysis

Extracts:
- vendor_name: Winning or relevant vendor
- bid_date: Date of bid/tender
- valid_until: Bid validity period
- total_price: Bid amount (numeric)
- currency: Currency code
- specifications: Technical specs
- delivery_terms: Delivery period/terms
- warranty: Warranty terms

Each field has: value, confidence (0-1), source
"""
import re
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ExtractedField:
    """A single extracted field with confidence and source."""
    value: Optional[str | int | float] = None
    confidence: float = 0.0
    source: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BidVariables:
    """Structured bid/tender extraction results."""
    vendor_name: ExtractedField = field(default_factory=ExtractedField)
    bid_date: ExtractedField = field(default_factory=ExtractedField)
    valid_until: ExtractedField = field(default_factory=ExtractedField)
    total_price: ExtractedField = field(default_factory=ExtractedField)
    currency: ExtractedField = field(default_factory=ExtractedField)
    unit_prices: ExtractedField = field(default_factory=ExtractedField)
    specifications: ExtractedField = field(default_factory=ExtractedField)
    delivery_terms: ExtractedField = field(default_factory=ExtractedField)
    warranty: ExtractedField = field(default_factory=ExtractedField)
    tender_reference: ExtractedField = field(default_factory=ExtractedField)
    
    def to_dict(self) -> dict:
        return {
            "vendor_name": self.vendor_name.to_dict(),
            "bid_date": self.bid_date.to_dict(),
            "valid_until": self.valid_until.to_dict(),
            "total_price": self.total_price.to_dict(),
            "currency": self.currency.to_dict(),
            "unit_prices": self.unit_prices.to_dict(),
            "specifications": self.specifications.to_dict(),
            "delivery_terms": self.delivery_terms.to_dict(),
            "warranty": self.warranty.to_dict(),
            "tender_reference": self.tender_reference.to_dict(),
        }
    
    def to_summary(self) -> str:
        """Human-readable summary of extracted variables."""
        lines = []
        if self.vendor_name.value:
            lines.append(f"Vendor: {self.vendor_name.value} ({self.vendor_name.confidence:.0%})")
        if self.total_price.value:
            curr = self.currency.value or ""
            lines.append(f"Total Price: {curr} {self.total_price.value:,} ({self.total_price.confidence:.0%})")
        if self.bid_date.value:
            lines.append(f"Bid Date: {self.bid_date.value} ({self.bid_date.confidence:.0%})")
        if self.tender_reference.value:
            lines.append(f"Reference: {self.tender_reference.value}")
        if self.specifications.value:
            lines.append(f"Specs: {self.specifications.value[:100]}...")
        if self.delivery_terms.value:
            lines.append(f"Delivery: {self.delivery_terms.value}")
        if self.warranty.value:
            lines.append(f"Warranty: {self.warranty.value}")
        return "\n".join(lines) if lines else "No bid variables extracted"


class BidExtractor:
    """
    Extracts structured bid/tender variables from text content.
    Uses regex patterns + optional LLM enhancement.
    """
    
    # Currency patterns
    CURRENCY_PATTERNS = {
        "PKR": [r"Rs\.?\s*", r"PKR\s*", r"Rupees?\s*"],
        "USD": [r"\$\s*", r"USD\s*", r"US\s*Dollars?\s*"],
        "EUR": [r"€\s*", r"EUR\s*", r"Euros?\s*"],
        "GBP": [r"£\s*", r"GBP\s*", r"Pounds?\s*"],
    }
    
    # Price patterns (captures number with optional commas/decimals)
    PRICE_PATTERN = r"([\d,]+(?:\.\d{1,2})?)"
    
    def __init__(self):
        self.default_source = "document"
    
    def extract_from_text(
        self, 
        text: str, 
        source: str = "document",
        llm_analysis: dict = None,
        query_context: str = ""
    ) -> BidVariables:
        """
        Extract bid variables from text content.
        
        Args:
            text: Raw text content (from document or LLM output)
            source: Source identifier for extracted values
            llm_analysis: Optional LLM analysis dict to enhance extraction
            query_context: Original user query (for vendor matching priority)
            
        Returns:
            BidVariables with extracted fields
        """
        result = BidVariables()
        
        # Extract vendor name (with query context for priority)
        result.vendor_name = self._extract_vendor(text, source, query_context)
        
        # Extract prices with currency
        price_result = self._extract_price(text, source)
        result.total_price = price_result["price"]
        result.currency = price_result["currency"]
        result.unit_prices = self._extract_unit_prices(text, source)
        
        # Extract dates
        result.bid_date = self._extract_date(text, source, context="bid")
        result.valid_until = self._extract_date(text, source, context="valid")
        
        # Extract terms
        result.specifications = self._extract_specifications(text, source)
        result.delivery_terms = self._extract_delivery(text, source)
        result.warranty = self._extract_warranty(text, source)
        result.tender_reference = self._extract_reference(text, source)
        
        # Enhance with LLM analysis if provided
        if llm_analysis:
            result = self._enhance_with_llm(result, llm_analysis, source, query_context)
        
        return result
    
    def _extract_vendor(self, text: str, source: str, query_context: str = "") -> ExtractedField:
        """Extract vendor/company name, prioritizing vendors mentioned in query."""
        
        # PRIORITY 1: Check if a vendor in the query appears in the document
        if query_context:
            # Extract potential vendor names from query
            query_vendor_patterns = [
                r"from\s+([A-Z][A-Za-z0-9&\s.,-]+?)(?:\s|$)",
                r"([A-Z][A-Za-z0-9]{2,})\s+(?:bid|tender|vendor|company)",
                r"(?:bid|tender|vendor|company)\s+([A-Z][A-Za-z0-9]{2,})",
            ]
            
            for pattern in query_vendor_patterns:
                match = re.search(pattern, query_context, re.IGNORECASE)
                if match:
                    query_vendor = match.group(1).strip()
                    # Check if this vendor is mentioned in the document text
                    if query_vendor.lower() in text.lower():
                        # Look for M/S pattern or bid pattern with this vendor
                        vendor_pattern = rf"M/S\s*{re.escape(query_vendor)}|{re.escape(query_vendor)}(?:'s)?\s+bid"
                        if re.search(vendor_pattern, text, re.IGNORECASE):
                            return ExtractedField(
                                value=query_vendor,
                                confidence=0.95,  # High confidence - matched query
                                source=source
                            )
        
        # PRIORITY 2: Look for "declared" winner patterns (most specific)
        winner_patterns = [
            r"M/S\s+([A-Za-z][A-Za-z0-9&\s.,-]+?)\s+is\s+declared",
            r"([A-Za-z][A-Za-z0-9&\s.,-]+?)\s+is\s+declared\s+(?:responsive|winner)",
            r"awarded\s+to\s+([A-Z][A-Za-z0-9&\s.,-]+)",
        ]
        
        for pattern in winner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                vendor = re.sub(r'\s+(is|was|has|bid|tender).*$', '', vendor, flags=re.IGNORECASE)
                if len(vendor) > 2 and len(vendor) < 100:
                    return ExtractedField(
                        value=vendor.strip(),
                        confidence=0.9,
                        source=source
                    )
        
        # PRIORITY 3: General vendor patterns (fallback)
        patterns = [
            r"M/S\s+([A-Za-z][A-Za-z0-9&\s.,-]+?)(?:\s+is\s+declared|\s+bid|\s+with|\s*$)",
            r"([A-Z][A-Za-z0-9&\s.,-]+?)(?:'s)?\s+bid\s+(?:of|was|is)",
            r"winner[:\s]+([A-Z][A-Za-z0-9&\s.,-]+)",
            r"from\s+([A-Z][A-Za-z0-9&\s.,-]+?)(?:\s+at|\s+for|\s+with|\s*$)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                vendor = re.sub(r'\s+(is|was|has|bid|tender).*$', '', vendor, flags=re.IGNORECASE)
                if len(vendor) > 2 and len(vendor) < 100:
                    return ExtractedField(
                        value=vendor.strip(),
                        confidence=0.85,
                        source=source
                    )
        
        return ExtractedField()
    
    def _extract_price(self, text: str, source: str) -> dict:
        """Extract total price with currency."""
        price_field = ExtractedField()
        currency_field = ExtractedField()
        
        # Try each currency
        for currency, prefixes in self.CURRENCY_PATTERNS.items():
            for prefix in prefixes:
                pattern = prefix + self.PRICE_PATTERN
                matches = re.findall(pattern, text, re.IGNORECASE)
                
                if matches:
                    # Take the largest price (likely total)
                    prices = []
                    for match in matches:
                        try:
                            price = float(match.replace(",", ""))
                            prices.append(price)
                        except ValueError:
                            continue
                    
                    if prices:
                        max_price = max(prices)
                        price_field = ExtractedField(
                            value=max_price,
                            confidence=0.95,
                            source=source
                        )
                        currency_field = ExtractedField(
                            value=currency,
                            confidence=0.95,
                            source=source
                        )
                        return {"price": price_field, "currency": currency_field}
        
        return {"price": price_field, "currency": currency_field}
    
    def _extract_unit_prices(self, text: str, source: str) -> ExtractedField:
        """Extract unit prices if mentioned."""
        patterns = [
            r"(?:unit\s+price|per\s+unit|each)[:\s]*(?:Rs\.?|PKR|\$|USD)?\s*([\d,]+(?:\.\d{2})?)",
            r"@\s*(?:Rs\.?|PKR|\$|USD)?\s*([\d,]+(?:\.\d{2})?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1).replace(",", ""))
                    return ExtractedField(value=price, confidence=0.8, source=source)
                except ValueError:
                    continue
        
        return ExtractedField()
    
    def _extract_date(self, text: str, source: str, context: str = "bid") -> ExtractedField:
        """Extract dates from text."""
        # Date patterns
        patterns = [
            # "06 January, 2024" or "06 January 2024"
            r"\b(\d{1,2}\s+[A-Za-z]+,?\s+\d{4})\b",
            # "2024-01-06"
            r"\b(\d{4}-\d{2}-\d{2})\b",
            # "06/01/2024"
            r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
            # "January 6, 2024"
            r"\b([A-Za-z]+\s+\d{1,2},?\s+\d{4})\b",
        ]
        
        # Context-specific keywords
        if context == "valid":
            context_patterns = [r"valid\s+(?:until|till|through)[:\s]*", r"validity[:\s]*"]
        else:
            context_patterns = [r"date[:\s]*", r"dated[:\s]*", r"on[:\s]*"]
        
        # Try context-specific first
        for ctx_pattern in context_patterns:
            for date_pattern in patterns:
                full_pattern = ctx_pattern + date_pattern
                match = re.search(full_pattern, text, re.IGNORECASE)
                if match:
                    return ExtractedField(
                        value=match.group(1),
                        confidence=0.9,
                        source=source
                    )
        
        # Fallback: any date
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return ExtractedField(
                    value=match.group(1),
                    confidence=0.6,
                    source=source
                )
        
        return ExtractedField()
    
    def _extract_specifications(self, text: str, source: str) -> ExtractedField:
        """Extract technical specifications."""
        patterns = [
            r"specifications?[:\s]*([^\n]+(?:\n(?!\n)[^\n]+)*)",
            r"technical\s+details?[:\s]*([^\n]+(?:\n(?!\n)[^\n]+)*)",
            r"specs?[:\s]*([^\n]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                specs = match.group(1).strip()
                if len(specs) > 10:
                    return ExtractedField(value=specs[:500], confidence=0.7, source=source)
        
        return ExtractedField()
    
    def _extract_delivery(self, text: str, source: str) -> ExtractedField:
        """Extract delivery terms."""
        patterns = [
            r"delivery[:\s]*([^\n]+)",
            r"lead\s+time[:\s]*([^\n]+)",
            r"(?:within|in)\s+(\d+\s+(?:days?|weeks?|months?))",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return ExtractedField(value=match.group(1).strip(), confidence=0.8, source=source)
        
        return ExtractedField()
    
    def _extract_warranty(self, text: str, source: str) -> ExtractedField:
        """Extract warranty terms."""
        patterns = [
            r"warranty[:\s]*([^\n]+)",
            r"guarantee[:\s]*([^\n]+)",
            r"(\d+\s+(?:year|month)s?\s+warranty)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return ExtractedField(value=match.group(1).strip(), confidence=0.8, source=source)
        
        return ExtractedField()
    
    def _extract_reference(self, text: str, source: str) -> ExtractedField:
        """Extract tender/bid reference number."""
        patterns = [
            r"(?:tender|bid|reference|ref)\.?\s*(?:no\.?|number|#)?[:\s]*([A-Za-z0-9/-]+)",
            r"(?:PPRA|NIT|EOI)[:\s#-]*([A-Za-z0-9/-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ref = match.group(1).strip()
                if len(ref) > 3:
                    return ExtractedField(value=ref, confidence=0.85, source=source)
        
        return ExtractedField()
    
    def _enhance_with_llm(
        self, 
        result: BidVariables, 
        llm_analysis: dict,
        source: str,
        query_context: str = ""
    ) -> BidVariables:
        """Enhance extraction with LLM analysis data."""
        
        # Extract from LLM reasoning text
        breakdown = llm_analysis.get("breakdown", {})
        
        # Price reasoning often contains the actual price
        price_reasoning = breakdown.get("price", {}).get("reasoning", "")
        if price_reasoning and not result.total_price.value:
            price_result = self._extract_price(price_reasoning, f"{source} (LLM)")
            if price_result["price"].value:
                result.total_price = price_result["price"]
                result.currency = price_result["currency"]
        
        # Vendor from any reasoning (with query context priority)
        if not result.vendor_name.value:
            all_reasoning = " ".join([
                v.get("reasoning", "") for v in breakdown.values()
                if isinstance(v, dict)
            ])
            vendor = self._extract_vendor(all_reasoning, f"{source} (LLM)", query_context)
            if vendor.value:
                result.vendor_name = vendor
        
        return result


def extract_bid_variables(
    text: str,
    source: str = "document",
    llm_analysis: dict = None
) -> dict:
    """
    Convenience function to extract bid variables.
    
    Args:
        text: Document or analysis text
        source: Source identifier
        llm_analysis: Optional LLM analysis dict
        
    Returns:
        Dict with extracted variables
    """
    extractor = BidExtractor()
    result = extractor.extract_from_text(text, source, llm_analysis)
    return result.to_dict()
