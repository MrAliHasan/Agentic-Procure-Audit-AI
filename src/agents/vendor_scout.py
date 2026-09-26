"""
Vendor Scout Agent - Specialized for vendor research and analysis
"""
import json
from src.llm.json_utils import loads_llm_json
from typing import Optional

from src.agents.base import BaseAgent
from src.llm.prompts import VENDOR_ANALYST_PROMPT
from src.tools.tavily_search import TavilySearchTool
from src.storage.chroma_store import get_vector_store
from src.models.vendor import Vendor


class VendorScoutAgent(BaseAgent):
    """
    Agent specialized in vendor discovery and research.
    
    Capabilities:
    - Search for vendors in specific categories
    - Research vendor backgrounds
    - Identify strengths and weaknesses
    - Find alternative vendors
    """
    
    def __init__(self, include_web_research: bool = True):
        """
        Initialize the Vendor Scout.
        
        Args:
            include_web_research: Whether to use web search
        """
        super().__init__(
            name="Vendor Scout",
            system_prompt=VENDOR_ANALYST_PROMPT,
            temperature=0.3  # More focused/factual
        )
        self.include_web_research = include_web_research
        self._search_tool: Optional[TavilySearchTool] = None
    
    def _get_search_tool(self) -> TavilySearchTool:
        """Get or create search tool."""
        if self._search_tool is None:
            self._search_tool = TavilySearchTool()
        return self._search_tool
    
    async def run(self, input_data: dict) -> dict:
        """
        Execute vendor research.
        
        Args:
            input_data: {
                "task": "research" | "discover" | "compare",
                "vendor_name": str (for research),
                "category": str (for discover),
                "vendors": list[str] (for compare)
            }
            
        Returns:
            Research results
        """
        task = input_data.get("task", "research")
        
        if task == "research":
            return await self.research_vendor(input_data.get("vendor_name", ""))
        elif task == "discover":
            return await self.discover_vendors(
                input_data.get("category", ""),
                input_data.get("criteria", {})
            )
        elif task == "compare":
            return await self.compare_vendors(input_data.get("vendors", []))
        else:
            raise ValueError(f"Unknown task: {task}")
    
    async def research_vendor(self, vendor_name: str) -> dict:
        """
        Research a specific vendor.
        
        Args:
            vendor_name: Vendor to research
            
        Returns:
            Research findings
        """
        # Check local knowledge first
        store = get_vector_store()
        local_data = await store.similarity_search(
            vendor_name, k=3, collection="vendors"
        )
        
        # Web research if enabled
        web_data = {}
        if self.include_web_research:
            search_tool = self._get_search_tool()
            web_data = await search_tool.search_vendor_info(vendor_name)
        
        # Synthesize with LLM
        prompt = f"""
        Research the following vendor: {vendor_name}
        
        Local Knowledge:
        {json.dumps(local_data, indent=2, default=str)}
        
        Web Research:
        {json.dumps(web_data, indent=2, default=str)}
        
        Provide a comprehensive analysis including:
        1. Company overview
        2. Products/services
        3. Strengths
        4. Weaknesses/concerns
        5. Recommendations
        
        Return as JSON with these keys: overview, products, strengths, weaknesses, recommendations
        """
        
        response = await self.think(prompt)
        
        # Parse response
        try:
            if "{" in response and "}" in response:
                analysis = loads_llm_json(response)
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}
        
        await self.close()
        
        return {
            "vendor_name": vendor_name,
            "analysis": analysis,
            "sources": {
                "local": len(local_data),
                "web": web_data.get("total_sources", 0)
            }
        }
    
    async def discover_vendors(
        self,
        category: str,
        criteria: dict = None
    ) -> dict:
        """
        Discover vendors in a category.
        
        Args:
            category: Product/service category
            criteria: Optional filtering criteria
            
        Returns:
            List of discovered vendors
        """
        criteria = criteria or {}
        
        # Search local knowledge
        store = get_vector_store()
        local_vendors = await store.similarity_search(
            f"{category} vendor supplier",
            k=10,
            collection="vendors"
        )
        
        # Web discovery if enabled
        web_vendors = []
        if self.include_web_research:
            search_tool = self._get_search_tool()
            query = f"top {category} vendors suppliers companies"
            results = await search_tool.search(query, max_results=10)
            web_vendors = [r.model_dump() for r in results]
        
        # Analyze with LLM
        prompt = f"""
        Find vendors for category: {category}
        
        Criteria: {json.dumps(criteria, default=str)}
        
        Local Vendors Found:
        {json.dumps(local_vendors, indent=2, default=str)}
        
        Web Search Results:
        {json.dumps(web_vendors, indent=2, default=str)}
        
        Extract and list all vendor names mentioned.
        For each vendor, provide: name, brief description, relevance score (0-100).
        
        Return as JSON: {{"vendors": [{{"name": "...", "description": "...", "relevance": 85}}]}}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                result = loads_llm_json(response)
            else:
                result = {"vendors": []}
        except json.JSONDecodeError:
            result = {"vendors": []}
        
        await self.close()
        
        return {
            "category": category,
            "criteria": criteria,
            "vendors": result.get("vendors", []),
            "sources": {
                "local": len(local_vendors),
                "web": len(web_vendors)
            }
        }
    
    async def compare_vendors(self, vendor_names: list[str]) -> dict:
        """
        Compare multiple vendors.
        
        Args:
            vendor_names: List of vendors to compare
            
        Returns:
            Comparison analysis
        """
        vendor_data = []
        
        for name in vendor_names:
            research = await self.research_vendor(name)
            vendor_data.append(research)
        
        # Comparative analysis
        prompt = f"""
        Compare these vendors:
        
        {json.dumps(vendor_data, indent=2, default=str)}
        
        Provide:
        1. Side-by-side comparison
        2. Best for each criterion
        3. Overall recommendation
        4. Trade-offs to consider
        
        Return as JSON: {{
            "comparison": [...],
            "best_per_criterion": {{}},
            "recommendation": "...",
            "trade_offs": [...]
        }}
        """
        
        response = await self.think(prompt)
        
        try:
            if "{" in response and "}" in response:
                comparison = loads_llm_json(response)
            else:
                comparison = {"raw_comparison": response}
        except json.JSONDecodeError:
            comparison = {"raw_comparison": response}
        
        await self.close()
        
        return {
            "vendors_compared": vendor_names,
            "comparison": comparison,
            "individual_research": vendor_data
        }
