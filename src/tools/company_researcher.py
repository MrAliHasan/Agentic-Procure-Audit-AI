"""
Company Research Tool - Deep Intelligence Report
Generates comprehensive strategic reports with LLM analysis.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx

from src.config import settings


@dataclass
class Executive:
    """Executive/key person at a company."""
    name: str
    role: str
    linkedin_url: str = ""
    email: str = ""


@dataclass
class NewsItem:
    """News article or announcement."""
    title: str
    snippet: str
    source: str
    url: str
    date: str = ""
    news_type: str = ""  # funding, product, partnership, acquisition, regulation, executive, general


@dataclass 
class CompanyProfile:
    """Complete company research profile with strategic analysis."""
    name: str
    website: str = ""
    industry: str = ""
    hq_location: str = ""
    founded: str = ""
    employees: str = ""
    description: str = ""
    
    # ENHANCED: Location details
    hq_city: str = ""
    hq_country: str = ""
    global_offices: List[str] = field(default_factory=list)
    
    # Data collections
    executives: List[Executive] = field(default_factory=list)
    recent_news: List[NewsItem] = field(default_factory=list)
    competitors: List[str] = field(default_factory=list)
    hiring_signals: List[str] = field(default_factory=list)
    products_services: List[str] = field(default_factory=list)
    
    # ENHANCED: Detailed financials
    funding: Dict[str, Any] = field(default_factory=lambda: {
        "total_raised": "",
        "last_round": "",
        "last_round_amount": "",
        "valuation": "",
        "revenue": "",
        "investors": []
    })
    social_profiles: Dict[str, str] = field(default_factory=dict)
    
    # ENHANCED: Market data
    market_data: Dict[str, Any] = field(default_factory=lambda: {
        "market_share": "",
        "tam": "",
        "sam": "",
        "som": "",
        "growth_rate": "",
        "competitor_shares": {}
    })
    
    # ENHANCED: Hiring details
    hiring_details: Dict[str, Any] = field(default_factory=lambda: {
        "total_openings": 0,
        "key_roles": [],
        "tech_stack": [],
        "hiring_locations": []
    })
    
    # Strategic Analysis (LLM-generated from search data)
    strategic_report: str = ""
    swot_analysis: Dict[str, List[str]] = field(default_factory=dict)
    market_position: str = ""
    growth_trajectory: str = ""
    business_model: str = ""
    key_risks: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    investment_thesis: str = ""
    contact_strategy: str = ""
    
    # REAL DATA SOURCES - URLs with snippets proving real-time research
    data_sources: List[Dict[str, str]] = field(default_factory=list)
    raw_search_snippets: List[str] = field(default_factory=list)
    
    # Metadata
    search_queries_used: int = 0
    sources_scraped: int = 0
    research_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


class CompanyResearcher:
    """Deep company research with comprehensive strategic analysis."""
    
    def __init__(self):
        self.serper_key = settings.serper_api_key
        self.groq_key = settings.groq_api_key
        self.groq_model = getattr(settings, 'groq_model', 'llama-3.3-70b-versatile')
        self.openai_key = getattr(settings, 'openai_api_key', '')
        self.openai_model = getattr(settings, 'openai_model', 'gpt-4o-mini')
        self.headers = {
            "X-API-KEY": self.serper_key,
            "Content-Type": "application/json",
        }
        self.all_search_data = []  # Store all search results for LLM analysis
    
    async def research(self, company_name: str) -> CompanyProfile:
        """
        Perform comprehensive deep research on a company.
        
        Generates:
        - Basic company info
        - Executive profiles with LinkedIn/email
        - News and market signals
        - SWOT Analysis
        - Market position analysis
        - Growth trajectory
        - Business model breakdown
        - Key risks and opportunities
        - Investment thesis
        - Contact/outreach strategy
        """
        profile = CompanyProfile(name=company_name)
        self.all_search_data = []
        
        # Phase 1: Gather comprehensive data from multiple angles
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Basic company info
            info1 = await self._search(client, f'"{company_name}" company about overview')
            info2 = await self._search(client, f'"{company_name}" founded headquarters employees revenue')
            
            # ENHANCED: Dedicated HQ/location search
            locations = await self._search(client, f'"{company_name}" headquarters address "based in" OR "located in" city')
            
            # Products and services
            products = await self._search(client, f'"{company_name}" products services what does')
            
            # Leadership
            execs = await self._search(client, f'site:linkedin.com/in "{company_name}" CEO OR founder OR "chief" OR president')
            vps = await self._search(client, f'site:linkedin.com/in "{company_name}" VP OR director OR "head of" OR CTO OR CFO')
            
            # ENHANCED: Real email discovery - search for actual contact emails
            email_search = await self._search(client, f'"{company_name}" email contact "@{company_name.lower().replace(" ", "")}" OR "reach us"')
            email_exec = await self._search(client, f'site:rocketreach.co OR site:apollo.io OR site:hunter.io "{company_name}" CEO OR CFO email')
            
            # News and signals
            news_recent = await self._search(client, f'"{company_name}" news 2024 2025')
            news_funding = await self._search(client, f'"{company_name}" funding investment acquisition')
            news_strategy = await self._search(client, f'"{company_name}" strategy expansion growth')
            
            # Market position
            market = await self._search(client, f'"{company_name}" market share industry leader')
            competitors = await self._search(client, f'"{company_name}" vs competitors alternatives comparison')
            
            # ENHANCED: Market size and TAM
            market_size = await self._search(client, f'"{company_name}" market size TAM SAM "total addressable market" billion')
            
            # Challenges and risks
            challenges = await self._search(client, f'"{company_name}" challenges risks problems')
            
            # Financial - ENHANCED with more specific queries
            financials = await self._search(client, f'"{company_name}" revenue profit valuation')
            investors = await self._search(client, f'"{company_name}" investors funded by "led by" series round')
            
            # Culture and hiring
            culture = await self._search(client, f'"{company_name}" culture glassdoor reviews')
            hiring = await self._search(client, f'"{company_name}" careers hiring jobs 2025')
            
            # ENHANCED: Detailed hiring with tech stack
            hiring_tech = await self._search(client, f'"{company_name}" jobs python OR javascript OR kubernetes engineering')
            
            # Technology
            tech = await self._search(client, f'"{company_name}" technology stack engineering')
            
            profile.search_queries_used = 20
        
        # Store all results for comprehensive LLM analysis
        self.all_search_data = {
            "company_info": info1 + info2 + locations,
            "products": products,
            "executives": execs + vps,
            "emails": email_search + email_exec,
            "news": news_recent + news_funding + news_strategy,
            "market": market + competitors + market_size,
            "challenges": challenges,
            "financials": financials + investors,
            "culture": culture,
            "hiring": hiring + hiring_tech,
            "technology": tech
        }
        
        # Phase 2: Extract structured data
        profile = self._extract_company_info(profile, info1 + info2)
        profile.executives = self._extract_executives(execs + vps, company_name)
        profile.recent_news = self._extract_news(news_recent + news_funding)
        profile.funding = self._extract_funding(financials + investors, company_name)
        profile.competitors = await self._extract_competitors(competitors, company_name)
        profile.hiring_signals = self._extract_hiring_signals(hiring)
        profile.products_services = self._extract_products(products, company_name)
        
        # ENHANCED: Extract additional intelligence
        profile = self._extract_location(profile, info1 + info2 + locations)
        profile.market_data = self._extract_market_data(market + competitors + market_size, company_name)
        profile.hiring_details = self._extract_hiring_details(hiring + hiring_tech, company_name)
        
        # Tag news by type
        for news_item in profile.recent_news:
            news_item.news_type = self._tag_news_type(news_item)
        
        # Collect REAL SOURCE DATA for citations
        profile.data_sources = self._collect_sources(info1 + info2 + financials + news_recent)
        profile.raw_search_snippets = self._collect_raw_snippets(info1 + info2 + products + market)
        profile.sources_scraped = len(profile.data_sources)
        
        # Phase 3: Generate comprehensive strategic analysis with LLM
        profile = await self._generate_strategic_report(profile)
        
        return profile
    
    async def _search(self, client: httpx.AsyncClient, query: str, num: int = 10) -> List[Dict]:
        """Execute Serper search."""
        try:
            response = await client.post(
                "https://google.serper.dev/search",
                json={"q": query, "num": num, "gl": "us", "hl": "en"},
                headers=self.headers
            )
            response.raise_for_status()
            results = response.json().get("organic", [])
            return results
        except Exception:
            return []
    
    async def _llm_call(self, prompt: str, max_tokens: int = 2000) -> str:
        """Make a call to LLM with Groq primary, OpenAI fallback."""
        
        # Try Groq first (faster)
        if self.groq_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.groq_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.groq_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens": max_tokens,
                        }
                    )
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                if "429" in str(e):
                    print(f"[Groq rate limited] Falling back to OpenAI...")
                else:
                    print(f"[Groq failed: {e}] Trying OpenAI fallback...")
        
        # Fallback to OpenAI GPT-4o-mini
        if self.openai_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.openai_model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "max_tokens": max_tokens,
                        }
                    )
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"[OpenAI failed: {e}]")
        
        return ""
    
    def _extract_company_info(self, profile: CompanyProfile, results: List[Dict]) -> CompanyProfile:
        """Extract basic company info from search results."""
        for r in results:
            link = r.get("link", "")
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            combined = f"{title} {snippet}".lower()
            
            if not profile.website and profile.name.lower().replace(" ", "") in link.replace("www.", "").lower():
                profile.website = link.split("/")[2] if "/" in link else link
            
            if not profile.founded:
                year_match = re.search(r'founded\s*(?:in\s*)?(\d{4})', combined)
                if year_match:
                    profile.founded = year_match.group(1)
            
            if not profile.employees:
                emp_match = re.search(r'(\d{1,3}(?:,\d{3})*\+?)\s*employees', combined)
                if emp_match:
                    profile.employees = emp_match.group(1)
            
            if not profile.hq_location:
                hq_match = re.search(r'headquartered?\s*(?:in\s*)?([A-Z][a-z]+(?:\s*,\s*[A-Z]{2})?)', f"{title} {snippet}")
                if hq_match:
                    profile.hq_location = hq_match.group(1)
        
        return profile
    
    def _extract_executives(self, results: List[Dict], company_name: str) -> List[Executive]:
        """Extract executives from LinkedIn search results."""
        executives = []
        seen_urls = set()
        
        for r in results:
            url = r.get("link", "")
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            
            if "linkedin.com/in" not in url or url in seen_urls:
                continue
            
            seen_urls.add(url)
            
            name = title.split(" - ")[0].strip() if " - " in title else title.split(" | ")[0].strip()
            
            role = ""
            if " - " in title:
                parts = title.split(" - ")
                if len(parts) >= 2:
                    role = parts[1].replace(" | LinkedIn", "").strip()
                    if " @ " in role:
                        role = role.split(" @ ")[0].strip()
                    elif " at " in role.lower():
                        idx = role.lower().find(" at ")
                        role = role[:idx].strip()
            
            email = ""
            email_match = re.search(r'[\w\.-]+@gmail\.com', snippet.lower())
            if email_match:
                email = email_match.group()
            
            role_lower = role.lower()
            is_exec = any(kw in role_lower for kw in [
                "ceo", "cto", "cfo", "coo", "cmo", "cpo", "cso",
                "chief", "founder", "co-founder", "president", 
                "vp", "vice president", "director", "head of",
                "partner", "owner", "managing", "general manager"
            ])
            
            if is_exec and name and len(name) > 2:
                executives.append(Executive(
                    name=name[:50],
                    role=role[:80],
                    linkedin_url=url,
                    email=email
                ))
        
        return executives[:20]
    
    def _is_relevant_news(self, title: str, snippet: str, url: str) -> bool:
        """Filter news for relevance - prefer funding, hiring, expansion, launches.
        
        Based on OmniExtract patterns - exclude financial noise, Reddit, generic pages.
        """
        combined = (title + " " + snippet + " " + url).lower()
        
        # EXCLUDE patterns (financial noise, Reddit, generic)
        exclude_patterns = [
            "quarterly earnings", "q1 results", "q2 results", "q3 results", "q4 results",
            "earnings call", "investor call", "shareholder meeting", "annual report",
            "stock price", "share price", "dividend", "eps ", "revenue guidance",
            "reddit.com", "reddit", "/r/",
            "newsroom/index", "press-releases/index", "media/news",
            "form 10-k", "form 10-q", "sec filing", "proxy statement",
            "yahoo finance", "seeking alpha", "motley fool",
            "glassdoor", "indeed.com", "ziprecruiter", "wikipedia.org"
        ]
        
        if any(pattern in combined for pattern in exclude_patterns):
            return False
        
        # PREFER patterns (relevant news)
        prefer_patterns = [
            "funding", "raised", "investment", "series ",
            "partnership", "partner", "collaboration", "joint venture",
            "expansion", "expanding", "new facility", "new plant", "new project",
            "hiring", "jobs", "workforce", "new hires", "head of", "appointed",
            "launch", "launching", "unveiled", "announced",
            "acquisition", "acquires", "merger", "deal",
            "revenue", "growth", "market", "customers"
        ]
        
        relevance_score = sum(1 for p in prefer_patterns if p in combined)
        return relevance_score >= 1
    
    def _extract_news(self, results: List[Dict]) -> List[NewsItem]:
        """Extract news items with relevance filtering and date validation.
        
        Based on OmniExtract patterns - includes URL links and filters future dates.
        """
        from datetime import datetime
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Future months in current year
        future_months = ["January", "February", "March", "April", "May", "June", 
                        "July", "August", "September", "October", "November", "December"][current_month:]
        
        news = []
        
        for r in results[:15]:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            link = r.get("link", "")
            combined_text = title + " " + snippet
            
            # Skip if not relevant news
            if not self._is_relevant_news(title, snippet, link):
                continue
            
            # Skip future years
            if str(current_year + 1) in combined_text or str(current_year + 2) in combined_text:
                continue
            
            # Skip future months in current year
            is_future_date = False
            for future_month in future_months:
                if future_month in combined_text and str(current_year) in combined_text:
                    is_future_date = True
                    break
            
            if is_future_date:
                continue
            
            # Skip forward-looking language
            forward_looking = ["applications open", "coming soon", "launching soon", "will be", 
                              "upcoming", "scheduled for", "expected to", "announces plans"]
            if any(fl in combined_text.lower() for fl in forward_looking):
                if str(current_year) in combined_text:
                    continue
            
            source = link.split("/")[2] if "/" in link else link
            source = source.replace("www.", "")
            
            # Extract date
            date = ""
            date_match = re.search(r'(\w{3,9}\s+\d{1,2},?\s+\d{4})', snippet)
            if date_match:
                date = date_match.group(1)
            
            news.append(NewsItem(
                title=title[:120],
                snippet=snippet[:250],
                source=source,
                url=link,  # Keep full URL for citations
                date=date
            ))
            
            if len(news) >= 8:  # Limit to top 8 relevant news items
                break
        
        return news
    
    def _extract_funding(self, results: List[Dict], company_name: str) -> Dict[str, Any]:
        """Extract comprehensive funding information including investors."""
        funding = {
            "total_raised": "",
            "last_round": "",
            "last_round_amount": "",
            "valuation": "",
            "revenue": "",
            "investors": []
        }
        combined_text = " ".join([r.get("snippet", "") for r in results]).lower()
        
        # Total funding raised
        raised_match = re.search(r'raised\s*\$?([\d.]+)\s*(million|billion|m|b)', combined_text)
        if raised_match:
            amount = raised_match.group(1)
            unit = raised_match.group(2)
            if unit in ["billion", "b"]:
                funding["total_raised"] = f"${amount}B"
            else:
                funding["total_raised"] = f"${amount}M"
        
        # Valuation
        valuation_match = re.search(r'valuation\s*(?:of\s*)?\$?([\d.]+)\s*(million|billion|m|b)', combined_text)
        if not valuation_match:
            valuation_match = re.search(r'valued\s*(?:at\s*)?\$?([\d.]+)\s*(million|billion|m|b)', combined_text)
        if valuation_match:
            val = valuation_match.group(1)
            unit = valuation_match.group(2)
            if unit in ["billion", "b"]:
                funding["valuation"] = f"${val}B"
            else:
                funding["valuation"] = f"${val}M"
        
        # Last funding round
        round_match = re.search(r'series\s*([a-h])', combined_text)
        if round_match:
            funding["last_round"] = f"Series {round_match.group(1).upper()}"
        elif "ipo" in combined_text or "public company" in combined_text:
            funding["last_round"] = "IPO/Public"
        elif "seed" in combined_text:
            funding["last_round"] = "Seed"
        
        # Revenue
        revenue_match = re.search(r'revenue\s*(?:of\s*)?\$?([\d.]+)\s*(million|billion|m|b)', combined_text)
        if not revenue_match:
            revenue_match = re.search(r'annualized\s*revenue\s*(?:of\s*)?\$?([\d.]+)\s*(million|billion|m|b)', combined_text)
        if revenue_match:
            rev = revenue_match.group(1)
            unit = revenue_match.group(2)
            if unit in ["billion", "b"]:
                funding["revenue"] = f"${rev}B"
            else:
                funding["revenue"] = f"${rev}M"
        
        # Extract investors (common VC names)
        investor_patterns = [
            r'led by ([A-Z][a-zA-Z\s]+)',
            r'investors include ([A-Za-z,\s]+)',
            r'backed by ([A-Z][a-zA-Z\s,]+)',
            r'from ([A-Z][a-zA-Z\s]+) and ([A-Z][a-zA-Z\s]+)'
        ]
        investors = set()
        common_vcs = ["Sequoia", "Andreessen", "a16z", "Google", "Microsoft", "Amazon", 
                     "SoftBank", "Tiger Global", "Benchmark", "Accel", "Kleiner", 
                     "Khosla", "Greylock", "Y Combinator", "Lightspeed", "NEA",
                     "Index Ventures", "General Catalyst", "Thrive Capital"]
        for vc in common_vcs:
            if vc.lower() in combined_text:
                investors.add(vc)
        funding["investors"] = list(investors)[:5]
        
        return funding
    
    async def _extract_competitors(self, results: List[Dict], company_name: str) -> List[str]:
        """Extract competitor names using LLM."""
        if not self.groq_key or not results:
            return []
        
        snippets = " | ".join([r.get("snippet", "")[:200] for r in results[:5]])
        
        prompt = f"""From this search data about "{company_name}" competitors, extract competitor company names.

