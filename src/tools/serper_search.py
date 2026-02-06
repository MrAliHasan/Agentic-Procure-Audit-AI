"""
Serper.dev Search Tool - Google Search API for comprehensive web research
"""
import httpx
from typing import Optional
from src.config import settings


class SerperSearchTool:
    """
    Async client for Serper.dev Google Search API.
    Provides access to Google search results, news, and more.
    """
    
    BASE_URL = "https://google.serper.dev"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.serper_api_key
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured")
        
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
    
    async def search(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        country: str = "us",
        lang: str = "en"
    ) -> dict:
        """
        Perform a Google search via Serper.
        
        Args:
            query: Search query
            num_results: Number of results (max 100)
            search_type: 'search', 'news', 'images', 'places'
            country: Country code (us, uk, etc)
            lang: Language code
        
        Returns:
            Search results with organic results, knowledge graph, etc.
        """
        endpoint = f"{self.BASE_URL}/{search_type}"
        
        payload = {
            "q": query,
            "num": min(num_results, 100),
            "gl": country,
            "hl": lang
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                endpoint,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def search_vendor_info(self, vendor_name: str, num_results: int = 10) -> dict:
        """Search for comprehensive vendor information."""
        queries = [
            f"{vendor_name} company overview products services",
            f"{vendor_name} reviews ratings customer feedback",
            f"{vendor_name} pricing cost comparison"
        ]
        
        all_results = []
        for query in queries:
            try:
                results = await self.search(query, num_results=num_results)
                organic = results.get("organic", [])
                all_results.extend(organic)
            except Exception as e:
                print(f"Serper search failed for '{query}': {e}")
        
        # Also check news
        try:
            news = await self.search(f"{vendor_name} news", search_type="news", num_results=5)
            all_results.extend(news.get("news", []))
        except Exception:
            pass
        
        return {
            "vendor": vendor_name,
            "results": all_results,
            "total": len(all_results)
        }
    
    async def search_vendor_risks(self, vendor_name: str) -> dict:
        """Search for vendor risk indicators."""
        risk_queries = [
            f"{vendor_name} lawsuit legal issues",
            f"{vendor_name} financial problems bankruptcy",
            f"{vendor_name} complaints problems issues",
            f"{vendor_name} recall defect quality issues"
        ]
        
        risk_results = []
        for query in risk_queries:
            try:
                results = await self.search(query, num_results=5)
                for result in results.get("organic", []):
                    result["risk_category"] = query.split()[-2]  # Extract category
                    risk_results.append(result)
            except Exception:
                pass
        
        # Calculate risk level based on findings
        risk_level = "low" if len(risk_results) < 3 else "medium" if len(risk_results) < 8 else "high"
        
        return {
            "vendor": vendor_name,
            "risk_level": risk_level,
            "risk_indicators": risk_results,
            "total_findings": len(risk_results)
        }
    
    async def search_market_trends(self, category: str, num_results: int = 15) -> dict:
        """Search for market trends in a category."""
        queries = [
            f"{category} market trends 2024 2025",
            f"{category} industry analysis forecast",
            f"{category} top suppliers manufacturers"
        ]
        
        all_results = []
        for query in queries:
            try:
                results = await self.search(query, num_results=num_results)
                all_results.extend(results.get("organic", []))
            except Exception:
                pass
        
        # Add news
        try:
            news = await self.search(f"{category} industry news", search_type="news", num_results=10)
            all_results.extend(news.get("news", []))
        except Exception:
            pass
        
        return {
            "category": category,
            "results": all_results,
            "total": len(all_results)
        }
    
    async def multi_search(self, queries: list[str], num_per_query: int = 10) -> list[dict]:
        """
        Perform multiple searches in parallel.
        Good for comprehensive research.
        """
        import asyncio
        
        tasks = [self.search(q, num_results=num_per_query) for q in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_organic = []
        for r in results:
            if isinstance(r, dict):
                all_organic.extend(r.get("organic", []))
        
        return all_organic
