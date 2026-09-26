"""
Order Intelligence Graph - Main LangGraph workflow
Implements the Retrieve-Grade-Search-Generate loop
"""
import json
from typing import Literal

from langgraph.graph import StateGraph, START, END

from src.graphs.states import OrderIntelligenceState
from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    VENDOR_ANALYST_PROMPT,
    RELEVANCE_GRADER_PROMPT,
    GRADING_PROMPT
)
from src.storage.chroma_store import get_vector_store
from src.tools.tavily_search import TavilySearchTool
from src.config import settings


# ============== Node Functions ==============

# Minimum cosine similarity for a stored record to count as relevant
VENDOR_RELEVANCE_THRESHOLD = 0.5
DOCUMENT_RELEVANCE_THRESHOLD = 0.4  # Lower threshold for internal docs


async def retrieve_node(state: OrderIntelligenceState) -> dict:
    """
    Retrieve relevant data from vector store.
    """
    query = state["query"]
    
    store = get_vector_store()
    
    # Search vendors
    vendors = await store.similarity_search(
        query=query,
        k=5,
        collection="vendors"
    )
    
    # Search documents
    documents = await store.similarity_search(
        query=query,
        k=3,
        collection="documents"
    )
    
    # RELEVANCE FILTER: the store uses cosine space, so "score" is already the
    # cosine similarity between the query and each stored record.
    relevant_vendors = []
    for vendor in vendors:
        if vendor.get("score", 0.0) >= VENDOR_RELEVANCE_THRESHOLD:
            vendor["relevance_score"] = round(vendor["score"], 3)
            relevant_vendors.append(vendor)
    
    relevant_docs = []
    for doc in documents:
        if doc.get("score", 0.0) >= DOCUMENT_RELEVANCE_THRESHOLD:
            doc["relevance_score"] = round(doc["score"], 3)
            relevant_docs.append(doc)
    
    return {
        "vendors": relevant_vendors,
        "documents": relevant_docs,
        "reasoning_steps": [f"Retrieved {len(vendors)} vendors, {len(relevant_vendors)} relevant | {len(documents)} documents, {len(relevant_docs)} relevant"]
    }


async def grade_node(state: OrderIntelligenceState) -> dict:
    """
    Grade the relevance of retrieved documents.
    Decides if we have enough information or need web search.
    """
    query = state["query"]
    vendors = state.get("vendors", [])
    documents = state.get("documents", [])
    
    # If we have no data, definitely need search
    if not vendors and not documents:
        return {
            "grade_decision": "needs_search",
            "relevance_scores": [],
            "reasoning_steps": ["No relevant data found in knowledge base, initiating web search"]
        }
    
    # Use LLM to grade relevance
    llm = OllamaClient()
    
    context = f"""
    Query: {query}
    
    Retrieved Vendors: {json.dumps(vendors[:3], indent=2)}
    Retrieved Documents: {json.dumps(documents[:2], indent=2)}
    """
    
    prompt = f"""
    {context}
    
    Grade the relevance of this retrieved information for answering the query.
    Return JSON with:
    - score: 0.0 to 1.0
    - reasoning: brief explanation
    - decision: "sufficient" if score >= {settings.relevance_threshold} else "needs_search"
    """
    
    try:
        response = await llm.generate(prompt, system=RELEVANCE_GRADER_PROMPT)
        await llm.close()
        
        # Parse response
        # Try to extract JSON from response
        if "{" in response and "}" in response:
            json_str = response[response.find("{"):response.rfind("}")+1]
            result = json.loads(json_str)
            score = result.get("score", 0.5)
            decision = result.get("decision", "needs_search")
        else:
            score = 0.5
            decision = "needs_search"
        
        return {
            "grade_decision": decision,
            "relevance_scores": [score],
            "reasoning_steps": [f"Relevance score: {score}, decision: {decision}"]
        }
        
    except Exception as e:
        await llm.close()
        # On error, proceed with search to be safe
        return {
            "grade_decision": "needs_search",
            "relevance_scores": [0.0],
            "reasoning_steps": [f"Grading error: {str(e)}, defaulting to web search"]
        }