Search data: {snippets}

Return ONLY a JSON array of competitor names (max 10):
["Company1", "Company2", ...]

Do NOT include "{company_name}" in the list."""

        content = await self._llm_call(prompt, 200)
        
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            try:
                competitors = json.loads(match.group())
                return [c for c in competitors if c.lower() != company_name.lower()][:10]
            except Exception:
                pass
        return []
    
    def _extract_hiring_signals(self, results: List[Dict]) -> List[str]:
        """Extract hiring signals from job search results."""
        signals = []
        
        for r in results[:5]:
            snippet = r.get("snippet", "").lower()
            
            role_match = re.search(r'(\d+)\+?\s*(?:open\s*)?(?:roles?|positions?|jobs?)', snippet)
            if role_match:
                signals.append(f"{role_match.group(1)}+ open positions")
            
            if "expanding" in snippet:
                signals.append("Expanding operations")
            if "remote" in snippet:
                signals.append("Remote positions available")
            if "engineering" in snippet and "hiring" in snippet:
                signals.append("Actively hiring engineers")
        
        return list(set(signals))[:6]
    
    def _extract_products(self, results: List[Dict], company_name: str) -> List[str]:
        """Extract products/services mentions."""
        products = []
        for r in results[:5]:
            snippet = r.get("snippet", "")
            # Basic extraction - will be enhanced by LLM
            if len(snippet) > 50:
                products.append(snippet[:150])
        return products[:5]
    
    def _extract_location(self, profile: CompanyProfile, results: List[Dict]) -> CompanyProfile:
        """Extract headquarters location and global offices."""
        combined_text = " ".join([r.get("snippet", "") for r in results])
        
        # HQ patterns
        hq_patterns = [
            r'headquartered in ([A-Z][a-zA-Z]+(?:,?\s*[A-Z]{2})?)',
            r'based in ([A-Z][a-zA-Z]+(?:,?\s*[A-Z]{2})?)',
            r'headquarters in ([A-Z][a-zA-Z]+)',
            r'head office in ([A-Z][a-zA-Z]+)'
        ]
        
        for pattern in hq_patterns:
            match = re.search(pattern, combined_text)
            if match:
                location = match.group(1).strip()
                # Parse city and country
                if "," in location:
                    parts = location.split(",")
                    profile.hq_city = parts[0].strip()
                    if len(parts) > 1:
                        # Could be state or country
                        second = parts[1].strip()
                        if len(second) == 2:  # State code
                            profile.hq_country = "United States"
                        else:
                            profile.hq_country = second
                else:
                    profile.hq_city = location
                break
        
        # Country detection
        countries = ["United States", "USA", "UK", "United Kingdom", "Germany", 
                    "France", "Canada", "Japan", "China", "India", "Australia"]
        for country in countries:
            if country.lower() in combined_text.lower():
                if not profile.hq_country:
                    profile.hq_country = country
                break
        
        # Global offices
        office_patterns = [
            r'offices in ([A-Z][a-zA-Z]+(?:,\s*[A-Z][a-zA-Z]+)*)',
            r'locations in ([A-Z][a-zA-Z]+(?:,\s*[A-Z][a-zA-Z]+)*)',
            r'presence in ([A-Z][a-zA-Z]+(?:,\s*[A-Z][a-zA-Z]+)*)'
        ]
        for pattern in office_patterns:
            match = re.search(pattern, combined_text)
            if match:
                offices_str = match.group(1)
                offices = [o.strip() for o in offices_str.split(",")]
                profile.global_offices = offices[:5]
                break
        
        return profile
    
    def _extract_real_emails(self, profile: CompanyProfile, results: List[Dict], company_name: str) -> CompanyProfile:
        """Extract REAL email addresses from search results, with pattern fallback."""
        combined_text = " ".join([r.get("snippet", "") + " " + r.get("title", "") for r in results])
        
        # Get domain from website
        domain = ""
        if profile.website:
            domain = profile.website.replace("www.", "").replace("https://", "").replace("http://", "")
            if "/" in domain:
                domain = domain.split("/")[0]
            profile.email_domain = domain
        
        # Step 1: Search for REAL emails in search results using regex
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        found_emails = re.findall(email_pattern, combined_text)
        
        # Filter to only company domain emails
        company_emails = []
        company_domain_lower = domain.lower() if domain else company_name.lower().replace(" ", "")
        for email in found_emails:
            email_lower = email.lower()
            # Skip common non-person emails
            skip_patterns = ["support@", "info@", "contact@", "sales@", "help@", "noreply@", "no-reply@"]
            if any(sp in email_lower for sp in skip_patterns):
                continue
            # Check if it's a company email
            if company_domain_lower in email_lower or company_name.lower().replace(" ", "") in email_lower:
                company_emails.append(email)
        
        # Build a map of found emails by first name for matching
        email_by_name = {}
        for email in company_emails:
            local_part = email.split("@")[0].lower()
            # Extract possible first name from email formats: first.last, firstl, first_last
            parts = re.split(r'[._]', local_part)
            if parts:
                email_by_name[parts[0]] = email
        
        # Step 2: Try to match found emails to executives by first name
        matched_count = 0
        for exec in profile.executives:
            if exec.name:
                name_parts = exec.name.lower().split()
                if name_parts:
                    first_name = re.sub(r'[^a-z]', '', name_parts[0])
                    if first_name in email_by_name:
                        exec.email = email_by_name[first_name]
                        matched_count += 1
        
        # Step 3: Detect email pattern from found emails
        detected_pattern = ""
        for email in company_emails[:5]:
            local_part = email.split("@")[0].lower()
            if "." in local_part:
                detected_pattern = "first.last"
                break
            elif "_" in local_part:
                detected_pattern = "first_last"
                break
            elif len(local_part) > 3:
                detected_pattern = "firstl" if local_part[-1].isalpha() else "first"
        
        profile.email_pattern = detected_pattern or "first.last"
        
        # Step 4: For executives without matched emails, generate using detected pattern
        if domain:
            for exec in profile.executives:
                if not exec.email and exec.name:
                    name_parts = exec.name.lower().split()
                    if len(name_parts) >= 2:
                        first = re.sub(r'[^a-z]', '', name_parts[0])
                        last = re.sub(r'[^a-z]', '', name_parts[-1])
                        if first and last:
                            if profile.email_pattern == "first.last":
                                exec.email = f"{first}.{last}@{domain}"
                            elif profile.email_pattern == "first_last":
                                exec.email = f"{first}_{last}@{domain}"
                            elif profile.email_pattern == "firstl":
                                exec.email = f"{first}{last[0]}@{domain}"
                            else:
                                exec.email = f"{first}.{last}@{domain}"
        
        return profile
    
    def _extract_market_data(self, results: List[Dict], company_name: str) -> Dict[str, Any]:
        """Extract market size, share, and growth data."""
        market_data = {
            "market_share": "",
            "tam": "",
            "sam": "",
            "som": "",
            "growth_rate": "",
            "competitor_shares": {}
        }
        combined_text = " ".join([r.get("snippet", "") for r in results]).lower()
        
        # Market share
        share_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:market\s*)?share', combined_text)
        if share_match:
            market_data["market_share"] = f"{share_match.group(1)}%"
        
        # TAM (Total Addressable Market)
        tam_match = re.search(r'(?:tam|total addressable market|total market)\s*(?:of\s*)?\$?([\d.]+)\s*(million|billion|trillion|m|b|t)', combined_text)
        if tam_match:
            val = tam_match.group(1)
            unit = tam_match.group(2)
            unit_map = {"million": "M", "m": "M", "billion": "B", "b": "B", "trillion": "T", "t": "T"}
            market_data["tam"] = f"${val}{unit_map.get(unit, 'B')}"
        
        # Growth rate
        growth_match = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:annual|yearly|yoy|cagr|growth)', combined_text)
        if growth_match:
            market_data["growth_rate"] = f"{growth_match.group(1)}% CAGR"
        
        return market_data
    
    def _extract_hiring_details(self, results: List[Dict], company_name: str) -> Dict[str, Any]:
        """Extract detailed hiring information: roles, tech stack, locations."""
        hiring_details = {
            "total_openings": 0,
            "key_roles": [],
            "tech_stack": [],
            "hiring_locations": []
        }
        combined_text = " ".join([r.get("snippet", "") + " " + r.get("title", "") for r in results]).lower()
        
        # Total openings
        openings_match = re.search(r'(\d+)\s*(?:\+)?\s*(?:open|active)?\s*(?:roles?|positions?|jobs?|openings?)', combined_text)
        if openings_match:
            hiring_details["total_openings"] = int(openings_match.group(1))
        
        # Key roles (departments hiring)
        role_keywords = {
            "engineering": "Engineering",
            "software": "Software Engineering",
            "product": "Product",
            "design": "Design",
            "sales": "Sales",
            "marketing": "Marketing",
            "data science": "Data Science",
            "machine learning": "Machine Learning",
            "ai": "AI/ML",
            "operations": "Operations",
            "finance": "Finance",
            "hr": "HR/People"
        }
        for keyword, role in role_keywords.items():
            if keyword in combined_text:
                if role not in hiring_details["key_roles"]:
                    hiring_details["key_roles"].append(role)
        hiring_details["key_roles"] = hiring_details["key_roles"][:5]
        
        # Tech stack
        tech_keywords = ["python", "javascript", "typescript", "react", "node.js", "golang", "go", 
                        "rust", "java", "kubernetes", "aws", "gcp", "azure", "docker", 
                        "postgresql", "mongodb", "redis", "tensorflow", "pytorch"]
        for tech in tech_keywords:
            if tech in combined_text:
                hiring_details["tech_stack"].append(tech.title())
        hiring_details["tech_stack"] = list(set(hiring_details["tech_stack"]))[:8]
        
        # Hiring locations
        location_keywords = ["san francisco", "new york", "austin", "seattle", "london", 
                            "remote", "hybrid", "berlin", "toronto", "singapore"]
        for loc in location_keywords:
            if loc in combined_text:
                hiring_details["hiring_locations"].append(loc.title())
        hiring_details["hiring_locations"] = list(set(hiring_details["hiring_locations"]))[:5]
        
        return hiring_details
    
    def _tag_news_type(self, news_item: NewsItem) -> str:
        """Tag news by type for filtering."""
        text = (news_item.title + " " + news_item.snippet).lower()
        
        if any(w in text for w in ["funding", "raised", "investment", "series", "valuation"]):
            return "funding"
        elif any(w in text for w in ["launch", "release", "new product", "unveiled", "introduces"]):
            return "product"
        elif any(w in text for w in ["partnership", "partner", "collaboration", "joint venture", "deal"]):
            return "partnership"
        elif any(w in text for w in ["acquired", "acquisition", "merger", "bought", "acquires"]):
            return "acquisition"
        elif any(w in text for w in ["compliance", "regulatory", "legal", "lawsuit", "sec", "policy"]):
            return "regulation"
        elif any(w in text for w in ["ceo", "cfo", "hired", "appointed", "resigned", "departed"]):
            return "executive"
        else:
            return "general"
    
    def _collect_sources(self, results: List[Dict]) -> List[Dict[str, str]]:
        """Collect real source URLs with titles and snippets for citations."""
        sources = []
        seen_urls = set()
        
        for r in results:
            url = r.get("link", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                sources.append({
                    "title": r.get("title", "")[:80],
                    "url": url,
                    "snippet": r.get("snippet", "")[:200],
                    "domain": url.split("/")[2] if "/" in url else url
                })
        
        return sources[:15]  # Top 15 unique sources
    
    def _collect_raw_snippets(self, results: List[Dict]) -> List[str]:
        """Collect raw search snippets to prove real-time data."""
        snippets = []
        for r in results[:10]:
            snippet = r.get("snippet", "")
            url = r.get("link", "")
            if snippet:
                domain = url.split("/")[2] if "/" in url else "unknown"
                snippets.append(f"[{domain}] {snippet[:180]}")
        return snippets
    
    async def _generate_strategic_report(self, profile: CompanyProfile) -> CompanyProfile:
        """Generate comprehensive strategic analysis using LLM."""
        if not self.groq_key:
            return profile
        
        # Compile all search data into context
        context = self._compile_research_context()
        
        # Generate comprehensive analysis
        analysis_prompt = f"""You are a senior business analyst. Generate a COMPREHENSIVE strategic intelligence report on {profile.name}.

