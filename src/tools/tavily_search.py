"""
Tavily Search Tool - Real-time web search for market intelligence

Uses AsyncTavilyClient for proper async support.
Leverages Tavily's advanced features: topic, time_range, include_answer, search_depth.
"""
import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from src.config import settings


class SearchResult(BaseModel):
    """A single search result."""
    title: str
    url: str
    content: str
    score: float = Field(default=0.0, ge=0, le=1)
    published_date: Optional[str] = None
    raw_content: Optional[str] = None


class TavilySearchTool:
    """
    Tavily API wrapper for AI-optimized web search.
    Provides real-time market intelligence and vendor research.
    
    Uses AsyncTavilyClient for native async support.
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the Tavily client.
        
        Args:
            api_key: Tavily API key (uses env if not provided)
        """
        self.api_key = api_key or settings.tavily_api_key
        if not self.api_key:
            raise ValueError("Tavily API key is required. Set TAVILY_API_KEY in .env")
        
        # Import here to avoid issues if not installed
        from tavily import AsyncTavilyClient
        self._client = AsyncTavilyClient(api_key=self.api_key)
    
    async def search(
        self,
        query: str,
        max_results: int = None,
        search_depth: str = "basic",
        topic: str = "general",
        time_range: str = None,
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_domains: list[str] = None,
        exclude_domains: list[str] = None
    ) -> list[SearchResult]:
        """
        Perform a web search.
        
        Args:
            query: Search query
            max_results: Maximum results to return (1-20)
            search_depth: "basic" or "advanced" (advanced = more thorough)
            topic: "general", "news", or "finance"
            time_range: "day", "week", "month", "year" or None
            include_answer: Include AI-generated answer
            include_raw_content: Include full page content
            include_domains: Only search these domains
            exclude_domains: Exclude these domains
            
        Returns:
            List of SearchResult objects
        """
        max_results = max_results or settings.tavily_max_results
        
        # Build search kwargs
        search_kwargs = {
            "query": query,
            "max_results": min(max_results, 20),  # Tavily max is 20
            "search_depth": search_depth,
            "topic": topic,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content
        }
        
        if time_range:
            search_kwargs["time_range"] = time_range
        
        if include_domains:
            search_kwargs["include_domains"] = include_domains
        
        if exclude_domains:
            search_kwargs["exclude_domains"] = exclude_domains
        
        # Use async client directly
        response = await self._client.search(**search_kwargs)
        
        # Parse results
        results = []
        for item in response.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=item.get("score", 0.0),
                published_date=item.get("published_date"),
                raw_content=item.get("raw_content")
            ))
        
        return results
    
    async def get_answer(self, question: str) -> str:
        """
        Get a direct AI-generated answer to a question.
        
        Uses advanced search depth for better answers.
        
        Args:
            question: Question to answer
            
        Returns:
            AI-generated answer string
        """
        response = await self._client.search(
            query=question,
            search_depth="advanced",
            include_answer=True,
            max_results=5
        )
        
        return response.get("answer", "No answer found.")
    
    async def search_vendor_info(
        self,
        vendor_name: str,
        aspects: list[str] = None
    ) -> dict:
        """
        Search for comprehensive vendor information.
        
        Args:
            vendor_name: Name of the vendor
            aspects: Specific aspects to research
            
        Returns:
            Dict with vendor intelligence
        """
        aspects = aspects or ["company overview", "reviews", "pricing", "news"]
        
        all_results = {}
        
        for aspect in aspects:
            query = f"{vendor_name} {aspect}"
            
            # Use news topic for news aspect
            topic = "news" if aspect == "news" else "general"
            
            results = await self.search(
                query, 
                max_results=3,
                topic=topic,
                search_depth="advanced" if aspect == "company overview" else "basic"
            )
            all_results[aspect] = [r.model_dump() for r in results]
        
        return {
            "vendor_name": vendor_name,
            "aspects_researched": aspects,
            "results": all_results,
            "total_sources": sum(len(r) for r in all_results.values())
        }
    
    async def search_market_trends(
        self,
        category: str,
        timeframe: str = "year"
    ) -> dict:
        """
        Search for market trends in a category.
        
        Args:
            category: Product/service category
            timeframe: Time range ("day", "week", "month", "year")
            
        Returns:
            Dict with market analysis
        """
        queries = [
            f"{category} market trends",
            f"{category} pricing trends",
            f"{category} top vendors suppliers",
            f"{category} industry outlook"
        ]
        
        all_results = []
        for query in queries:
            results = await self.search(
                query, 
                max_results=3,
                time_range=timeframe,
                search_depth="advanced"
            )
            all_results.extend([r.model_dump() for r in results])
        
        return {
            "category": category,
            "timeframe": timeframe,
            "queries_used": queries,
            "results": all_results,
            "total_sources": len(all_results)
        }
    
    async def search_vendor_risks(
        self,
        vendor_name: str
    ) -> dict:
        """
        Search for vendor risk factors.
        
        Args:
            vendor_name: Name of the vendor
            
        Returns:
            Dict with risk intelligence
        """
        queries = [
            f'"{vendor_name}" lawsuit OR legal issues',
            f'"{vendor_name}" financial problems OR bankruptcy',
            f'"{vendor_name}" complaints OR negative reviews',
            f'"{vendor_name}" security breach OR data leak'
        ]
        
        all_results = []
        for query in queries:
            results = await self.search(
                query, 
                max_results=2,
                topic="news",  # Use news for more recent/relevant results
                time_range="year"  # Last year's risks are most relevant
            )
            all_results.extend([{**r.model_dump(), "query": query} for r in results])
        
        # Determine risk level based on findings
        risk_level = "low"
        if len(all_results) > 5:
            risk_level = "high"
        elif len(all_results) > 2:
            risk_level = "medium"
        
        return {
            "vendor_name": vendor_name,
            "risk_level": risk_level,
            "risk_factors_found": len(all_results),
            "findings": all_results
        }
    
    async def search_finance(
        self,
        query: str,
        max_results: int = 5
    ) -> list[SearchResult]:
        """
        Search for financial information.
        
        Uses Tavily's finance topic for better results.
        
        Args:
            query: Financial query
            max_results: Maximum results
            
        Returns:
            List of finance-focused results
        """
        return await self.search(
            query,
            max_results=max_results,
            topic="finance",
            search_depth="advanced"
        )


# Convenience functions
async def web_search(query: str, max_results: int = 5) -> list[SearchResult]:
    """
    Simple web search function.
    
    Args:
        query: Search query
        max_results: Maximum results
        
    Returns:
        List of search results
    """
    tool = TavilySearchTool()
    return await tool.search(query, max_results)


async def get_web_answer(question: str) -> str:
    """
    Get a direct answer to a question from web search.
    
    Args:
        question: Question to answer
        
    Returns:
        AI-generated answer
    """
    tool = TavilySearchTool()
    return await tool.get_answer(question)