async def web_search_node(state: OrderIntelligenceState) -> dict:
    """
    Search the web for additional information using Serper + Tavily.
    Uses WebResearchTool with DEEP SCRAPING for full page content access.
    """
    query = state["query"]
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", settings.max_web_searches)
    
    if iteration >= max_iterations:
        return {
            "reasoning_steps": ["Max web search iterations reached"]
        }
    
    try:
        from src.tools.web_research import WebResearchTool
        
        research_tool = WebResearchTool()
        
        # DEEP RESEARCH: Scrape full page content, not just snippets
        deep_results = await research_tool.deep_research_with_scraping(
            query,
            max_urls_to_scrape=10
        )
        
        # DIRECT DOCUMENT SEARCH: Find PDFs/docs anywhere on the internet
        doc_search_results = await research_tool.search_documents_directly(
            query,
            file_types=["pdf", "doc", "docx"],
            max_documents=5,
            save_dir="./data/downloads/query_docs"
        )
        
        # Get vendor-specific research with pricing
        vendors = state.get("vendors", [])
        vendor_data = []
        
        if vendors:
            for vendor in vendors[:3]:  # Top 3 vendors
                vendor_name = vendor.get("name", "")
                if vendor_name:
                    vendor_research = await research_tool.deep_vendor_research(
                        vendor_name,
                        include_pricing=True,
                        include_documents=True,
                        max_pages=5
                    )
                    vendor_data.append(vendor_research)
        
        # Combine all results
        all_results = deep_results.get("search_results", [])
        full_content = deep_results.get("full_content", [])
        
        # Add vendor research content
        for vd in vendor_data:
            full_content.extend(vd.get("full_content", []))
            all_results.extend(vd.get("search_results", []))
        
        # Add document text to full content (from web downloads)
        for doc_text in doc_search_results.get("extracted_texts", []):
            full_content.append({
                "url": doc_text.get("source_url", ""),
                "title": doc_text.get("title", doc_text.get("filename", "")),
                "content": doc_text.get("text", "")[:5000]
            })
        
        # CRITICAL: Add INTERNAL documents from vector store to full_content
        # These are your private/internal docs like contracts, bids, etc.
        internal_docs = state.get("documents", [])
        for doc in internal_docs:
            doc_text = doc.get("text", "") or ""
            file_name = doc.get("metadata", {}).get("file_name", "Internal Document")
            doc_type = doc.get("metadata", {}).get("type", "document")
            
            if doc_text.strip():
                full_content.insert(0, {  # Insert at start for priority
                    "url": f"internal://{file_name}",
                    "title": f"[INTERNAL {doc_type.upper()}] {file_name}",
                    "content": doc_text[:8000]  # More content for internal docs
                })
        
        # UNIVERSAL PRICING EXTRACTION (works for ANY content)
        real_pricing = []
        try:
            from src.tools.pricing_scraper import PricingScraperTool
            pricing_scraper = PricingScraperTool()
            
            # Use LLM to extract pricing from the scraped content
            all_content_text = "\n".join([
                f"{c.get('title', '')}: {c.get('content', '')}" 
                for c in full_content[:5]  # Top 5 pages
            ])
            
            if all_content_text.strip():
                # Use LLM to intelligently extract ANY pricing info
                pricing_result = await pricing_scraper.llm_extract_pricing(
                    content=all_content_text[:10000],
                    query_context=query
                )
                
                if pricing_result.get("success") and pricing_result.get("prices_found"):
                    # Format pricing for LLM context
                    pricing_text = f"\n\n## Extracted Pricing Data\n"
                    pricing_text += f"Query: {query}\n\n"
                    
                    for price_item in pricing_result.get("prices_found", [])[:10]:
                        item_name = price_item.get("item", "Unknown")
                        price_val = price_item.get("price", "N/A")
                        currency = price_item.get("currency", "")
                        price_type = price_item.get("type", "")
                        details = price_item.get("details", "")
                        
                        pricing_text += f"- **{item_name}**: {price_val} {currency} ({price_type})"
                        if details:
                            pricing_text += f" - {details}"
                        pricing_text += "\n"
                        
                        real_pricing.append({
                            "item": item_name,
                            "price": price_val,
                            "currency": currency,
                            "type": price_type
                        })
                    
                    if pricing_result.get("pricing_structure"):
                        pricing_text += f"\n**Pricing Structure**: {pricing_result['pricing_structure']}\n"
                    
                    if pricing_result.get("key_takeaways"):
                        pricing_text += "\n**Key Insights**:\n"
                        for insight in pricing_result.get("key_takeaways", []):
                            pricing_text += f"- {insight}\n"
                    
                    full_content.append({
                        "url": "pricing_extraction",
                        "title": "LLM-Extracted Pricing Data",
                        "content": pricing_text
                    })
        except Exception as e:
            print(f"LLM Pricing extraction error: {e}")
        
        # Deduplicate
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)
        
        return {
            "web_results": unique_results,
            "full_page_content": full_content,
            "pricing_data": [p for vd in vendor_data for p in vd.get("pricing_info", [])],
            "real_pricing": real_pricing,
            "documents_downloaded": doc_search_results.get("documents_downloaded", 0),
            "web_search_queries": [query],
            "iteration": iteration + 1,
            "reasoning_steps": [
                f"Deep research scraped {len(full_content)} pages with full content",
                f"Found {len(unique_results)} search results from {research_tool.available_sources}",
                f"Downloaded {doc_search_results.get('documents_downloaded', 0)} documents from internet",
                f"Scraped {len(real_pricing)} real product prices from distributors"
            ]
        }
        
    except Exception as e:
        # Fallback to basic Tavily if WebResearchTool fails
        try:
            search_tool = TavilySearchTool()
            results = await search_tool.search(query, max_results=5)
            web_results = [r.model_dump() for r in results]
            
            return {
                "web_results": web_results,
                "web_search_queries": [query],
                "iteration": iteration + 1,
                "reasoning_steps": [f"Fallback search returned {len(results)} results"]
            }
        except Exception as fallback_e:
            return {
                "web_results": [],
                "iteration": iteration + 1,
                "reasoning_steps": [f"Web search error: {str(e)}, fallback error: {str(fallback_e)}"],
                "error": str(e)
            }


