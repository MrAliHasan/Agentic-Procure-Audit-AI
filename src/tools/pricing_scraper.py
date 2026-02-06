"""
Pricing Scraper - Aggressive extraction of real prices from ANY vendor/platform
Supports: Electronic distributors, E-commerce platforms, SaaS products, General vendors
"""
import asyncio
import re
import httpx
from typing import Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, quote_plus


class PricingScraperTool:
    """
    Universal pricing scraper that works for:
    - Electronic component distributors (Mouser, DigiKey, etc.)
    - E-commerce platforms (Shopify, Daraz, WooCommerce, etc.)
    - SaaS products (subscription pricing)
    - General product pages
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        # Distributor-specific pricing patterns (electronics)
        self.price_patterns = {
            "mouser": [
                r'(?:Price|Unit Price)[:\s]*\$?([\d,]+\.?\d*)',
                r'"price"[:\s]*"?\$?([\d,]+\.?\d*)"?',
                r'class="[^"]*price[^"]*"[^>]*>\s*\$?([\d,]+\.?\d*)',
            ],
            "digikey": [
                r'(?:Unit Price|Price)[:\s]*\$?([\d,]+\.?\d*)',
                r'"unitPrice"[:\s]*"?\$?([\d,]+\.?\d*)"?',
                r'data-price="([\d,]+\.?\d*)"',
            ],
            "arrow": [
                r'(?:Price)[:\s]*\$?([\d,]+\.?\d*)',
                r'"price"[:\s]*([\d,]+\.?\d*)',
            ],
            "newark": [
                r'(?:Price|Each)[:\s]*\$?([\d,]+\.?\d*)',
            ],
            "rs-online": [
                r'(?:Price)[:\s]*\$?([\d,]+\.?\d*)',
            ],
            # E-commerce platform patterns
            "ecommerce": [
                r'(?:commission|fee)[:\s]*(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)\s*%\s*(?:commission|fee|per sale)',
                r'(?:monthly|annual)[:\s]*(?:PKR|Rs\.?|USD|\$)\s*([\d,]+)',
                r'(?:PKR|Rs\.?)\s*([\d,]+)(?:/month|/year)?',
                r'(?:starting|from)[:\s]*(?:PKR|Rs\.?|\$)?\s*([\d,]+)',
                r'(\d+(?:\.\d+)?)\s*%\s*(?:transaction|payment)',
                r'(?:subscription|plan)[:\s]*\$?([\d,]+)',
            ],
            # SaaS pricing patterns
            "saas": [
                r'\$([\d,]+(?:\.\d+)?)\s*/\s*(?:mo|month)',
                r'\$([\d,]+(?:\.\d+)?)\s*/\s*(?:yr|year)',
                r'(?:Basic|Pro|Enterprise)[:\s]*\$([\d,]+)',
                r'(?:free trial|free plan)',
                r'(\d+)\s*(?:day|month)\s*free',
            ],
            "generic": [
                r'\$\s*([\d,]+\.?\d{0,2})',
                r'USD\s*([\d,]+\.?\d{0,2})',
                r'(?:price|Price)[:\s]*\$?([\d,]+\.?\d*)',
                r'(?:cost|Cost)[:\s]*\$?([\d,]+\.?\d*)',
                r'PKR\s*([\d,]+)',
                r'Rs\.?\s*([\d,]+)',
            ]
        }
        
        # Keywords to detect query type
        self.ecommerce_keywords = [
            "shopify", "woocommerce", "daraz", "amazon", "alibaba", "olx",
            "ebay", "magento", "prestashop", "bigcommerce", "platform",
            "e-commerce", "ecommerce", "marketplace", "seller fees",
            "commission", "vendor fees"
        ]
        self.saas_keywords = [
            "software", "subscription", "saas", "cloud", "monthly plan",
            "enterprise", "pro plan", "pricing page"
        ]

    
    def _identify_distributor(self, url: str) -> str:
        """Identify distributor from URL."""
        domain = urlparse(url).netloc.lower()
        
        if "mouser" in domain:
            return "mouser"
        elif "digikey" in domain:
            return "digikey"
        elif "arrow" in domain:
            return "arrow"
        elif "newark" in domain:
            return "newark"
        elif "rs-online" in domain or "rsdelivers" in domain:
            return "rs-online"
        else:
            return "generic"
    
    async def scrape_product_page(self, url: str) -> dict:
        """
        Scrape a product page for pricing information.
        
        Returns structured pricing data.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                html = response.text
                soup = BeautifulSoup(html, "lxml")
                
                # Remove scripts/styles
                for element in soup(["script", "style"]):
                    element.decompose()
                
                text = soup.get_text(separator=" ", strip=True)
                
                # Identify distributor and use appropriate patterns
                distributor = self._identify_distributor(url)
                patterns = self.price_patterns.get(distributor, self.price_patterns["generic"])
                
                # Extract prices
                prices = []
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        try:
                            price = float(match.replace(",", ""))
                            if 0.001 <= price <= 100000:  # Reasonable price range
                                prices.append(price)
                        except ValueError:
                            continue
                
                # Also check HTML for structured data
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            if "offers" in data:
                                offers = data["offers"]
                                if isinstance(offers, dict) and "price" in offers:
                                    prices.append(float(offers["price"]))
                                elif isinstance(offers, list):
                                    for offer in offers:
                                        if "price" in offer:
                                            prices.append(float(offer["price"]))
                    except:
                        continue
                
                # Get product name
                title = soup.title.string if soup.title else ""
                h1 = soup.find("h1")
                product_name = h1.get_text(strip=True) if h1 else title
                
                # Get quantity breaks if available
                quantity_prices = self._extract_quantity_breaks(text)
                
                return {
                    "url": url,
                    "distributor": distributor,
                    "product_name": product_name[:200],
                    "prices": list(set(prices))[:10],
                    "min_price": min(prices) if prices else None,
                    "max_price": max(prices) if prices else None,
                    "quantity_breaks": quantity_prices,
                    "currency": "USD",
                    "success": True
                }
                
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    def _extract_quantity_breaks(self, text: str) -> list:
        """Extract quantity-based pricing (e.g., 1+ $5.00, 10+ $4.50)."""
        quantity_breaks = []
        
        patterns = [
            r'(\d+)\+?\s*[:\s]*\$?([\d,]+\.?\d{0,2})',
            r'Qty\s*(\d+)[:\s]*\$?([\d,]+\.?\d{0,2})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for qty, price in matches:
                try:
                    quantity_breaks.append({
                        "quantity": int(qty),
                        "price": float(price.replace(",", ""))
                    })
                except ValueError:
                    continue
        
        # Sort by quantity and remove duplicates
        seen = set()
        unique_breaks = []
        for item in sorted(quantity_breaks, key=lambda x: x["quantity"]):
            key = (item["quantity"], item["price"])
            if key not in seen:
                seen.add(key)
                unique_breaks.append(item)
        
        return unique_breaks[:10]
    
    async def search_and_price(
        self,
        product_name: str,
        distributors: list = None
    ) -> dict:
        """
        Search for a product across distributors and get pricing.
        
        Uses Serper to find product pages, then scrapes each for pricing.
        """
        from src.config import settings
        
        if distributors is None:
            distributors = ["mouser", "digikey", "arrow", "newark"]
        
        results = {
            "product": product_name,
            "pricing_by_distributor": {},
            "lowest_price": None,
            "lowest_price_url": None,
            "all_prices": []
        }
        
        # Search for product pages on each distributor
        if settings.serper_api_key:
            from src.tools.serper_search import SerperSearchTool
            serper = SerperSearchTool()
            
            for distributor in distributors:
                query = f'site:{distributor}.com "{product_name}" price'
                try:
                    search_results = await serper.search(query, num_results=3)
                    
                    for item in search_results.get("organic", []):
                        url = item.get("link", "")
                        if url:
                            pricing = await self.scrape_product_page(url)
                            if pricing.get("success") and pricing.get("prices"):
                                results["pricing_by_distributor"][distributor] = pricing
                                results["all_prices"].extend([
                                    {"price": p, "distributor": distributor, "url": url}
                                    for p in pricing["prices"]
                                ])
                                break  # Got pricing for this distributor
                                
                except Exception as e:
                    print(f"Search failed for {distributor}: {e}")
        
        # Find lowest price
        if results["all_prices"]:
            lowest = min(results["all_prices"], key=lambda x: x["price"])
            results["lowest_price"] = lowest["price"]
            results["lowest_price_url"] = lowest["url"]
        
        return results
    
    async def get_vendor_pricing_report(
        self,
        vendor_name: str,
        sample_products: list = None
    ) -> dict:
        """
        Generate a pricing report for a vendor.
        
        Args:
            vendor_name: Vendor/distributor name
            sample_products: List of products to check prices for
            
        Returns:
            Comprehensive pricing report
        """
        from src.config import settings
        
        report = {
            "vendor": vendor_name,
            "products_checked": [],
            "average_price_competitiveness": None,
            "sample_prices": [],
            "pricing_summary": ""
        }
        
        # If no products specified, search for popular products from this vendor
        if not sample_products:
            if settings.serper_api_key:
                from src.tools.serper_search import SerperSearchTool
                serper = SerperSearchTool()
                
                # Find product pages on this vendor's site
                query = f'site:{vendor_name.lower().replace(" ", "")}.com product price'
                search_results = await serper.search(query, num_results=5)
                
                for item in search_results.get("organic", []):
                    url = item.get("link", "")
                    if url:
                        pricing = await self.scrape_product_page(url)
                        if pricing.get("success"):
                            report["products_checked"].append(pricing)
                            if pricing.get("prices"):
                                report["sample_prices"].extend(pricing["prices"][:3])
        
        # Calculate summary stats
        if report["sample_prices"]:
            avg_price = sum(report["sample_prices"]) / len(report["sample_prices"])
            report["pricing_summary"] = f"Found {len(report['products_checked'])} products with average price ${avg_price:.2f}"
        else:
            report["pricing_summary"] = "No pricing data could be extracted"
        
        return report
    
    async def compare_prices_across_vendors(
        self,
        product_query: str,
        vendors: list = None
    ) -> dict:
        """
        Compare prices for a product across multiple vendors.
        
        Returns a comparison table with prices from each vendor.
        """
        if vendors is None:
            vendors = ["mouser", "digikey", "arrow", "newark", "rs-online"]
        
        from src.config import settings
        
        comparison = {
            "product_query": product_query,
            "vendors_checked": [],
            "prices": [],
            "best_price": None,
            "best_vendor": None,
            "price_comparison_table": []
        }
        
        if not settings.serper_api_key:
            comparison["error"] = "Serper API key not configured"
            return comparison
        
        from src.tools.serper_search import SerperSearchTool
        serper = SerperSearchTool()
        
        for vendor in vendors:
            query = f'site:{vendor}.com "{product_query}" price'
            
            try:
                search_results = await serper.search(query, num_results=2)
                
                for item in search_results.get("organic", []):
                    url = item.get("link", "")
                    if url:
                        pricing = await self.scrape_product_page(url)
                        if pricing.get("success") and pricing.get("min_price"):
                            comparison["vendors_checked"].append(vendor)
                            comparison["prices"].append({
                                "vendor": vendor,
                                "price": pricing["min_price"],
                                "url": url,
                                "product_name": pricing.get("product_name", "")
                            })
                            comparison["price_comparison_table"].append({
                                "vendor": vendor.title(),
                                "price": f"${pricing['min_price']:.2f}",
                                "url": url
                            })
                            break
                            
            except Exception as e:
                print(f"Price comparison failed for {vendor}: {e}")
        
        # Find best price
        if comparison["prices"]:
            best = min(comparison["prices"], key=lambda x: x["price"])
            comparison["best_price"] = best["price"]
            comparison["best_vendor"] = best["vendor"]
        
        return comparison
    
    async def llm_extract_pricing(
        self,
        content: str,
        query_context: str = ""
    ) -> dict:
        """
        Use LLM to intelligently extract pricing from ANY content.
        
        This is the universal extraction method - works for:
        - Product prices
        - Service fees
        - Platform commissions
        - Subscription costs
        - Any pricing structure
        
        Args:
            content: Page content or text to extract from
            query_context: Optional context about what user is looking for
            
        Returns:
            dict with extracted pricing data
        """
        from src.llm.ollama_client import OllamaClient
        import json
        import re
        
        llm = OllamaClient(timeout=120)
        
        prompt = f"""Extract ALL pricing information from this content.

CONTEXT (what user is researching):
{query_context[:500] if query_context else "General pricing information"}

CONTENT TO ANALYZE:
{content[:6000]}

EXTRACT:
1. Any prices mentioned (products, services, fees, subscriptions)
2. Commission rates or percentage fees
3. Pricing tiers or plans
4. Cost comparisons if mentioned
5. Currency and price units

OUTPUT FORMAT (JSON):
{{
    "prices_found": [
        {{
            "item": "What is being priced",
            "price": "Price value (number or percentage)",
            "currency": "USD/PKR/EUR/% etc",
            "type": "product/subscription/commission/fee/other",
            "details": "Any additional context"
        }}
    ],
    "pricing_structure": "Brief description of how pricing works",
    "key_takeaways": ["Important pricing insights"]
}}

Return ONLY valid JSON. Extract ALL prices you can find."""

        try:
            response = await llm.generate(
                prompt,
                system="You are a pricing extraction expert. Extract all pricing information and return only valid JSON.",
                temperature=0.1
            )
            await llm.close()
            
            # Parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                result["extraction_method"] = "llm"
                result["success"] = True
                return result
            
            return {
                "success": False,
                "raw_response": response,
                "extraction_method": "llm"
            }
            
        except Exception as e:
            await llm.close()
            return {
                "success": False,
                "error": str(e),
                "extraction_method": "llm"
            }
    
    async def extract_from_url_with_llm(
        self,
        url: str,
        query_context: str = ""
    ) -> dict:
        """
        Fetch a URL and use LLM to extract pricing.
        Universal method that works on ANY webpage.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "lxml")
                
                # Remove scripts/styles
                for element in soup(["script", "style"]):
                    element.decompose()
                
                text = soup.get_text(separator=" ", strip=True)
                title = soup.title.string if soup.title else ""
                
                result = await self.llm_extract_pricing(text, query_context)
                result["url"] = url
                result["page_title"] = title[:200]
                
                return result
                
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
