"""
Intelligent Lead Scraper - LLM-Powered Lead Generation

Uses Groq LLM to intelligently generate search queries for maximum lead capture.
Supports both Groq (cloud) and Ollama (local) for flexibility.

Features:
- LLM generates diverse, intelligent search queries
- Adds email/contact-finding terms automatically
- Deduplicates results across multiple searches
- Extracts structured contact data
"""

import asyncio
import re
import json
import httpx
from typing import Optional, List, Dict, Any, Set
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
class IntelligentSearchResult:
    """Result from intelligent lead search."""
    query: str
    queries_generated: List[str] = field(default_factory=list)
    total_urls_found: int = 0
    leads: List[Lead] = field(default_factory=list)
    search_time: float = 0.0
    scrape_time: float = 0.0
    llm_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class GroqClient:
    """Simple Groq API client for query generation."""
    
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.groq_api_key
        self.model = model or settings.groq_model
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured. Set it in .env file.")
    
    async def query(self, prompt: str, system: Optional[str] = None) -> str:
        """Send a query to Groq LLM."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Groq API error {response.status_code}: {response.text}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
    
    async def query_json(self, prompt: str, system: Optional[str] = None) -> Dict:
        """Query and parse JSON response."""
        content = await self.query(prompt, system)
        
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Try array format
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                return {"queries": json.loads(json_match.group())}
            except json.JSONDecodeError:
                pass
        
        raise ValueError(f"No valid JSON in LLM response: {content[:200]}")


class IntelligentLeadScraper:
    """
    LLM-powered lead scraper that generates intelligent search queries.
    
    Instead of repeating the same query, it uses LLM to generate diverse
    queries that find more leads with contact information.
    """
    
    # Email patterns
    EMAIL_PATTERNS = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    ]
    
    # Phone patterns (US)
    PHONE_PATTERNS = [
        r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
    ]
    
    # Skip these domains
    SKIP_DOMAINS = [
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'yelp.com', 'yellowpages.com', 'google.com',
        'wikipedia.org', 'reddit.com', 'pinterest.com', 'mapquest.com'
    ]
    
    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        max_concurrent: int = 15,
        timeout: int = 12,
    ):
        self.serper_key = serper_api_key or settings.serper_api_key
        self.groq_key = groq_api_key or settings.groq_api_key
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        
        if not self.serper_key:
            raise ValueError("SERPER_API_KEY not configured")
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        
        # Track seen URLs to avoid duplicates
        self._seen_urls: Set[str] = set()
    
    async def _generate_search_queries(self, base_query: str, num_queries: int = 5) -> List[str]:
        """Use LLM to generate diverse search queries for lead generation."""
        
        if not self.groq_key:
            # Fallback to manual query variations if no LLM
            return self._generate_fallback_queries(base_query, num_queries)
        
        try:
            llm = GroqClient(api_key=self.groq_key)
            
            prompt = f"""Generate {num_queries} Google search queries to find leads with contact info for: "{base_query}"

RULES:
1. First query MUST be the original: "{base_query} contact email"
2. Include related profession/service variations
3. Mix broad queries (without quotes) and targeted queries (with "email" or "gmail")
4. Use different nearby locations/neighborhoods
5. Keep queries simple - don't over-complicate them

Example for "dentists Miami":
- dentists Miami contact email
- orthodontists Miami phone
- pediatric dentists South Beach email
- cosmetic dentists Coral Gables gmail
- dental clinic Miami Beach contact