async def generate_node(state: OrderIntelligenceState) -> dict:
    """
    Generate final analysis using all gathered information.
    Uses ContextOptimizer for smart relevance-based context selection.
    """
    query = state["query"]
    criteria = state.get("criteria", ["price", "quality", "reliability", "risk"])
    vendors = state.get("vendors", [])
    documents = state.get("documents", [])
    web_results = state.get("web_results", [])
    full_content = state.get("full_page_content", [])
    real_pricing = state.get("real_pricing", [])
    
    # Use ContextOptimizer for smart context selection
    from src.processors.context_optimizer import ContextOptimizer
    optimizer = ContextOptimizer()
    
    context_parts = []
    
    # Add vendors (always include all)
    if vendors:
        context_parts.append(f"**Vendors from Knowledge Base:**\n{json.dumps(vendors, indent=2)}")
    
    # Add real pricing (PRIORITY - always include all)
    if real_pricing:
        context_parts.append(f"**Real Product Prices (from distributor sites):**\n{json.dumps(real_pricing, indent=2)}")
    
    # Add documents (always include, but clean them)
    if documents:
        cleaned_docs = []
        for doc in documents[:5]:
            cleaned_docs.append({
                "title": doc.get("title", ""),
                "content": optimizer.clean_html(doc.get("content", ""))[:2000]
            })
        context_parts.append(f"**Documents:**\n{json.dumps(cleaned_docs, indent=2)}")
    
    # SMART CONTEXT: Optimize web results + full pages by relevance
    all_pages = []
    
    # Combine web results and full page content
    for wr in web_results:
        all_pages.append({
            "title": wr.get("title", ""),
            "url": wr.get("url", ""),
            "content": wr.get("content", "") or wr.get("snippet", "")
        })
    
    for page in full_content:
        all_pages.append({
            "title": page.get("title", ""),
            "url": page.get("url", ""),
            "content": page.get("content", "")
        })
    
    # Rank by relevance and select best content
    if all_pages:
        optimized = await optimizer.optimize_context(
            query=query,
            pages=all_pages,
            max_total_chars=20000,  # Allow more since we're being smart about it
            max_chars_per_page=3000
        )
        
        # Format for LLM
        web_context = optimizer.format_for_llm(optimized)
        context_parts.append(web_context)
    
    context = "\n\n".join(context_parts)
    
    prompt = f"""
    Query: {query}
    
    Criteria to evaluate: {', '.join(criteria)}
    
    Available Information:
    {context}
    
    Based on this information, provide a comprehensive analysis.
    
    IMPORTANT: Provide FULL reasoning for each score, DO NOT use "..." or abbreviations.
    
    Return JSON in this EXACT format:
    {{
        "overall_score": <number 0-100>,
        "recommendation": "<APPROVED|REVIEW|REJECTED>",
        "breakdown": {{
            "price": {{"score": <number>, "reasoning": "<2-3 sentences explaining WHY this score>"}},
            "quality": {{"score": <number>, "reasoning": "<2-3 sentences explaining WHY this score>"}},
            "reliability": {{"score": <number>, "reasoning": "<2-3 sentences explaining WHY this score>"}},
            "risk": {{"score": <number>, "reasoning": "<2-3 sentences explaining WHY this score>"}}
        }},
        "key_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
        "confidence": <number 0.0-1.0>
    }}
    
    Include specific prices, vendor names, and data points in your reasoning.
    """
    
    llm = OllamaClient()
    
    try:
        response = await llm.generate(prompt, system=GRADING_PROMPT, temperature=0.3)
        await llm.close()
        
        # Try to parse as JSON
        analysis = {}
        if "{" in response and "}" in response:
            json_str = response[response.find("{"):response.rfind("}")+1]
            try:
                analysis = json.loads(json_str)
            except json.JSONDecodeError:
                analysis = {"raw_response": response}
        else:
            analysis = {"raw_response": response}
        
        # EXTRACT STRUCTURED BID VARIABLES
        # Combine document text + LLM response for extraction
        from src.tools.bid_extractor import BidExtractor, BidVariables
        
        bid_extractor = BidExtractor()
        
        # Get internal document text for extraction
        internal_doc_text = ""
        for doc in documents:
            doc_text = doc.get("text", "") or ""
            if doc_text:
                file_name = doc.get("metadata", {}).get("file_name", "document")
                internal_doc_text += f"\n--- {file_name} ---\n{doc_text}\n"
        
        # Extract from document text first (most reliable)
        doc_source = "Internal Document"
        if internal_doc_text.strip():
            bid_vars = bid_extractor.extract_from_text(
                internal_doc_text, 
                source=doc_source,
                llm_analysis=analysis,
                query_context=query  # Pass query for vendor priority matching
            )
        else:
            # Fallback: extract from LLM response + web content
            combined_text = response
            for content in full_content[:3]:
                combined_text += f"\n{content.get('content', '')}"
            
            bid_vars = bid_extractor.extract_from_text(
                combined_text,
                source="Web + LLM Analysis",
                llm_analysis=analysis,
                query_context=query  # Pass query for vendor priority matching
            )
        
        return {
            "analysis": analysis,
            "bid_variables": bid_vars.to_dict(),
            "final_answer": response,
            "reasoning_steps": ["Generated final analysis"]
        }
        
    except Exception as e:
        await llm.close()
        return {
            "analysis": {"error": str(e)},
            "bid_variables": {},
            "final_answer": f"Analysis generation failed: {str(e)}",
            "error": str(e)
        }