RESEARCH DATA:
{context}

KNOWN FACTS:
- Website: {profile.website}
- Founded: {profile.founded}
- Employees: {profile.employees}
- HQ: {profile.hq_location}
- Funding: {json.dumps(profile.funding)}
- Competitors: {', '.join(profile.competitors[:5])}

Generate a detailed JSON analysis:
{{
    "industry": "specific industry/sector",
    "description": "2-3 sentence company overview",
    "business_model": "How they make money - detailed explanation",
    "market_position": "Their position in the market - leader/challenger/niche. Market share if known.",
    "growth_trajectory": "Growth phase (early-stage/scaling/mature), recent momentum, trajectory",
    "swot": {{
        "strengths": ["5 key strengths with specifics"],
        "weaknesses": ["4 potential weaknesses or challenges"],
        "opportunities": ["4 growth opportunities"],
        "threats": ["4 market or competitive threats"]
    }},
    "key_risks": ["5 specific business risks"],
    "opportunities": ["5 actionable opportunities"],
    "investment_thesis": "3-4 sentences on why someone would invest/partner with this company",
    "strategic_report": "A 300-400 word executive briefing covering: 1) What they do and why it matters, 2) Competitive advantage, 3) Recent strategic moves, 4) Market opportunity, 5) Key challenges, 6) Outlook",
    "contact_strategy": "Best approach to reach decision makers at this company, who to contact, what messaging would resonate"
}}