Return ONLY a JSON array:
["query1", "query2", ...]"""

            result = await llm.query_json(prompt)
            queries = result.get("queries", result) if isinstance(result, dict) else result
            
            if isinstance(queries, list) and len(queries) > 0:
                # Always ensure base query is included  
                base_with_contact = f"{base_query} contact email"
                if base_with_contact not in queries:
                    queries = [base_with_contact] + queries[:num_queries-1]
                return queries[:num_queries]
            
        except Exception as e:
            print(f"LLM query generation failed: {e}, using fallback")
        
        return self._generate_fallback_queries(base_query, num_queries)
    
    def _generate_fallback_queries(self, base_query: str, num_queries: int) -> List[str]:
        """Generate query variations without LLM."""
        variations = [
            base_query,
            f"{base_query} email contact",
            f"{base_query} phone number",
            f"{base_query} gmail contact us",
            f"{base_query} website official",
            f"{base_query} near me reviews",
            f"best {base_query} contact information",
            f"{base_query} local business directory",
        ]
        return variations[:num_queries]
    
    async def _search_serper(self, query: str, num_results: int = 20) -> List[Dict]:
        """Search via Serper API with pagination to get up to 20 results per query."""
        url = "https://google.serper.dev/search"
        all_results = []
        
        # Serper returns max 10 per request, paginate for 20 results
        pages_needed = min(num_results // 10, 2)  # Max 2 pages = 20 results
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make parallel requests for all pages
            async def fetch_page(start: int):
                try:
                    response = await client.post(
                        url,
                        json={"q": query, "num": 10, "start": start, "gl": "us", "hl": "en"},
                        headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
                    )
                    response.raise_for_status()
                    return response.json().get("organic", [])
                except Exception:
                    return []
            
            # Fetch pages in parallel
            tasks = [fetch_page(i * 10) for i in range(pages_needed)]
            results = await asyncio.gather(*tasks)
            
            for page_results in results:
                all_results.extend(page_results)
        
        return all_results[:num_results]
    
    async def _search_places(self, query: str, num_results: int = 20) -> List[Dict]:
        """Search Google Places via Serper."""
        url = "https://google.serper.dev/places"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={"q": query, "num": min(num_results, 20), "gl": "us"},
                    headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json().get("places", [])
        except Exception:
            return []
    
    async def _fetch_url(self, url: str) -> Optional[Dict]:
        """Fetch a URL and extract content."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()
                
                html = response.text
                soup = BeautifulSoup(html, 'html.parser')
                
                for tag in soup(['script', 'style', 'nav', 'footer']):
                    tag.decompose()
                
                return {
                    "url": url,
                    "html": html,
                    "text": soup.get_text(separator=' ', strip=True)[:15000],
                    "title": soup.title.string if soup.title else "",
                }
        except Exception:
            return None
    
    def _clean_email(self, email: str) -> str:
        """Clean email address."""
        email = unquote(email).strip().strip('.,;:!?\"\' ')
        email = email.replace(' ', '').replace('\t', '').replace('\n', '')
        return email.lower()
    
    def _extract_emails(self, text: str, html: str = "") -> List[str]:
        """Extract emails from content."""
        emails = set()
        content = text + " " + html
        
        for pattern in self.EMAIL_PATTERNS:
            for match in re.findall(pattern, content, re.IGNORECASE):
                cleaned = self._clean_email(match)
                if cleaned and not any(x in cleaned for x in [
                    'example.com', 'domain.com', 'email.com', '.png', '.jpg', 
                    '.gif', 'wixpress', 'sentry', 'cloudflare'
                ]):
                    emails.add(cleaned)
        
        return list(emails)
    
    def _extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers."""
        phones = set()
        for pattern in self.PHONE_PATTERNS:
            phones.update(re.findall(pattern, text))
        return list(phones)
    
    def _should_skip(self, url: str) -> bool:
        """Check if URL should be skipped."""
        if url in self._seen_urls:
            return True
        try:
            domain = urlparse(url).netloc.replace("www.", "")
            return any(skip in domain for skip in self.SKIP_DOMAINS)
        except Exception:
            return True
    
    async def _process_result(self, result: Dict) -> Optional[Lead]:
        """Process a search result into a Lead."""
        url = result.get("link", "")
        
        if not url or self._should_skip(url):
            return None
        
        self._seen_urls.add(url)
        
        lead = Lead(
            name=result.get("title", ""),
            website=url,
            source_url=url,
            snippet=result.get("snippet", ""),
            address=result.get("address", ""),
            phone=result.get("phone", ""),
        )
        
        # Scrape page for contact info
        page = await self._fetch_url(url)
        
        if page:
            text = page.get("text", "")
            html = page.get("html", "")
            
            emails = self._extract_emails(text, html)
            if emails:
                lead.email = emails[0]
                if len(emails) > 1:
                    lead.extra_data["all_emails"] = emails
            
            if not lead.phone:
                phones = self._extract_phones(text)
                if phones:
                    lead.phone = phones[0]
        
        return lead
    
    async def search(
        self,
        query: str,
        max_leads: int = 50,
        num_search_queries: int = 5,
    ) -> IntelligentSearchResult:
        """
        Intelligently search for leads using LLM-generated queries.
        
        Args:
            query: Base search query (e.g., "dentists in Miami")
            max_leads: Maximum leads to return
            num_search_queries: Number of LLM-generated query variations
        
        Returns:
            IntelligentSearchResult with leads and metrics
        """
        import time
        start_time = time.time()
        
        result = IntelligentSearchResult(query=query)
        self._seen_urls.clear()
        
        try:
            # Step 1: Generate intelligent search queries using LLM
            llm_start = time.time()
            queries = await self._generate_search_queries(query, num_search_queries)
            result.queries_generated = queries
            result.llm_time = time.time() - llm_start
            
            # Step 2: Execute all searches in parallel
            search_start = time.time()
            all_results = []
            
            # Search with generated queries (100 results each for max coverage)
            search_tasks = [self._search_serper(q, num_results=100) for q in queries]
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            for sr in search_results:
                if isinstance(sr, list):
                    all_results.extend(sr)
            
            # Also search places
            places = await self._search_places(query)
            all_results.extend(places)
            
            result.total_urls_found = len(all_results)
            result.search_time = time.time() - search_start
            
            # Step 3: Process URLs concurrently
            scrape_start = time.time()
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_with_limit(r):
                async with semaphore:
                    return await self._process_result(r)
            
            # Limit to avoid too many requests - process 3x to account for failures
            to_process = all_results[:max_leads * 3]
            tasks = [process_with_limit(r) for r in to_process]
            leads = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter valid leads with contact info
            for lead in leads:
                if isinstance(lead, Lead) and lead.name:
                    if lead.email or lead.phone:
                        result.leads.append(lead)
                        if len(result.leads) >= max_leads:
                            break
            
            result.scrape_time = time.time() - scrape_start
            
            # Step 4: Auto-rotate - KEEP generating more queries until target is met
            rotation_count = 0
            max_rotations = 3  # Max 3 rotations to avoid infinite loop
            
            while len(result.leads) < max_leads and rotation_count < max_rotations:
                rotation_count += 1
                remaining = max_leads - len(result.leads)
                
                # Generate 5 more queries each rotation
                extra_queries = await self._generate_more_queries(query, result.queries_generated, 5)
                
                if not extra_queries:
                    break  # No more unique queries possible
                
                result.queries_generated.extend(extra_queries)
                
                # Search with new queries
                extra_tasks = [self._search_serper(q, num_results=100) for q in extra_queries]
                extra_results = await asyncio.gather(*extra_tasks, return_exceptions=True)
                
                extra_urls = []
                for sr in extra_results:
                    if isinstance(sr, list):
                        extra_urls.extend(sr)
                
                if not extra_urls:
                    break  # No more URLs found
                
                result.total_urls_found += len(extra_urls)
                
                # Process extra URLs - process 3x what we need
                to_process_extra = extra_urls[:remaining * 3]
                extra_lead_tasks = [process_with_limit(r) for r in to_process_extra]
                extra_leads = await asyncio.gather(*extra_lead_tasks, return_exceptions=True)
                
                for lead in extra_leads:
                    if isinstance(lead, Lead) and lead.name:
                        if lead.email or lead.phone:
                            result.leads.append(lead)
                            if len(result.leads) >= max_leads:
                                break
            
        except Exception as e:
            result.errors.append(str(e))
        
        return result
    
    async def _generate_more_queries(self, base_query: str, existing_queries: List[str], num: int) -> List[str]:
        """Generate additional queries that are different from existing ones."""
        if not self.groq_key:
            return []
        
        try:
            llm = GroqClient(api_key=self.groq_key)
            existing = ", ".join(existing_queries[:5])
            
            prompt = f"""Generate {num} MORE Google search queries for: "{base_query}"

These queries ALREADY EXIST, generate DIFFERENT ones:
{existing}

Create new variations with different keywords, locations, or related services.
Return ONLY a JSON array: ["query1", "query2", ...]"""

            result = await llm.query_json(prompt)
            queries = result.get("queries", result) if isinstance(result, dict) else result
            
            if isinstance(queries, list):
                return [q for q in queries if q not in existing_queries][:num]
        except Exception:
            pass
        
        return []


# CLI convenience function
async def intelligent_search(query: str, max_leads: int = 50) -> IntelligentSearchResult:
    """Run intelligent lead search."""
    scraper = IntelligentLeadScraper()
    return await scraper.search(query, max_leads=max_leads)