# ============== Routing Functions ==============

def decide_to_search(state: OrderIntelligenceState) -> Literal["search", "generate"]:
    """
    Conditional edge: decide whether to search the web or generate directly.
    
    Follows the grade node's decision. Set ALWAYS_WEB_SEARCH=true to force
    one web research pass even when local data is sufficient.
    """
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", settings.max_web_searches)
    
    if iteration >= max_iterations:
        return "generate"
    
    if settings.always_web_search and iteration == 0:
        return "search"
    
    if state.get("grade_decision", "needs_search") == "needs_search":
        return "search"
    
    return "generate"


# ============== Graph Builder ==============

def create_order_intelligence_graph():
    """
    Create the main Order Intelligence LangGraph workflow.
    
    Implements the Retrieve-Grade-Search-Generate loop:
    1. RETRIEVE: Pull relevant data from vector store
    2. GRADE: LLM scores relevance (RELEVANCE_THRESHOLD, default 0.7)
    3. SEARCH: If the grade is insufficient, deep web research via Serper + Tavily
    4. GENERATE: Produce final analysis with reasoning chain
    
    Returns:
        Compiled LangGraph ready for execution
    """
    workflow = StateGraph(OrderIntelligenceState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade", grade_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("generate", generate_node)
    
    # Add edges
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "grade")
    
    # Conditional edge after grading
    workflow.add_conditional_edges(
        "grade",
        decide_to_search,
        {
            "search": "web_search",
            "generate": "generate"
        }
    )
    
    # After web search, go to generate
    workflow.add_edge("web_search", "generate")
    
    # Generate is the final step
    workflow.add_edge("generate", END)
    
    return workflow.compile()


