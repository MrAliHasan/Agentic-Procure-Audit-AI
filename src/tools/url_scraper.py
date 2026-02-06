"""
URL Scraper Tool - Fetch full content from websites
Provides deep access to vendor pages, pricing, and documents
"""
import asyncio
import httpx
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class URLScraperTool:
    """
    Async URL scraper for fetching full page content.
    Goes beyond search snippets to get actual page data.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    async def fetch_url(self, url: str) -> dict:
        """
        Fetch full content from a URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Dict with title, text content, links, etc.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()
                
                # Get title
                title = soup.title.string if soup.title else ""
                
                # Get main text content
                text = soup.get_text(separator="\n", strip=True)
                
                # Limit text length
                text = text[:15000] if len(text) > 15000 else text
                
                # Get all links
                links = []
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http"):
                        links.append(href)
                    elif href.startswith("/"):
                        links.append(urljoin(url, href))
                
                return {
                    "url": url,
                    "title": title,
                    "content": text,
                    "links": links[:50],  # Limit to 50 links
                    "success": True
                }
                
        except Exception as e:
            return {
                "url": url,
                "title": "",
                "content": "",
                "links": [],
                "success": False,
                "error": str(e)
            }
    
    async def fetch_multiple(self, urls: list[str], max_concurrent: int = 5) -> list[dict]:
        """
        Fetch multiple URLs concurrently.
        
        Args:
            urls: List of URLs to fetch
            max_concurrent: Max concurrent requests
            
        Returns:
            List of results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url: str):
            async with semaphore:
                return await self.fetch_url(url)
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def extract_pricing_from_url(self, url: str) -> dict:
        """
        Extract pricing information from a page.
        Looks for common price patterns.
        """
        result = await self.fetch_url(url)
        
        if not result["success"]:
            return {"url": url, "prices": [], "error": result.get("error")}
        
        import re
        
        content = result["content"]
        
        # Find price patterns ($XX.XX, €XX.XX, etc.)
        price_patterns = [
            r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # $1,234.56
            r'€\d{1,3}(?:,\d{3})*(?:\.\d{2})?',   # €1,234.56
            r'£\d{1,3}(?:,\d{3})*(?:\.\d{2})?',   # £1,234.56
            r'USD\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            prices.extend(matches[:10])  # Limit per pattern
        
        return {
            "url": url,
            "title": result["title"],
            "prices": list(set(prices))[:20],  # Unique prices, max 20
            "success": True
        }
    
    async def deep_research_vendor(self, vendor_name: str, vendor_url: str = None) -> dict:
        """
        Deep research a vendor by scraping their website.
        
        Args:
            vendor_name: Name of vendor
            vendor_url: Optional URL (will search if not provided)
            
        Returns:
            Comprehensive vendor data
        """
        from src.tools.serper_search import SerperSearchTool
        from src.config import settings
        
        results = {
            "vendor": vendor_name,
            "pages_scraped": [],
            "pricing_info": [],
            "content_summary": "",
            "links_found": []
        }
        
        # Get URLs to scrape
        urls_to_scrape = []
        
        if vendor_url:
            urls_to_scrape.append(vendor_url)
        
        # Search for vendor pages
        if settings.serper_api_key:
            try:
                serper = SerperSearchTool()
                search_results = await serper.search(f"{vendor_name} official website pricing", num_results=5)
                
                for item in search_results.get("organic", []):
                    url = item.get("link", "")
                    if url and url not in urls_to_scrape:
                        urls_to_scrape.append(url)
            except Exception as e:
                print(f"Search failed: {e}")
        
        # Scrape the URLs
        if urls_to_scrape:
            scraped = await self.fetch_multiple(urls_to_scrape[:5])
            
            all_content = []
            for page in scraped:
                if page["success"]:
                    results["pages_scraped"].append({
                        "url": page["url"],
                        "title": page["title"],
                        "content_length": len(page["content"])
                    })
                    all_content.append(page["content"][:3000])
                    results["links_found"].extend(page["links"][:10])
            
            results["content_summary"] = "\n\n---\n\n".join(all_content)
        
        # Try to extract pricing
        for url in urls_to_scrape[:3]:
            pricing = await self.extract_pricing_from_url(url)
            if pricing.get("prices"):
                results["pricing_info"].append(pricing)
        
        return results
    
    # ============== Document Detection & Download ==============
    
    DOCUMENT_EXTENSIONS = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv",
        ".txt": "text/plain"
    }
    
    def detect_document_links(self, links: list[str]) -> list[dict]:
        """
        Detect document links from a list of URLs.
        
        Args:
            links: List of URLs
            
        Returns:
            List of document URLs with type info
        """
        documents = []
        
        for link in links:
            parsed = urlparse(link)
            path = parsed.path.lower()
            
            for ext, mime in self.DOCUMENT_EXTENSIONS.items():
                if path.endswith(ext):
                    documents.append({
                        "url": link,
                        "extension": ext,
                        "mime_type": mime,
                        "filename": path.split("/")[-1]
                    })
                    break
        
        return documents
    
    async def download_document(
        self,
        url: str,
        save_dir: str = "./data/downloads"
    ) -> dict:
        """
        Download a document from URL.
        
        Args:
            url: Document URL
            save_dir: Directory to save to
            
        Returns:
            Download result with local path
        """
        import os
        from pathlib import Path
        
        try:
            # Create save directory
            save_path = Path(save_dir)
            save_path.mkdir(parents=True, exist_ok=True)
            
            # Get filename from URL
            parsed = urlparse(url)
            filename = parsed.path.split("/")[-1]
            if not filename:
                filename = f"document_{hash(url)}.pdf"
            
            local_path = save_path / filename
            
            # Download
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                # Save to file
                with open(local_path, "wb") as f:
                    f.write(response.content)
            
            return {
                "url": url,
                "local_path": str(local_path),
                "filename": filename,
                "size_bytes": len(response.content),
                "success": True
            }
            
        except Exception as e:
            return {
                "url": url,
                "local_path": None,
                "success": False,
                "error": str(e)
            }
    
    async def download_multiple_documents(
        self,
        urls: list[str],
        save_dir: str = "./data/downloads",
        max_concurrent: int = 3
    ) -> list[dict]:
        """
        Download multiple documents concurrently.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(url: str):
            async with semaphore:
                return await self.download_document(url, save_dir)
        
        tasks = [download_with_semaphore(url) for url in urls]
        return await asyncio.gather(*tasks)
    
    async def extract_document_text(self, file_path: str) -> dict:
        """
        Extract text from a downloaded document using OCR.
        
        Args:
            file_path: Path to local document
            
        Returns:
            Extracted text and metadata
        """
        from pathlib import Path
        
        try:
            from src.tools.ocr import DocumentOCR
            
            path = Path(file_path)
            if not path.exists():
                return {"success": False, "error": "File not found"}
            
            ocr = DocumentOCR()
            text = await ocr.extract_text(str(path))
            
            return {
                "file_path": str(path),
                "filename": path.name,
                "text": text,
                "text_length": len(text),
                "success": True
            }
            
        except Exception as e:
            return {
                "file_path": file_path,
                "success": False,
                "error": str(e)
            }
    
    async def scrape_and_download_documents(
        self,
        url: str,
        max_documents: int = 5,
        save_dir: str = "./data/downloads"
    ) -> dict:
        """
        Scrape a page, find document links, download, and extract text.
        
        Full pipeline:
        1. Scrape page for document links
        2. Download documents
        3. OCR/extract text from each
        4. Return combined results
        
        Args:
            url: Page URL to scrape
            max_documents: Max docs to download
            save_dir: Where to save files
            
        Returns:
            Dict with documents and extracted text
        """
        result = {
            "source_url": url,
            "documents_found": [],
            "documents_downloaded": [],
            "extracted_text": [],
            "errors": []
        }
        
        # Step 1: Scrape page
        page = await self.fetch_url(url)
        if not page["success"]:
            result["errors"].append(f"Failed to scrape: {page.get('error')}")
            return result
        
        # Step 2: Find document links
        doc_links = self.detect_document_links(page["links"])
        result["documents_found"] = doc_links
        
        if not doc_links:
            return result
        
        # Step 3: Download documents
        urls_to_download = [d["url"] for d in doc_links[:max_documents]]
        downloads = await self.download_multiple_documents(urls_to_download, save_dir)
        
        for dl in downloads:
            if dl["success"]:
                result["documents_downloaded"].append(dl)
            else:
                result["errors"].append(f"Download failed: {dl.get('error')}")
        
        # Step 4: Extract text from downloaded documents
        for dl in result["documents_downloaded"]:
            if dl.get("local_path"):
                extracted = await self.extract_document_text(dl["local_path"])
                if extracted["success"]:
                    result["extracted_text"].append({
                        "filename": extracted["filename"],
                        "text": extracted["text"][:10000],  # Limit text
                        "source_url": dl["url"]
                    })
                else:
                    result["errors"].append(f"Extraction failed: {extracted.get('error')}")
        
        return result
    
    async def comprehensive_scrape_with_documents(
        self,
        urls: list[str],
        download_documents: bool = True,
        max_docs_per_page: int = 3,
        save_dir: str = "./data/downloads"
    ) -> dict:
        """
        Comprehensive scrape: pages + documents + OCR.
        
        Args:
            urls: URLs to scrape
            download_documents: Whether to download found documents
            max_docs_per_page: Max docs to download per page
            save_dir: Download directory
            
        Returns:
            Combined results with page content and document text
        """
        result = {
            "pages_scraped": [],
            "documents_downloaded": [],
            "total_text_content": "",
            "document_count": 0
        }
        
        all_text = []
        
        for url in urls:
            # Scrape page
            page = await self.fetch_url(url)
            if page["success"]:
                result["pages_scraped"].append({
                    "url": url,
                    "title": page["title"],
                    "content": page["content"][:5000]
                })
                all_text.append(page["content"][:3000])
                
                # Download documents if enabled
                if download_documents:
                    doc_result = await self.scrape_and_download_documents(
                        url, max_docs_per_page, save_dir
                    )
                    result["documents_downloaded"].extend(doc_result["documents_downloaded"])
                    
                    for extracted in doc_result["extracted_text"]:
                        all_text.append(f"\n--- Document: {extracted['filename']} ---\n{extracted['text']}")
                        result["document_count"] += 1
        
        result["total_text_content"] = "\n\n".join(all_text)
        
        return result

