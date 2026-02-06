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
    
    # RELEVANCE FILTER: Only include vendors that are actually relevant to the query
    # Use embeddings to calculate relevance score
    relevant_vendors = []
    if vendors:
        from src.llm.embeddings import get_embeddings
        import math
        
        embeddings = get_embeddings()
        query_embedding = embeddings.embed_query(query)
        
        for vendor in vendors:
            # Get vendor description for embedding
            vendor_text = f"{vendor.get('name', '')} {vendor.get('description', '')} {vendor.get('products', '')}"
            vendor_embedding = embeddings.embed_query(vendor_text[:500])
            
            # Calculate cosine similarity
            dot_product = sum(a * b for a, b in zip(query_embedding, vendor_embedding))
            norm1 = math.sqrt(sum(a * a for a in query_embedding))
            norm2 = math.sqrt(sum(b * b for b in vendor_embedding))
            
            if norm1 > 0 and norm2 > 0:
                similarity = dot_product / (norm1 * norm2)
            else:
                similarity = 0.0
            
            # Only include if relevance > threshold
            RELEVANCE_THRESHOLD = 0.5
            if similarity >= RELEVANCE_THRESHOLD:
                vendor["relevance_score"] = round(similarity, 3)
                relevant_vendors.append(vendor)
    
    # Search documents
    documents = await store.similarity_search(
        query=query,
        k=3,
        collection="documents"
    )
    
    # Filter documents by relevance too
    relevant_docs = []
    if documents:
        from src.llm.embeddings import get_embeddings
        import math
        
        embeddings = get_embeddings()
        query_embedding = embeddings.embed_query(query)
        
        for doc in documents:
            doc_text = f"{doc.get('title', '')} {doc.get('content', '')[:500]}"
            doc_embedding = embeddings.embed_query(doc_text[:500])
            
            dot_product = sum(a * b for a, b in zip(query_embedding, doc_embedding))
            norm1 = math.sqrt(sum(a * a for a in query_embedding))
            norm2 = math.sqrt(sum(b * b for b in doc_embedding))
            
            similarity = dot_product / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0
            
            if similarity >= 0.5:
                doc["relevance_score"] = round(similarity, 3)
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
        
        # Add document text to full content
        for doc_text in doc_search_results.get("extracted_texts", []):
            full_content.append({
                "url": doc_text.get("source_url", ""),
                "title": doc_text.get("title", doc_text.get("filename", "")),
                "content": doc_text.get("text", "")[:5000]
            })
        
        # AGGRESSIVE PRICING SCRAPING
        real_pricing = []
        try:
            from src.tools.pricing_scraper import PricingScraperTool
            pricing_scraper = PricingScraperTool()
            
            # Search for product prices if query mentions specific parts
            price_comparison = await pricing_scraper.compare_prices_across_vendors(
                query,
                vendors=["mouser", "digikey", "arrow", "newark"]
            )
            
            if price_comparison.get("prices"):
                real_pricing = price_comparison["prices"]
                
                # Add pricing info to full content for LLM context
                pricing_text = f"\n\n## Real-Time Pricing Data\n"
                pricing_text += f"Query: {query}\n"
                pricing_text += f"Best Price: ${price_comparison.get('best_price', 'N/A')} from {price_comparison.get('best_vendor', 'N/A')}\n\n"
                pricing_text += "| Vendor | Price | URL |\n|--------|-------|-----|\n"
                for p in price_comparison.get("price_comparison_table", []):
                    pricing_text += f"| {p['vendor']} | {p['price']} | {p['url'][:50]}... |\n"
                
                full_content.append({
                    "url": "pricing_comparison",
                    "title": "Real-Time Price Comparison",
                    "content": pricing_text
                })
        except Exception as e:
            print(f"Pricing scrape error: {e}")
        
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
        
        return {
            "analysis": analysis,
            "final_answer": response,
            "reasoning_steps": ["Generated final analysis"]
        }
        
    except Exception as e:
        await llm.close()
        return {
            "analysis": {"error": str(e)},
            "final_answer": f"Analysis generation failed: {str(e)}",
            "error": str(e)
        }


# ============== Routing Functions ==============

def decide_to_search(state: OrderIntelligenceState) -> Literal["search", "generate"]:
    """
    Conditional edge: decide whether to search or generate.
    
    ALWAYS search for comprehensive analysis - web data adds value
    even when local data is "sufficient".
    """
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", settings.max_web_searches)
    
    # Always do at least one web search for comprehensive analysis
    if iteration == 0:
        return "search"
    
    # After first search, check if we need more
    grade_decision = state.get("grade_decision", "needs_search")
    
    if iteration >= max_iterations:
        return "generate"
    
    # If grading says needs more search and we haven't exhausted iterations
    if grade_decision == "needs_search":
        return "search"
    
    return "generate"


# ============== Graph Builder ==============

def create_order_intelligence_graph():
    """
    Create the main Order Intelligence LangGraph workflow.
    
    Implements the Retrieve-Grade-Search-Generate loop:
    1. RETRIEVE: Pull relevant data from vector store
    2. GRADE: Assess relevance (threshold: 0.7)
    3. SEARCH: If grade fails, search web via Tavily
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
    
    initial_state = {
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
    
    result = await graph.ainvoke(initial_state)
    
    return {
        "query": query,
        "analysis": result.get("analysis"),
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
