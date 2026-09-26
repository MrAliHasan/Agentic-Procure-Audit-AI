"""
Lead Scraper Tool - Universal Lead Generation via Search + Scrape + Extract

A new standalone feature that:
1. Searches Google for any query (businesses, professionals, etc.)
2. Scrapes the resulting URLs concurrently
3. Extracts structured data (name, email, phone, address, website)
4. Returns clean JSON output

Does NOT modify any existing features.
"""

import asyncio
import re
import httpx
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse, unquote
from bs4 import BeautifulSoup

from src.config import settings


@dataclass
class Lead:
    """Extracted lead data."""
    name: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    source_url: str = ""
    snippet: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeadSearchResult:
    """Result from lead search."""
    query: str
    total_found: int = 0
    leads: List[Lead] = field(default_factory=list)
    search_time: float = 0.0
    scrape_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class LeadScraper:
    """
    Universal lead generation scraper.
    
    Usage:
        scraper = LeadScraper()
        results = await scraper.search_leads("dentists in Miami", max_results=20)
    """
    
    # Common email regex patterns
    EMAIL_PATTERNS = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ]
    
    # Phone patterns (US format)
    PHONE_PATTERNS = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
        r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
    ]
    
    # Domains to skip (not useful for lead gen)
    SKIP_DOMAINS = [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'yelp.com', 'yellowpages.com', 'google.com',
        'wikipedia.org', 'reddit.com', 'pinterest.com'
    ]
    
    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        max_concurrent: int = 10,
        timeout: int = 15,
    ):
        self.api_key = serper_api_key or settings.serper_api_key
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured")
        
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    
    async def _search_serper(
        self, 
        query: str, 
        num_results: int = 20,
        search_type: str = "search"
    ) -> List[Dict]:
        """Search via Serper API with pagination to get up to 20 results per query."""
        url = f"https://google.serper.dev/{search_type}"
        all_results = []
        
        # Serper returns max 10 per request, paginate for 20 results
        pages_needed = min(num_results // 10, 2)  # Max 2 pages = 20 results
        
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make parallel requests for all pages
            async def fetch_page(start: int):
                try:
                    payload = {
                        "q": query,
                        "num": 10,
                        "start": start,
                        "gl": "us",
                        "hl": "en",
                    }
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    results = data.get("organic", [])
                    if "places" in data:
                        results.extend(data.get("places", []))
                    return results
                except Exception:
                    return []
            
            # Fetch pages in parallel
            tasks = [fetch_page(i * 10) for i in range(pages_needed)]
            results = await asyncio.gather(*tasks)
            
            for page_results in results:
                all_results.extend(page_results)
        
        return all_results[:num_results]
    
    async def _fetch_url(self, url: str) -> Optional[Dict]:
        """Fetch a single URL and extract basic content."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove scripts and styles
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                
                text = soup.get_text(separator=' ', strip=True)
                
                return {
                    "url": url,
                    "html": html,
                    "text": text[:10000],  # Limit text size
                    "title": soup.title.string if soup.title else "",
                }
        except Exception as e:
            return {"url": url, "error": str(e)}
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email address."""
        # URL decode (handles %20 and other encoded chars)
        email = unquote(email).strip()
        
        # Remove leading/trailing special chars
        email = email.strip('.,;:!?\"\' ')
        
        # Remove any whitespace
        email = email.replace(' ', '').replace('\t', '').replace('\n', '')
        
        return email.lower()
    
    def _extract_emails(self, text: str, html: str = "") -> List[str]:
        """Extract email addresses from text."""
        emails = set()
        content = text + " " + html
        
        for pattern in self.EMAIL_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for email in matches:
                cleaned = self._clean_email(email)
                # Filter out common false positives
                if cleaned and not any(x in cleaned for x in ['example.com', 'domain.com', 'email.com', '.png', '.jpg', '.gif', 'wixpress', 'sentry']):
                    emails.add(cleaned)
        
        return list(emails)
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text."""
        phones = set()
        
        for pattern in self.PHONE_PATTERNS:
            matches = re.findall(pattern, text)
            phones.update(matches)
        
        return list(phones)
    
    def _extract_address(self, text: str) -> str:
        """Try to extract address from text."""
        # Look for common address patterns
        patterns = [
            r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)[\s,]+[\w\s]+,?\s*[A-Z]{2}\s*\d{5}',
            r'\d+\s+[\w\s]+,\s*[\w\s]+,\s*[A-Z]{2}\s*\d{5}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        
        return ""
    
    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            return any(skip in domain for skip in self.SKIP_DOMAINS)
        except Exception:
            return True
    
    async def _process_result(self, result: Dict) -> Optional[Lead]:
        """Process a search result into a Lead."""
        url = result.get("link", "")
        
        if not url or self._should_skip_url(url):
            return None
        
        lead = Lead(
            name=result.get("title", ""),
            website=url,
            source_url=url,
            snippet=result.get("snippet", ""),
        )
        
        # Handle places results (have structured data)
        if "address" in result:
            lead.address = result.get("address", "")
        if "phone" in result:
            lead.phone = result.get("phone", "")
        
        # Scrape the page for more data
        page_data = await self._fetch_url(url)
        
        if page_data and "error" not in page_data:
            text = page_data.get("text", "")
            html = page_data.get("html", "")
            
            # Extract emails
            emails = self._extract_emails(text, html)
            if emails:
                lead.email = emails[0]
                if len(emails) > 1:
                    lead.extra_data["all_emails"] = emails
            
            # Extract phones if not already set
            if not lead.phone:
                phones = self._extract_phones(text)
                if phones:
                    lead.phone = phones[0]
                    if len(phones) > 1:
                        lead.extra_data["all_phones"] = phones
            
            # Extract address if not already set
            if not lead.address:
                lead.address = self._extract_address(text)
        
        return lead
    
    async def search_leads(
        self,
        query: str,
        max_results: int = 20,
        include_places: bool = True,
    ) -> LeadSearchResult:
        """
        Search for leads matching a query.
        
        Args:
            query: Search query (e.g., "dentists in Miami")
            max_results: Maximum number of leads to return
            include_places: Also search Google Places for local businesses
        
        Returns:
            LeadSearchResult with extracted leads
        """
        import time
        start_time = time.time()
        
        result = LeadSearchResult(query=query)
        all_search_results = []
        
        try:
            # For large result sets, paginate with multiple Serper calls
            # Serper max per call is 100
            pages_needed = (max_results + 99) // 100  # Ceiling division
            
            for page in range(pages_needed):
                num_to_fetch = min(100, max_results - len(all_search_results))
                if num_to_fetch <= 0:
                    break
                
                # Add page offset to query for different results
                page_query = query if page == 0 else f"{query} page:{page + 1}"
                
                # Serper returns max 100 results per call (2 credits for 100)
                search_results = await self._search_serper(page_query, num_results=100)
                all_search_results.extend(search_results)
            
            # Also search places if requested (adds local business data)
            if include_places:
                try:
                    places = await self._search_serper(query, num_results=min(20, max_results), search_type="places")
                    all_search_results.extend(places)
                except Exception:
                    pass
            
            result.total_found = len(all_search_results)
            search_time = time.time()
            result.search_time = search_time - start_time
            
            # Process results concurrently
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_with_semaphore(r):
                async with semaphore:
                    return await self._process_result(r)
            
            tasks = [process_with_semaphore(r) for r in all_search_results[:max_results]]
            leads = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid leads
            for lead in leads:
                if isinstance(lead, Lead) and lead.name:
                    # Only include leads with at least some contact info
                    if lead.email or lead.phone or lead.address:
                        result.leads.append(lead)
            
            result.scrape_time = time.time() - search_time
            
        except Exception as e:
            result.errors.append(str(e))
        
        return result
    
    def leads_to_json(self, result: LeadSearchResult) -> List[Dict]:
        """Convert leads to JSON-serializable format."""
        return [
            {
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "address": lead.address,
                "website": lead.website,
                "snippet": lead.snippet,
                **lead.extra_data,
            }
            for lead in result.leads
        ]


# Convenience function for CLI
async def scrape_leads(
    query: str,
    max_results: int = 20,
) -> LeadSearchResult:
    """Scrape leads for a query."""
    scraper = LeadScraper()
    return await scraper.search_leads(query, max_results=max_results)
