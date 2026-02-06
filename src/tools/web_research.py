"""
Web Research Tool - Combines Serper and Tavily for comprehensive research
Uses both APIs in parallel for maximum coverage
"""
import asyncio
from typing import Optional
from src.config import settings


class WebResearchTool:
    """
    Unified web research tool that combines Serper.dev and Tavily
    for comprehensive vendor research with fallback support.
    """
    
    def __init__(self):
        self._serper = None
        self._tavily = None
        self._init_tools()
    
    def _init_tools(self):
        """Initialize available search tools."""
        # Try Serper
        if settings.serper_api_key:
            try:
                from src.tools.serper_search import SerperSearchTool
                self._serper = SerperSearchTool()
            except Exception as e:
                print(f"Serper init failed: {e}")
        
        # Try Tavily
        if settings.tavily_api_key:
            try:
                from src.tools.tavily_search import TavilySearchTool
                self._tavily = TavilySearchTool()
            except Exception as e:
                print(f"Tavily init failed: {e}")
    
    @property
    def available_sources(self) -> list[str]:
        """Return list of available search sources."""
        sources = []
        if self._serper:
            sources.append("serper")
        if self._tavily:
            sources.append("tavily")
        return sources
    
    async def comprehensive_vendor_research(
        self,
        vendor_name: str,
        include_risks: bool = True,
        max_results_per_source: int = 15
    ) -> dict:
        """
        Perform comprehensive vendor research using all available sources.
        
        Returns combined results from both Serper and Tavily.
        """
        tasks = []
        
        # Serper searches
        if self._serper:
            tasks.append(self._serper_vendor_search(vendor_name, max_results_per_source))
            if include_risks:
                tasks.append(self._serper.search_vendor_risks(vendor_name))
        
        # Tavily searches
        if self._tavily:
            tasks.append(self._tavily_vendor_search(vendor_name, max_results_per_source))
            if include_risks:
                tasks.append(self._tavily.search_vendor_risks(vendor_name))
        
        if not tasks:
            return {"error": "No search APIs configured", "results": []}
        
        # Run all searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        combined = self._combine_results(results, vendor_name)
        
        return combined
    
    async def _serper_vendor_search(self, vendor_name: str, max_results: int) -> dict:
        """Perform multiple Serper searches for vendor info."""
        queries = [
            f"{vendor_name} company overview products services",
            f"{vendor_name} reviews ratings customer feedback",
            f"{vendor_name} pricing cost competitive analysis",
            f"{vendor_name} reliability delivery performance",
            f"{vendor_name} certifications compliance quality"
        ]
        
        all_results = []
        for query in queries:
            try:
                result = await self._serper.search(query, num_results=max_results)
                for item in result.get("organic", []):
                    item["source"] = "serper"
                    item["query"] = query
                    all_results.append(item)
            except Exception as e:
                print(f"Serper query failed: {e}")
        
        return {"results": all_results, "source": "serper"}
    
    async def _tavily_vendor_search(self, vendor_name: str, max_results: int) -> dict:
        """Perform Tavily searches for vendor info."""
        try:
            result = await self._tavily.search_vendor_info(vendor_name)
            for item in result.get("results", {}).get("general", []):
                item["source"] = "tavily"
            return {"results": result.get("results", {}).get("general", []), "source": "tavily"}
        except Exception as e:
            print(f"Tavily search failed: {e}")
            return {"results": [], "source": "tavily", "error": str(e)}
    
    def _combine_results(self, results: list, vendor_name: str) -> dict:
        """Combine and deduplicate results from multiple sources."""
        all_results = []
        seen_urls = set()
        risk_indicators = []
        
        for result in results:
            if isinstance(result, Exception):
                continue
            
            if isinstance(result, dict):
                # Handle vendor search results
                for item in result.get("results", []):
                    url = item.get("link") or item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet") or item.get("content", ""),
                            "url": url,
                            "source": item.get("source", "unknown")
                        })
                
                # Handle risk indicators
                for item in result.get("risk_indicators", []):
                    risk_indicators.append(item)
        
        return {
            "vendor": vendor_name,
            "results": all_results,
            "risk_indicators": risk_indicators,
            "total_results": len(all_results),
            "sources_used": self.available_sources
        }
    
    async def comprehensive_market_research(
        self,
        category: str,
        max_results_per_source: int = 20
    ) -> dict:
        """
        Perform comprehensive market research for a category.
        """
        tasks = []
        
        if self._serper:
            tasks.append(self._serper.search_market_trends(category, max_results_per_source))
        
        if self._tavily:
            tasks.append(self._tavily.search_market_trends(category))
        
        if not tasks:
            return {"error": "No search APIs configured", "results": []}
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        seen_urls = set()
        
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, dict):
                for item in result.get("results", []):
                    url = item.get("link") or item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet") or item.get("content", ""),
                            "url": url
                        })
        
        return {
            "category": category,
            "results": all_results,
            "total_results": len(all_results),
            "sources_used": self.available_sources
        }
    
    async def quick_search(self, query: str, num_results: int = 10) -> list[dict]:
        """
        Simple search across all available sources.
        Returns deduplicated results.
        """
        tasks = []
        
        if self._serper:
            tasks.append(self._serper.search(query, num_results=num_results))
        
        if self._tavily:
            tasks.append(self._tavily.search(query, max_results=num_results))
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        seen_urls = set()
        
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, dict):
                # Serper format
                for item in result.get("organic", []):
                    url = item.get("link", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": item.get("title", ""),
                            "content": item.get("snippet", ""),
                            "url": url,
                            "source": "serper"
                        })
                
                # Tavily format
                for item in result.get("results", []):
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            "title": item.get("title", ""),
                            "content": item.get("content", ""),
                            "url": url,
                            "source": "tavily"
                        })
        
        return all_results
    
    async def deep_research_with_scraping(
        self,
        query: str,
        max_urls_to_scrape: int = 10
    ) -> dict:
        """
        Deep research: Search + scrape full page content.
        
        This goes beyond snippets to get actual page content,
        including pricing, full product descriptions, etc.
        
        Args:
            query: Search query
            max_urls_to_scrape: Max URLs to fetch full content from
            
        Returns:
            Combined search results with full page content
        """
        from src.tools.url_scraper import URLScraperTool
        
        # Step 1: Get search results
        search_results = await self.quick_search(query, num_results=max_urls_to_scrape)
        
        if not search_results:
            return {"query": query, "results": [], "full_content": []}
        
        # Step 2: Extract URLs to scrape
        urls = [r["url"] for r in search_results if r.get("url")][:max_urls_to_scrape]
        
        # Step 3: Scrape full content from URLs
        scraper = URLScraperTool()
        scraped = await scraper.fetch_multiple(urls, max_concurrent=5)
        
        # Step 4: Combine results
        full_content = []
        for page in scraped:
            if page["success"]:
                full_content.append({
                    "url": page["url"],
                    "title": page["title"],
                    "content": page["content"][:5000],  # Limit per page
                    "links": page["links"][:10]
                })
        
        return {
            "query": query,
            "search_results": search_results,
            "full_content": full_content,
            "pages_scraped": len(full_content),
            "total_content_length": sum(len(p["content"]) for p in full_content)
        }
    
    async def search_documents_directly(
        self,
        topic: str,
        file_types: list[str] = None,
        max_documents: int = 10,
        save_dir: str = "./data/downloads"
    ) -> dict:
        """
        Search directly for documents (PDFs, etc.) ANYWHERE on the internet.
        
        Uses filetype: search operators to find documents hosted on:
        - Third-party sites
        - Industry databases
        - Government filings
        - Academic papers
        - Partner/distributor sites
        
        Args:
            topic: Search topic (vendor name, product, etc.)
            file_types: List of file types to search for
            max_documents: Max documents to download
            save_dir: Directory to save documents
            
        Returns:
            Downloaded documents with extracted text
        """
        from src.tools.url_scraper import URLScraperTool
        
        if file_types is None:
            file_types = ["pdf", "doc", "docx", "xls", "xlsx"]
        
        # Build filetype-specific search queries
        document_urls = []
        
        for file_type in file_types:
            queries = [
                f"{topic} filetype:{file_type}",
                f"{topic} datasheet filetype:{file_type}",
                f"{topic} specifications filetype:{file_type}",
                f"{topic} catalog filetype:{file_type}",
            ]
            
            for query in queries:
                results = await self.quick_search(query, num_results=5)
                for r in results:
                    url = r.get("url", "")
                    if url and url.lower().endswith(f".{file_type}"):
                        document_urls.append({
                            "url": url,
                            "title": r.get("title", ""),
                            "file_type": file_type
                        })
        
        # Deduplicate
        seen_urls = set()
        unique_docs = []
        for doc in document_urls:
            if doc["url"] not in seen_urls:
                seen_urls.add(doc["url"])
                unique_docs.append(doc)
        
        # Download and extract text
        scraper = URLScraperTool()
        downloaded = []
        extracted_texts = []
        
        for doc in unique_docs[:max_documents]:
            dl = await scraper.download_document(doc["url"], save_dir)
            if dl["success"]:
                downloaded.append(dl)
                
                # Extract text
                extracted = await scraper.extract_document_text(dl["local_path"])
                if extracted["success"]:
                    extracted_texts.append({
                        "filename": extracted["filename"],
                        "text": extracted["text"][:10000],
                        "source_url": doc["url"],
                        "title": doc["title"]
                    })
        
        return {
            "topic": topic,
            "documents_found": len(unique_docs),
            "documents_downloaded": len(downloaded),
            "downloads": downloaded,
            "extracted_texts": extracted_texts,
            "total_text_length": sum(len(t["text"]) for t in extracted_texts)
        }

    
    async def deep_vendor_research(
        self,
        vendor_name: str,
        include_pricing: bool = True,
        include_documents: bool = True,
        max_pages: int = 8
    ) -> dict:
        """
        Deep vendor research with full page scraping AND document download.
        
        Gets comprehensive vendor info including:
        - Full website content
        - Pricing information
        - Product details
        - Reviews and ratings
        - Downloaded PDFs/documents with OCR extraction
        
        Args:
            vendor_name: Vendor to research
            include_pricing: Whether to extract pricing info
            include_documents: Whether to download and OCR documents
            max_pages: Max pages to scrape
            
        Returns:
            Comprehensive vendor research data
        """
        from src.tools.url_scraper import URLScraperTool
        
        # Multi-query search for comprehensive coverage
        queries = [
            f"{vendor_name} products pricing catalog",
            f"{vendor_name} official website",
            f"{vendor_name} customer reviews ratings",
            f"{vendor_name} datasheet pdf specifications"  # Find documents
        ]
        
        all_urls = set()
        search_results = []
        
        # Collect URLs from multiple searches
        for query in queries:
            results = await self.quick_search(query, num_results=5)
            for r in results:
                url = r.get("url", "")
                if url and url not in all_urls:
                    all_urls.add(url)
                    search_results.append(r)
        
        # Scrape pages with document download
        scraper = URLScraperTool()
        urls_to_scrape = list(all_urls)[:max_pages]
        
        # Use comprehensive scrape if documents enabled
        if include_documents:
            scraped_result = await scraper.comprehensive_scrape_with_documents(
                urls_to_scrape,
                download_documents=True,
                max_docs_per_page=3,
                save_dir=f"./data/downloads/{vendor_name.replace(' ', '_').lower()}"
            )
            
            full_content = scraped_result["pages_scraped"]
            documents = scraped_result["documents_downloaded"]
            document_text = scraped_result["total_text_content"]
        else:
            # Basic scrape without documents
            scraped = await scraper.fetch_multiple(urls_to_scrape, max_concurrent=5)
            full_content = []
            documents = []
            document_text = ""
            
            for page in scraped:
                if page["success"]:
                    full_content.append({
                        "url": page["url"],
                        "title": page["title"],
                        "content": page["content"][:4000]
                    })
        
        # Extract pricing
        pricing_data = []
        if include_pricing:
            for url in urls_to_scrape[:5]:
                pricing = await scraper.extract_pricing_from_url(url)
                if pricing.get("prices"):
                    pricing_data.append(pricing)
        
        return {
            "vendor": vendor_name,
            "search_results": search_results,
            "full_content": full_content,
            "pricing_info": pricing_data,
            "documents_downloaded": documents,
            "document_text": document_text[:20000],  # Limit total doc text
            "pages_scraped": len(full_content),
            "documents_count": len(documents),
            "urls_found": list(all_urls),
            "sources_used": self.available_sources + ["url_scraper", "ocr"]
        }
    
    async def intelligent_research(
        self,
        query: str,
        num_results: int = 10
    ) -> dict:
        """
        Perform intelligent research using multi-step LLM-guided search.
        
        This method:
        1. Uses LLM to analyze the query and plan search strategy
        2. Executes multiple targeted searches
        3. Uses LLM to extract and synthesize information
        4. Returns structured, actionable data
        
        Best for complex queries like:
        - "Compare e-commerce platform fees in Pakistan"
        - "Find best suppliers for industrial equipment under $10k"
        - "What are vendor pricing trends for semiconductors 2026"
        
        Args:
            query: Natural language query
            num_results: Results per search
            
        Returns:
            dict with structured extracted data
        """
        try:
            from src.agents.intelligent_search import intelligent_search_agent
            
            result = await intelligent_search_agent(
                original_prompt=query,
                num_results=num_results
            )
            
            # Add metadata
            result["method"] = "intelligent_research"
            result["sources_used"] = self.available_sources + ["intelligent_search_agent"]
            
            return result
            
        except Exception as e:
            # Fall back to regular deep research
            print(f"Intelligent research failed: {e}, falling back to deep research")
            return await self.deep_research_with_scraping(
                query,
                max_urls_to_scrape=num_results
            )
    
    async def smart_url_extract(
        self,
        url: str,
        extraction_prompt: str
    ) -> dict:
        """
        SmartScraper-style extraction - fetch URL and use LLM to extract structured data.
        
        This works like ScrapeGraphAI's SmartScraperGraph - you provide a URL and
        describe what you want to extract, and it uses an LLM to intelligently
        extract that data.
        
        Example:
            result = await tool.smart_url_extract(
                url="https://example.com/products",
                extraction_prompt="Extract all product names and prices"
            )
        
        Args:
            url: URL to fetch and extract from
            extraction_prompt: Natural language description of what to extract
            
        Returns:
            dict with extracted structured data
        """
        try:
            from src.agents.intelligent_search import smart_url_extract
            
            result = await smart_url_extract(url, extraction_prompt)
            return result
            
        except Exception as e:
            return {
                "error": str(e),
                "url": url
            }
