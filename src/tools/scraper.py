"""
Web Scraper Tool - Vendor website scraping with anti-detection
"""
import asyncio
from typing import Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from src.models.vendor import Vendor


class VendorScraper:
    """
    Web scraper for extracting vendor information from websites.
    Uses httpx for basic scraping with option for Playwright for JS-heavy sites.
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the scraper.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
    
    async def scrape_vendor_website(self, url: str) -> dict:
        """
        Scrape basic information from a vendor website.
        
        Args:
            url: Vendor website URL
            
        Returns:
            Dict with extracted vendor info
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Extract basic info
                title = soup.title.string if soup.title else ""
                
                # Extract meta description
                meta_desc = ""
                meta_tag = soup.find("meta", {"name": "description"})
                if meta_tag:
                    meta_desc = meta_tag.get("content", "")
                
                # Extract contact info
                emails = self._extract_emails(response.text)
                phones = self._extract_phones(response.text)
                
                # Extract social links
                social_links = self._extract_social_links(soup)
                
                # Extract about text 
                about_text = self._extract_about_section(soup)
                
                return {
                    "url": url,
                    "domain": urlparse(url).netloc,
                    "title": title,
                    "description": meta_desc,
                    "about": about_text,
                    "emails": emails[:3],  # Limit to 3
                    "phones": phones[:3],
                    "social_links": social_links,
                    "success": True
                }
                
            except Exception as e:
                return {
                    "url": url,
                    "success": False,
                    "error": str(e)
                }
    
    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses from text."""
        import re
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, text)
        # Filter out common false positives
        filtered = [e for e in set(emails) if not any(x in e.lower() for x in ['example', 'test', 'sample'])]
        return list(filtered)
    
    def _extract_phones(self, text: str) -> list[str]:
        """Extract phone numbers from text."""
        import re
        # Common phone patterns
        patterns = [
            r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}'
        ]
        phones = []
        for pattern in patterns:
            phones.extend(re.findall(pattern, text))
        return list(set(phones))[:5]
    
    def _extract_social_links(self, soup: BeautifulSoup) -> dict:
        """Extract social media links."""
        social = {}
        social_domains = {
            'linkedin.com': 'linkedin',
            'twitter.com': 'twitter',
            'x.com': 'twitter',
            'facebook.com': 'facebook',
            'github.com': 'github'
        }
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            for domain, name in social_domains.items():
                if domain in href and name not in social:
                    social[name] = href
                    break
        
        return social
    
    def _extract_about_section(self, soup: BeautifulSoup) -> str:
        """Extract about/company section text."""
        # Try common about section selectors
        selectors = [
            {'id': 'about'},
            {'class_': 'about'},
            {'id': 'company'},
            {'class_': 'company-info'}
        ]
        
        for selector in selectors:
            section = soup.find(['section', 'div', 'article'], selector)
            if section:
                text = section.get_text(strip=True, separator=' ')
                if len(text) > 50:
                    return text[:500]  # Limit length
        
        # Fallback: get first substantial paragraph
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if len(text) > 100:
                return text[:500]
        
        return ""
    
    async def scrape_with_playwright(self, url: str) -> dict:
        """
        Scrape a JavaScript-heavy website using Playwright.
        
        Args:
            url: Website URL
            
        Returns:
            Dict with extracted content
        """
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Get rendered HTML
                content = await page.content()
                title = await page.title()
                
                await browser.close()
                
                soup = BeautifulSoup(content, "lxml")
                
                return {
                    "url": url,
                    "title": title,
                    "content": soup.get_text(strip=True, separator=' ')[:2000],
                    "success": True
                }
                
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    async def scrape_product_catalog(self, url: str) -> list[dict]:
        """
        Attempt to scrape product information from a catalog page.
        
        Args:
            url: Catalog/products page URL
            
        Returns:
            List of product dicts
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers,
            follow_redirects=True
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                products = []
                
                # Look for common product card patterns
                product_selectors = [
                    {'class_': 'product'},
                    {'class_': 'product-card'},
                    {'class_': 'product-item'},
                    {'itemtype': 'http://schema.org/Product'}
                ]
                
                for selector in product_selectors:
                    items = soup.find_all(['div', 'article', 'li'], selector, limit=20)
                    if items:
                        for item in items:
                            name = item.find(['h2', 'h3', 'h4', '.product-name'])
                            price = item.find(['span', 'div'], class_=lambda x: x and 'price' in x.lower())
                            
                            products.append({
                                "name": name.get_text(strip=True) if name else "",
                                "price": price.get_text(strip=True) if price else "",
                                "raw_text": item.get_text(strip=True)[:200]
                            })
                        break
                
                return products
                
            except Exception as e:
                return []


async def scrape_vendor(url: str) -> dict:
    """Convenience function to scrape a vendor website."""
    scraper = VendorScraper()
    return await scraper.scrape_vendor_website(url)
