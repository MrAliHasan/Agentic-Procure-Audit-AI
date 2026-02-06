"""
Smart Fetcher - Reliable web fetching with automatic HTTP→Browser fallback
Adapted from OmniExtract-AI's scrapling_fetcher.py
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup


@dataclass
class FetchResult:
    """Result of a fetch operation."""
    html: str
    status: int
    url: str
    method: str  # "http" or "browser"
    elapsed_ms: int
    success: bool
    error: Optional[str] = None


class SmartFetcher:
    """
    Smart web fetcher that tries fast HTTP first, then falls back to browser mode.
    
    Usage:
        fetcher = SmartFetcher()
        result = await fetcher.fetch("https://example.com")
        if result.success:
            print(result.html)
    """
    
    def __init__(
        self,
        default_timeout: int = 30,
        retry_with_browser: bool = True,
        headers: Optional[dict] = None
    ):
        """
        Initialize the fetcher.
        
        Args:
            default_timeout: Request timeout in seconds
            retry_with_browser: If True, retry with browser on HTTP failure
            headers: Custom headers for HTTP requests
        """
        self.default_timeout = default_timeout
        self.retry_with_browser = retry_with_browser
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Stats
        self.http_attempts = 0
        self.http_successes = 0
        self.browser_attempts = 0
        self.browser_successes = 0
    
    async def fetch(
        self,
        url: str,
        timeout: Optional[int] = None,
        force_browser: bool = False
    ) -> FetchResult:
        """
        Fetch a URL with automatic fallback.
        
        Strategy:
        1. Try fast HTTP fetch (httpx)
        2. If fails/blocked → Use browser mode (Playwright)
        
        Args:
            url: URL to fetch
            timeout: Request timeout (uses default if not specified)
            force_browser: Skip HTTP and use browser directly
            
        Returns:
            FetchResult with html, status, method used
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        # Skip HTTP if forcing browser
        if force_browser:
            return await self._browser_fetch(url, timeout, start_time)
        
        # Try HTTP first (fast)
        http_result = await self._http_fetch(url, timeout)
        
        if http_result.success:
            return http_result
        
        # If HTTP failed and browser fallback is enabled
        if self.retry_with_browser:
            return await self._browser_fetch(url, timeout, start_time)
        
        return http_result
    
    async def _http_fetch(self, url: str, timeout: int) -> FetchResult:
        """Fast HTTP fetch using httpx."""
        self.http_attempts += 1
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(timeout),
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                html = response.text
                
                # Check if we got blocked
                if self._is_blocked(html, response.status_code):
                    return FetchResult(
                        html="",
                        status=response.status_code,
                        url=str(response.url),
                        method="http",
                        elapsed_ms=int((time.time() - start_time) * 1000),
                        success=False,
                        error="Blocked by anti-bot protection"
                    )
                
                self.http_successes += 1
                return FetchResult(
                    html=html,
                    status=response.status_code,
                    url=str(response.url),
                    method="http",
                    elapsed_ms=int((time.time() - start_time) * 1000),
                    success=True
                )
                
        except Exception as e:
            return FetchResult(
                html="",
                status=0,
                url=url,
                method="http",
                elapsed_ms=int((time.time() - start_time) * 1000),
                success=False,
                error=str(e)
            )
    
    async def _browser_fetch(
        self,
        url: str,
        timeout: int,
        overall_start_time: Optional[float] = None
    ) -> FetchResult:
        """Browser-based fetch using Playwright."""
        self.browser_attempts += 1
        start_time = overall_start_time or time.time()
        
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return FetchResult(
                html="",
                status=0,
                url=url,
                method="browser",
                elapsed_ms=int((time.time() - start_time) * 1000),
                success=False,
                error="Playwright not installed"
            )
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=self.headers.get("User-Agent"),
                    viewport={"width": 1920, "height": 1080}
                )
                
                page = await context.new_page()
                
                # Navigate with timeout
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)
                
                html = await page.content()
                
                await browser.close()
                
                self.browser_successes += 1
                return FetchResult(
                    html=html,
                    status=200,
                    url=url,
                    method="browser",
                    elapsed_ms=int((time.time() - start_time) * 1000),
                    success=True
                )
                
        except Exception as e:
            return FetchResult(
                html="",
                status=0,
                url=url,
                method="browser",
                elapsed_ms=int((time.time() - start_time) * 1000),
                success=False,
                error=str(e)
            )
    
    def _is_blocked(self, html: str, status_code: int) -> bool:
        """Check if the response indicates we've been blocked."""
        if status_code in [403, 429, 503]:
            return True
        
        block_indicators = [
            "access denied",
            "blocked",
            "captcha",
            "please verify you are a human",
            "robot check",
            "rate limit",
            "too many requests",
            "cloudflare",
            "ddos protection"
        ]
        
        html_lower = html.lower()[:5000]  # Only check first 5KB
        return any(indicator in html_lower for indicator in block_indicators)
    
    def get_stats(self) -> dict:
        """Get fetch statistics."""
        return {
            "http_attempts": self.http_attempts,
            "http_successes": self.http_successes,
            "http_success_rate": self.http_successes / max(self.http_attempts, 1),
            "browser_attempts": self.browser_attempts,
            "browser_successes": self.browser_successes,
            "browser_success_rate": self.browser_successes / max(self.browser_attempts, 1)
        }


# Singleton instance
_default_fetcher = None


def get_fetcher() -> SmartFetcher:
    """Get the default fetcher instance."""
    global _default_fetcher
    if _default_fetcher is None:
        _default_fetcher = SmartFetcher()
    return _default_fetcher


async def smart_fetch(
    url: str,
    timeout: int = 30,
    force_browser: bool = False
) -> FetchResult:
    """
    Convenience function to fetch a URL.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        force_browser: Skip HTTP and use browser directly
        
    Returns:
        FetchResult with html, status, method used
    """
    fetcher = get_fetcher()
    return await fetcher.fetch(url, timeout, force_browser)


async def fetch_html(
    url: str,
    timeout: int = 30,
    force_browser: bool = False
) -> str:
    """
    Fetch HTML content from a URL.
    
    Returns:
        HTML string or empty string on failure
    """
    result = await smart_fetch(url, timeout, force_browser)
    return result.html if result.success else ""


async def fetch_and_parse(
    url: str,
    timeout: int = 30,
    force_browser: bool = False
) -> Optional[BeautifulSoup]:
    """
    Fetch URL and return parsed BeautifulSoup object.
    
    Returns:
        BeautifulSoup object or None on failure
    """
    html = await fetch_html(url, timeout, force_browser)
    if html:
        return BeautifulSoup(html, "html.parser")
    return None