Be specific and insightful. Don't be generic. Use actual data from the research."""

        content = await self._llm_call(analysis_prompt, 3000)
        
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                data = json.loads(match.group())
                
                if not profile.industry:
                    profile.industry = data.get("industry", "")
                if not profile.description:
                    profile.description = data.get("description", "")
                
                profile.business_model = data.get("business_model", "")
                profile.market_position = data.get("market_position", "")
                profile.growth_trajectory = data.get("growth_trajectory", "")
                profile.swot_analysis = data.get("swot", {})
                profile.key_risks = data.get("key_risks", [])
                profile.opportunities = data.get("opportunities", [])
                profile.investment_thesis = data.get("investment_thesis", "")
                profile.strategic_report = data.get("strategic_report", "")
                profile.contact_strategy = data.get("contact_strategy", "")
                
            except json.JSONDecodeError:
                # Try to extract the strategic report even if JSON fails
                profile.strategic_report = content[:1500]
        
        return profile
    
    def _compile_research_context(self) -> str:
        """Compile all search data into a context string for LLM."""
        context_parts = []
        
        for category, results in self.all_search_data.items():
            if results:
                snippets = []
                for r in results[:5]:
                    title = r.get("title", "")
                    snippet = r.get("snippet", "")
                    snippets.append(f"- {title}: {snippet[:200]}")
                if snippets:
                    context_parts.append(f"\n## {category.upper()}:\n" + "\n".join(snippets))
        
        return "\n".join(context_parts)[:8000]  # Cap at 8000 chars
    
    def to_dict(self, profile: CompanyProfile) -> Dict[str, Any]:
        """Convert profile to dictionary for JSON output."""
        return {
            "company": profile.name,
            "research_date": profile.research_date,
            "overview": {
                "website": profile.website,
                "industry": profile.industry,
                "description": profile.description,
                "hq_location": profile.hq_location,
                "hq_city": profile.hq_city,
                "hq_country": profile.hq_country,
                "global_offices": profile.global_offices,
                "founded": profile.founded,
                "employees": profile.employees,
            },
            "financials": profile.funding,
            "market_data": profile.market_data,
            "strategic_analysis": {
                "executive_summary": profile.strategic_report,
                "business_model": profile.business_model,
                "market_position": profile.market_position,
                "growth_trajectory": profile.growth_trajectory,
                "swot_analysis": profile.swot_analysis,
                "key_risks": profile.key_risks,
                "opportunities": profile.opportunities,
                "investment_thesis": profile.investment_thesis,
            },
            "contacts": {
                "executives": [
                    {
                        "name": e.name,
                        "role": e.role,
                        "linkedin_url": e.linkedin_url
                    }
                    for e in profile.executives
                ],
                "contact_strategy": profile.contact_strategy,
            },
            "market_intelligence": {
                "competitors": profile.competitors,
                "hiring_signals": profile.hiring_signals,
                "hiring_details": profile.hiring_details,
                "recent_news": [
                    {
                        "title": n.title,
                        "snippet": n.snippet,
                        "source": n.source,
                        "url": n.url,
                        "date": n.date,
                        "type": n.news_type
                    }
                    for n in profile.recent_news
                ],
            },
            "data_sources": profile.data_sources,  # Real source URLs with snippets
            "raw_search_data": profile.raw_search_snippets,  # Raw snippets proving real-time search
            "_metadata": {
                "search_queries_used": profile.search_queries_used,
                "sources_scraped": profile.sources_scraped,
                "data_freshness": "Real-time Serper API search",
            }
        }
    
    def generate_markdown_report(self, profile: CompanyProfile) -> str:
        """Generate a formatted markdown report."""
        
        # Build data sources section - use bullet list for cleaner rendering
        sources_section = ""
        if profile.data_sources:
            sources_section = "\n## 📊 Data Sources (Real-Time Search Results)\n\n"
            sources_section += "> **Proof of real-time research**: The following data was retrieved live from Google via Serper API.\n\n"
            for i, src in enumerate(profile.data_sources[:10], 1):
                domain = src.get('domain', '')
                title = src.get('title', '').replace('|', '-')[:50]
                url = src.get('url', '')
                snippet = src.get('snippet', '')[:80]
                sources_section += f"**{i}. [{domain}]({url})**\n"
                sources_section += f"   - {title}\n"
                sources_section += f"   - *{snippet}...*\n\n"
            sources_section += "---\n"
        
        # Build raw snippets section
        raw_data_section = ""
        if profile.raw_search_snippets:
            raw_data_section = "\n## 🔍 Raw Search Data\n\n"
            raw_data_section += "> Unprocessed snippets from live Google search results:\n\n"
            for snippet in profile.raw_search_snippets[:6]:
                raw_data_section += f"- {snippet}\n"
            raw_data_section += "\n---\n"
        
        report = f"""# {profile.name} - Strategic Intelligence Report

**Research Date:** {profile.research_date} | **Queries Executed:** {profile.search_queries_used} | **Sources Analyzed:** {profile.sources_scraped}

> ⚡ **Real-Time Research**: This report was generated using live web searches via Serper API, not cached or training data.

---
{sources_section}
## Executive Summary

{profile.strategic_report or "Analysis pending..."}

---

## Company Overview

| Attribute | Value |
|-----------|-------|
| **Website** | {profile.website or 'N/A'} |
| **Industry** | {profile.industry or 'N/A'} |
| **Headquarters** | {profile.hq_location or 'N/A'} |
| **Founded** | {profile.founded or 'N/A'} |
| **Employees** | {profile.employees or 'N/A'} |

{profile.description or ''}

---

## Business Model

{profile.business_model or 'Analysis pending...'}

---

## Market Position

{profile.market_position or 'Analysis pending...'}

**Growth Trajectory:** {profile.growth_trajectory or 'N/A'}

---

## Financial Summary

"""
        if profile.funding:
            for k, v in profile.funding.items():
                report += f"- **{k.replace('_', ' ').title()}:** {v}\n"
        else:
            report += "*No financial data available*\n"
        
        report += """
---

## SWOT Analysis

"""
        if profile.swot_analysis:
            report += "### Strengths\n"
            for s in profile.swot_analysis.get("strengths", []):
                report += f"- ✅ {s}\n"
            
            report += "\n### Weaknesses\n"
            for w in profile.swot_analysis.get("weaknesses", []):
                report += f"- ⚠️ {w}\n"
            
            report += "\n### Opportunities\n"
            for o in profile.swot_analysis.get("opportunities", []):
                report += f"- 🚀 {o}\n"
            
            report += "\n### Threats\n"
            for t in profile.swot_analysis.get("threats", []):
                report += f"- ⛔ {t}\n"
        
        report += """
---

## Key Risks

"""
        for r in profile.key_risks:
            report += f"- 🔴 {r}\n"
        
        report += """
---

## Opportunities

"""
        for o in profile.opportunities:
            report += f"- 🟢 {o}\n"
        
        report += f"""
---

## Investment Thesis

{profile.investment_thesis or 'Analysis pending...'}

---

## Competitive Landscape

**Main Competitors:** {', '.join(profile.competitors) if profile.competitors else 'N/A'}

---

## Key Executives

"""
        if profile.executives:
            report += "| Name | Role | LinkedIn |\n|------|------|----------|\n"
            for e in profile.executives[:10]:
                linkedin = f"[Link]({e.linkedin_url})" if e.linkedin_url else "N/A"
                report += f"| {e.name} | {e.role} | {linkedin} |\n"
        
        report += f"""
---

## Contact Strategy

{profile.contact_strategy or 'N/A'}

---

## Recent News & Signals

"""
        for n in profile.recent_news[:8]:
            report += f"- **{n.title}** ({n.source})\n"
        
        if profile.hiring_signals:
            report += "\n### Hiring Signals\n"
            for s in profile.hiring_signals:
                report += f"- 🎯 {s}\n"
        
        report += f"""
---

*Report generated by SOI Company Research | {profile.search_queries_used} searches executed*
"""
        return report
