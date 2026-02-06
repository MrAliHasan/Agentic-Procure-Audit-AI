"""
Intelligent Search Agent - Multi-step LLM-guided search
Adapted from OmniExtract-AI for local Ollama LLM usage.
"""

import json
import re
import asyncio
from typing import Dict, Any, List, Optional

from src.llm.ollama_client import OllamaClient
from src.tools.serper_search import search as serper_search
from src.config import settings


async def intelligent_search_agent(
    original_prompt: str,
    num_results: int = 10
) -> dict:
    """
    Intelligent Search Agent - Understands the prompt and executes multi-step searches.
    
    This agent:
    1. Analyzes the user's prompt to understand what data they need
    2. Plans a series of search queries
    3. Executes searches and extracts relevant data
    4. AUTO-RETRIES with query variations if results are incomplete
    5. Compiles final structured results
    
    Uses local Ollama LLM for planning and extraction.
    
    Args:
        original_prompt: The user's original query
        num_results: Number of results per search query
        
    Returns:
        dict: Structured results with extracted data
    """
    llm = OllamaClient(timeout=300)
    
    try:
        # Step 1: Use LLM to understand the prompt and plan searches
        planning_prompt = f"""You are an intelligent search agent. Analyze this user request and plan the searches needed.

USER REQUEST:
{original_prompt[:2000]}

YOUR TASK:
1. Understand what information the user wants to find
2. Plan a series of Google searches to find this information
3. Think step-by-step about what queries will get the best results

SEARCH STRATEGY GUIDELINES:
- To find product pricing: "[Product Name] price [Year] [Location]"
- To find vendors/suppliers: "[Category] suppliers [Location] reviews pricing"
- To find e-commerce platforms: "[Platform name] fees pricing commission [Location]"
- To find company information: "[Company] about reviews pricing plans"
- To compare products: "best [product category] comparison [Year]"

OUTPUT FORMAT (JSON only):
{{
    "understanding": "Brief summary of what user wants",
    "data_points_needed": ["list of specific data to find"],
    "search_plan": [
        {{
            "step": 1,
            "purpose": "what this search will find",
            "query": "the exact Google search query"
        }}
    ]
}}

Generate 3-6 targeted searches. Be specific with queries. Return only JSON."""

        # Get search plan using local LLM
        plan_response = await llm.generate(
            planning_prompt,
            system="You are a search planning expert. Return only valid JSON.",
            temperature=0.3
        )
        
        # Parse plan
        json_match = re.search(r'\{[\s\S]*\}', plan_response)
        if not json_match:
            return {"error": "Failed to create search plan", "raw_response": plan_response}
        
        try:
            search_plan = json.loads(json_match.group())
        except json.JSONDecodeError:
            return {"error": "Failed to parse search plan", "raw_response": plan_response}
        
        # Step 2: Execute all searches using Serper
        all_search_results = []
        total_results = 0
        
        for step in search_plan.get("search_plan", []):
            query = step.get("query", "")
            if query:
                results = await serper_search(query, num_results=num_results)
                step_results = {
                    "step": step.get("step"),
                    "purpose": step.get("purpose"),
                    "query": query,
                    "results": results.get("organic", []) if isinstance(results, dict) else results
                }
                all_search_results.append(step_results)
                total_results += len(step_results["results"])
        
        # Step 3: Extract and synthesize information using LLM
        extraction_prompt = f"""You are a data extraction expert. Extract comprehensive information from search results.

ORIGINAL USER REQUEST:
{original_prompt[:1500]}

SEARCH PLAN:
{json.dumps(search_plan.get("data_points_needed", []), indent=2)}

SEARCH RESULTS:
{json.dumps(all_search_results, indent=2)[:12000]}

YOUR TASK:
Extract and synthesize the most relevant information to answer the user's query.

For pricing queries, look for:
- Specific prices with currency
- Fee structures (commission %, transaction fees, etc.)
- Pricing tiers or plans
- Price comparisons between vendors

For vendor/platform queries, look for:
- Platform names and features
- User reviews and ratings
- Pros and cons
- Market share or popularity

EXTRACTION RULES:
- Only include REAL data found in search results - never fabricate
- Include the source URL for each data point
- Organize data logically based on the query type
- Be comprehensive but structured

OUTPUT FORMAT (JSON):
{{
    "summary": "Brief answer to the user's query",
    "data": [
        {{
            "item": "Name of product/vendor/platform",
            "pricing": "Pricing details if available",
            "features": ["key features"],
            "source_url": "URL where this was found",
            "notes": "Any additional relevant info"
        }}
    ],
    "key_insights": ["insight 1", "insight 2"],
    "data_confidence": "high/medium/low based on data quality"
}}

Return pure JSON only."""

        final_response = await llm.generate(
            extraction_prompt,
            system="You are a data extraction expert. Return only valid JSON with extracted information.",
            temperature=0.2
        )
        
        # Parse final result
        json_match = re.search(r'\{[\s\S]*\}', final_response)
        final_result = None
        
        if json_match:
            try:
                final_result = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        await llm.close()
        
        # Add metadata
        if final_result:
            final_result["_search_metadata"] = {
                "agent": "intelligent_search_agent",
                "searches_executed": len(all_search_results),
                "total_results_found": total_results,
                "understanding": search_plan.get("understanding", "")
            }
            return final_result
        
        return {
            "raw_response": final_response,
            "search_results": all_search_results,
            "search_plan": search_plan,
            "_search_metadata": {
                "agent": "intelligent_search_agent",
                "searches_executed": len(all_search_results),
                "total_results_found": total_results
            }
        }
        
    except Exception as e:
        await llm.close()
        return {"error": str(e)}


async def smart_url_extract(
    url: str,
    extraction_prompt: str
) -> dict:
    """
    SmartScraper-style extraction - fetch URL and use LLM to extract structured data.
    
    Args:
        url: URL to fetch and extract from
        extraction_prompt: What data to extract (natural language)
        
    Returns:
        dict: Extracted structured data
    """
    from src.tools.url_scraper import scrape_url_content
    
    # Fetch the page content
    page_content = await scrape_url_content(url, use_browser=True)
    
    if not page_content or not page_content.get("content"):
        return {"error": f"Failed to fetch content from {url}"}
    
    content = page_content.get("content", "")[:8000]  # Limit content size
    
    # Use LLM to extract data
    llm = OllamaClient(timeout=300)
    
    try:
        prompt = f"""You are a data extraction expert. Extract structured data from this webpage.

EXTRACTION REQUEST:
{extraction_prompt}

WEBPAGE CONTENT:
{content}

Extract the requested information and return it as a well-structured JSON object.
Include confidence scores for each extracted field.
If information is not found, indicate with null or empty string.

Return only valid JSON."""

        response = await llm.generate(
            prompt,
            system="You are a data extraction expert. Return only valid JSON.",
            temperature=0.1
        )
        await llm.close()
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                result = json.loads(json_match.group())
                result["_source_url"] = url
                return result
            except json.JSONDecodeError:
                pass
        
        return {"raw_response": response, "_source_url": url}
        
    except Exception as e:
        await llm.close()
        return {"error": str(e), "_source_url": url}
