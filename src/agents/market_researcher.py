"""
Market Researcher Agent - Specialized for market intelligence
"""
import json
from src.llm.json_utils import loads_llm_json
from typing import Optional

from src.agents.base import BaseAgent
from src.llm.prompts import MARKET_RESEARCHER_PROMPT
from src.tools.tavily_search import TavilySearchTool


class MarketResearcherAgent(BaseAgent):
    """
    Agent specialized in market research and analysis.
    
    Capabilities:
    - Market trend analysis
    - Competitor research
    - Pricing intelligence
    - Industry outlook
    """
    
    def __init__(self):
        """Initialize the Market Researcher."""
        super().__init__(
            name="Market Researcher",
            system_prompt=MARKET_RESEARCHER_PROMPT,
            temperature=0.3
        )
        self._search_tool: Optional[TavilySearchTool] = None
    
    def _get_search_tool(self) -> TavilySearchTool:
        """Get or create search tool."""
        if self._search_tool is None:
            self._search_tool = TavilySearchTool()
        return self._search_tool
    
    async def run(self, input_data: dict) -> dict:
        """
        Execute market research.
        
        Args:
            input_data: {
                "task": "trends" | "competitors" | "pricing" | "outlook",
                "category": str,
                ...
            }
            
        Returns:
            Research results
        """
        task = input_data.get("task", "trends")
        category = input_data.get("category", "")
        
        if task == "trends":
            return await self.analyze_trends(category)
        elif task == "competitors":
            return await self.research_competitors(
                category,
                input_data.get("known_vendors", [])
            )
        elif task == "pricing":
            return await self.analyze_pricing(
                category,
                input_data.get("product", "")
            )
        elif task == "outlook":
            return await self.industry_outlook(category)
        else:
            raise ValueError(f"Unknown task: {task}")
    
    async def analyze_trends(self, category: str) -> dict:
        """
        Analyze market trends for a category.
        
        Args:
            category: Product/service category
            
        Returns:
            Trend analysis
        """
        search_tool = self._get_search_tool()
        
        # Search for trends
        trends_data = await search_tool.search_market_trends(category)
        
        # Analyze with LLM
        prompt = f"""
        Analyze market trends for: {category}
        
        Research data:
        {json.dumps(trends_data, indent=2, default=str)}
        
        Provide:
        1. Current market trends
        2. Emerging trends
        3. Declining trends
        4. Key drivers
        5. Future predictions
        
        Return as JSON: {{
            "current_trends": [...],
            "emerging_trends": [...],
            "declining_trends": [...],
            "key_drivers": [...],
            "predictions": [...]
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                analysis = loads_llm_json(response)
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        await self.close()
        
        return {
            "category": category,
            "analysis": analysis,
            "sources_used": trends_data.get("total_sources", 0)
        }
    
    async def research_competitors(
        self,
        category: str,
        known_vendors: list[str] = None
    ) -> dict:
        """
        Research competitors in a market.
        
        Args:
            category: Market category
            known_vendors: Already known vendors
            
        Returns:
            Competitor analysis
        """
        known_vendors = known_vendors or []
        search_tool = self._get_search_tool()
        
        # Search for competitors
        query = f"top {category} companies vendors market leaders"
        results = await search_tool.search(
            query,
            max_results=10,
            search_depth="advanced"
        )
        
        # Analyze
        prompt = f"""
        Identify competitors in: {category}
        
        Known players: {known_vendors}
        
        Search results:
        {json.dumps([r.model_dump() for r in results], indent=2)}
        
        Provide:
        1. Market leaders
        2. Challengers
        3. New entrants
        4. Competitive landscape overview
        
        Return as JSON: {{
            "market_leaders": [{{"name": "...", "position": "..."}}],
            "challengers": [...],
            "new_entrants": [...],
            "landscape": "..."
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                analysis = loads_llm_json(response)
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        await self.close()
        
        return {
            "category": category,
            "analysis": analysis,
            "sources_used": len(results)
        }
    
    async def analyze_pricing(
        self,
        category: str,
        product: str = None
    ) -> dict:
        """
        Analyze pricing in a market.
        
        Args:
            category: Market category
            product: Specific product (optional)
            
        Returns:
            Pricing analysis
        """
        search_tool = self._get_search_tool()
        
        query = f"{category} {product or ''} pricing cost analysis"
        results = await search_tool.search(
            query,
            max_results=10,
            topic="finance",
            search_depth="advanced"
        )
        
        prompt = f"""
        Analyze pricing for: {category} {product or ''}
        
        Research:
        {json.dumps([r.model_dump() for r in results], indent=2)}
        
        Provide:
        1. Price ranges
        2. Pricing models common in market
        3. Factors affecting pricing
        4. Cost optimization opportunities
        
        Return as JSON: {{
            "price_ranges": {{}},
            "pricing_models": [...],
            "price_factors": [...],
            "optimization_opportunities": [...]
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                analysis = loads_llm_json(response)
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        await self.close()
        
        return {
            "category": category,
            "product": product,
            "analysis": analysis,
            "sources_used": len(results)
        }
    
    async def industry_outlook(self, category: str) -> dict:
        """
        Generate industry outlook report.
        
        Args:
            category: Industry category
            
        Returns:
            Outlook report
        """
        search_tool = self._get_search_tool()
        
        queries = [
            f"{category} industry outlook 2025",
            f"{category} market forecast",
            f"{category} industry challenges opportunities"
        ]
        
        all_results = []
        for query in queries:
            results = await search_tool.search(query, max_results=3)
            all_results.extend([r.model_dump() for r in results])
        
        prompt = f"""
        Generate industry outlook for: {category}
        
        Research:
        {json.dumps(all_results, indent=2)}
        
        Provide comprehensive outlook including:
        1. Market size and growth
        2. Key opportunities
        3. Major challenges
        4. Technology trends
        5. Regulatory considerations
        6. Recommendations
        
        Return as JSON: {{
            "market_overview": "...",
            "growth_forecast": "...",
            "opportunities": [...],
            "challenges": [...],
            "tech_trends": [...],
            "regulatory": [...],
            "recommendations": [...]
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                outlook = loads_llm_json(response)
            else:
                outlook = {"raw_outlook": response}
        except json.JSONDecodeError:
            outlook = {"raw_outlook": response}
        
        await self.close()
        
        return {
            "category": category,
            "outlook": outlook,
            "sources_used": len(all_results)
        }