# ============== High-level API ==============

def _initial_state(query: str, criteria: list[str] = None) -> dict:
    """Build the starting state for the Order Intelligence graph."""
    return {
        "query": query,
        "criteria": criteria or ["price", "quality", "reliability", "risk"],
        "vendors": [],
        "documents": [],
        "web_results": [],
        "web_search_queries": [],
        "relevance_scores": [],
        "grade_decision": "",
        "reasoning_steps": [],
        "analysis": None,
        "final_answer": "",
        "iteration": 0,
        "max_iterations": settings.max_web_searches,
        "error": None
    }


def _format_result(query: str, result: dict) -> dict:
    """Shape the final graph state into the public analysis result."""
    return {
        "query": query,
        "analysis": result.get("analysis"),
        "bid_variables": result.get("bid_variables", {}),
        "final_answer": result.get("final_answer"),
        "reasoning_chain": result.get("reasoning_steps", []),
        "sources": {
            "vendors": len(result.get("vendors", [])),
            "documents": len(result.get("documents", [])),
            "web_results": len(result.get("web_results", []))
        },
        "web_searches_performed": result.get("iteration", 0),
        "error": result.get("error")
    }


async def analyze_query(
    query: str,
    criteria: list[str] = None
) -> dict:
    """
    High-level function to analyze a query using the Order Intelligence graph.
    
    Args:
        query: The user's query
        criteria: Optional list of criteria to evaluate
        
    Returns:
        Analysis result dict
    """
    graph = create_order_intelligence_graph()
    result = await graph.ainvoke(_initial_state(query, criteria))
    return _format_result(query, result)


async def stream_analysis(query: str, criteria: list[str] = None):
    """
    Run the graph node by node.
    
    Yields ("node", node_name, update) after each node finishes, then
    ("done", None, result) with the same shape analyze_query returns.
    """
    graph = create_order_intelligence_graph()
    final_state = {}
    async for mode, chunk in graph.astream(
        _initial_state(query, criteria), stream_mode=["updates", "values"]
    ):
        if mode == "values":
            final_state = chunk
        else:
            for node_name, update in chunk.items():
                yield "node", node_name, update or {}
    yield "done", None, _format_result(query, final_state)

