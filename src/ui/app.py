"""
Streamlit Web UI for Sovereign Order Intelligence
"""
import streamlit as st
import asyncio
import json
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Sovereign Order Intelligence",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .score-bar {
        height: 20px;
        border-radius: 10px;
        background: #e0e0e0;
    }
    .score-fill {
        height: 100%;
        border-radius: 10px;
    }
    .approved { background: linear-gradient(90deg, #00c853, #69f0ae); }
    .review { background: linear-gradient(90deg, #ffa000, #ffd54f); }
    .rejected { background: linear-gradient(90deg, #ff1744, #ff8a80); }
</style>
""", unsafe_allow_html=True)


# ============== Helper Functions ==============

def run_async(coro):
    """Run async function in Streamlit."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ============== Sidebar ==============

st.sidebar.markdown("# 🏭 SOI")
st.sidebar.markdown("**Sovereign Order Intelligence**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "🔍 Analyze Query", "📊 Vendor Grading", "📄 Document Processing", "🌐 Web Research", "⚙️ Settings"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Quick Stats")


# Show stats
@st.cache_data(ttl=60)
def get_stats():
    try:
        from src.storage.chroma_store import get_vector_store
        store = get_vector_store()
        return run_async(store.get_stats())
    except:
        return {}


stats = get_stats()
for collection, data in stats.items():
    st.sidebar.metric(collection, data.get("count", 0))


# ============== Dashboard ==============

if page == "🏠 Dashboard":
    st.markdown('<p class="main-header">Sovereign Order Intelligence</p>', unsafe_allow_html=True)
    st.markdown("**AI-Powered Supply Chain & Vendor Management** | 100% Local")
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 🔒 AI Sovereignty")
        st.markdown("All data stays local. GDPR compliant by design.")
    
    with col2:
        st.markdown("### 🧠 Agentic RAG")
        st.markdown("Retrieve → Grade → Search → Generate loop.")
    
    with col3:
        st.markdown("### 📊 Explainable AI")
        st.markdown("Full reasoning traces for every decision.")
    
    with col4:
        st.markdown("### 🌐 Real-Time Intel")
        st.markdown("Live market research via web search.")
    
    st.markdown("---")
    
    # Quick actions
    st.markdown("### Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Analyze Query", use_container_width=True):
            st.switch_page = "🔍 Analyze Query"
    
    with col2:
        if st.button("📊 Grade Vendor", use_container_width=True):
            st.switch_page = "📊 Vendor Grading"
    
    with col3:
        if st.button("📄 Process Document", use_container_width=True):
            st.switch_page = "📄 Document Processing"


# ============== Analyze Query ==============

elif page == "🔍 Analyze Query":
    st.markdown("## 🔍 Analyze Query")
    st.markdown("Use the agentic RAG workflow to analyze any supply chain question.")
    
    query = st.text_area(
        "Enter your query",
        placeholder="e.g., 'Compare the top 3 electronic component suppliers for reliability and price'",
        height=100
    )
    
    criteria = st.multiselect(
        "Evaluation Criteria",
        ["price", "quality", "reliability", "risk", "delivery", "support"],
        default=["price", "quality", "reliability", "risk"]
    )
    
    if st.button("🚀 Analyze", type="primary"):
        if query:
            with st.spinner("Running Order Intelligence workflow..."):
                try:
                    from src.graphs.order_intelligence import analyze_query
                    result = run_async(analyze_query(query, list(criteria)))
                    
                    # Display results
                    st.markdown("### Results")
                    
                    # Sources summary
                    sources = result.get("sources", {})
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Vendors Found", sources.get("vendors", 0))
                    col2.metric("Documents", sources.get("documents", 0))
                    col3.metric("Web Results", sources.get("web_results", 0))
                    
                    # Analysis
                    st.markdown("### Analysis")
                    st.markdown(result.get("final_answer", "No result"))
                    
                    # Reasoning chain
                    with st.expander("🧠 Reasoning Chain"):
                        for step in result.get("reasoning_chain", []):
                            st.markdown(f"- {step}")
                    
                    # Raw data
                    with st.expander("📊 Raw Data"):
                        st.json(result.get("analysis", {}))
                        
                except Exception as e:
                    st.error(f"Analysis failed: {e}")
        else:
            st.warning("Please enter a query")


# ============== Vendor Grading ==============

elif page == "📊 Vendor Grading":
    st.markdown("## 📊 Vendor Grading")
    st.markdown("Grade and compare vendors with explainable AI scoring.")
    
    tab1, tab2 = st.tabs(["Grade Single Vendor", "Compare Vendors"])
    
    with tab1:
        vendor_name = st.text_input("Vendor Name", placeholder="e.g., Acme Corp")
        
        col1, col2 = st.columns(2)
        with col1:
            include_web = st.checkbox("Include Web Research", value=True)
        with col2:
            criteria = st.multiselect(
                "Criteria",
                ["price", "quality", "reliability", "risk"],
                default=["price", "quality", "reliability", "risk"],
                key="grade_criteria"
            )
        
        if st.button("📊 Grade Vendor", type="primary"):
            if vendor_name:
                with st.spinner(f"Grading {vendor_name}..."):
                    try:
                        from src.processors.vendor_grader import VendorGrader
                        from src.tools.tavily_search import TavilySearchTool
                        from src.processors.report_generator import ReportGenerator
                        
                        grader = VendorGrader()
                        
                        web_research = None
                        if include_web:
                            try:
                                search_tool = TavilySearchTool()
                                research = run_async(search_tool.search_vendor_info(vendor_name))
                                web_research = research.get("results", {})
                            except:
                                pass
                        
                        analysis = run_async(grader.grade(
                            vendor_name,
                            {"name": vendor_name},
                            list(criteria),
                            web_research
                        ))
                        
                        # Display results
                        st.markdown("### Results")
                        
                        # Overall metrics
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Overall Score", f"{analysis.overall_score}/100")
                        col2.metric("Recommendation", analysis.recommendation)
                        col3.metric("Confidence", f"{analysis.confidence:.0%}")
                        
                        # Score breakdown
                        st.markdown("### Score Breakdown")
                        for criterion, detail in analysis.breakdown.items():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"**{criterion.title()}**")
                            with col2:
                                st.progress(detail.score / 100)
                                st.caption(detail.reasoning[:200])
                        
                        # Generate report
                        reporter = ReportGenerator()
                        report = run_async(reporter.vendor_report(analysis))
                        
                        with st.expander("📝 Full Report"):
                            st.markdown(report)
                            
                    except Exception as e:
                        st.error(f"Grading failed: {e}")
            else:
                st.warning("Please enter a vendor name")
    
    with tab2:
        st.markdown("### Compare Multiple Vendors")
        
        vendors_input = st.text_area(
            "Enter vendor names (one per line)",
            placeholder="Acme Corp\nGlobal Supply Co\nTech Parts Inc",
            height=100
        )
        
        if st.button("🔄 Compare", type="primary"):
            vendors = [v.strip() for v in vendors_input.split("\n") if v.strip()]
            if len(vendors) >= 2:
                with st.spinner("Comparing vendors..."):
                    try:
                        from src.processors.vendor_grader import VendorGrader
                        
                        grader = VendorGrader()
                        vendor_data = [(v, {"name": v}) for v in vendors]
                        comparison = run_async(grader.compare(vendor_data))
                        
                        st.markdown("### Comparison Results")
                        st.markdown(f"**Winner**: {comparison.get('summary', '')}")
                        
                        # Rankings table
                        st.markdown("### Rankings")
                        for i, analysis in enumerate(comparison.get("analyses", []), 1):
                            cols = st.columns([1, 3, 2, 2])
                            cols[0].markdown(f"**#{i}**")
                            cols[1].markdown(analysis.get("vendor_name", ""))
                            cols[2].markdown(f"{analysis.get('overall_score', 0)}/100")
                            cols[3].markdown(analysis.get("recommendation", ""))
                            
                    except Exception as e:
                        st.error(f"Comparison failed: {e}")
            else:
                st.warning("Please enter at least 2 vendors")


# ============== Document Processing ==============

elif page == "📄 Document Processing":
    st.markdown("## 📄 Document Processing")
    st.markdown("Upload and extract data from invoices, contracts, and bids.")
    
    uploaded_file = st.file_uploader(
        "Upload Document",
        type=["pdf", "png", "jpg", "jpeg"],
        help="Supported: PDF, PNG, JPG"
    )
    
    doc_type = st.selectbox(
        "Document Type",
        ["auto", "invoice", "contract", "bid"],
        help="Auto-detect or specify manually"
    )
    
    if uploaded_file:
        if st.button("🔄 Process Document", type="primary"):
            with st.spinner("Processing document..."):
                try:
                    import tempfile
                    from src.processors.document_processor import DocumentProcessor
                    
                    # Save uploaded file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name
                    
                    processor = DocumentProcessor()
                    result = run_async(processor.process(tmp_path, doc_type))
                    
                    # Cleanup
                    Path(tmp_path).unlink(missing_ok=True)
                    
                    # Display results
                    doc = result.document
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Type", doc.type.upper())
                    col2.metric("Confidence", f"{doc.confidence:.0%}")
                    col3.metric("Status", doc.validation_status)
                    
                    if doc.extracted_fields:
                        st.markdown("### Extracted Fields")
                        st.json(doc.extracted_fields)
                    
                    with st.expander("📝 Raw Text"):
                        st.text(doc.extracted_text[:2000])
                    
                    if result.errors:
                        st.error(f"Errors: {', '.join(result.errors)}")
                    
                    if result.warnings:
                        st.warning(f"Warnings: {', '.join(result.warnings)}")
                        
                except Exception as e:
                    st.error(f"Processing failed: {e}")


# ============== Web Research ==============

elif page == "🌐 Web Research":
    st.markdown("## 🌐 Web Research")
    st.markdown("Research vendors and markets using real-time web search.")
    
    tab1, tab2, tab3 = st.tabs(["Vendor Research", "Market Trends", "Risk Analysis"])
    
    with tab1:
        vendor_name = st.text_input("Vendor Name", placeholder="e.g., SAP", key="research_vendor")
        
        if st.button("🔍 Research Vendor", type="primary"):
            if vendor_name:
                with st.spinner(f"Researching {vendor_name}..."):
                    try:
                        from src.tools.tavily_search import TavilySearchTool
                        
                        search_tool = TavilySearchTool()
                        info = run_async(search_tool.search_vendor_info(vendor_name))
                        
                        for aspect, results in info.get("results", {}).items():
                            st.markdown(f"### {aspect.title()}")
                            for r in results[:3]:
                                st.markdown(f"**{r.get('title', '')}**")
                                st.markdown(r.get('content', '')[:300] + "...")
                                st.caption(r.get('url', ''))
                                st.markdown("---")
                                
                    except Exception as e:
                        st.error(f"Research failed: {e}")
    
    with tab2:
        category = st.text_input("Market Category", placeholder="e.g., electronic components")
        
        if st.button("📊 Research Market"):
            if category:
                with st.spinner(f"Researching {category} market..."):
                    try:
                        from src.tools.tavily_search import TavilySearchTool
                        
                        search_tool = TavilySearchTool()
                        trends = run_async(search_tool.search_market_trends(category))
                        
                        st.markdown("### Market Trends")
                        for result in trends.get("results", [])[:5]:
                            st.markdown(f"**{result.get('title', '')}**")
                            st.markdown(result.get('content', '')[:300] + "...")
                            st.caption(result.get('url', ''))
                            st.markdown("---")
                            
                    except Exception as e:
                        st.error(f"Research failed: {e}")
    
    with tab3:
        vendor_name = st.text_input("Vendor Name", placeholder="e.g., Acme Corp", key="risk_vendor")
        
        if st.button("⚠️ Check Risks"):
            if vendor_name:
                with st.spinner(f"Checking risks for {vendor_name}..."):
                    try:
                        from src.tools.tavily_search import TavilySearchTool
                        
                        search_tool = TavilySearchTool()
                        risks = run_async(search_tool.search_vendor_risks(vendor_name))
                        
                        risk_level = risks.get("risk_level", "unknown")
                        colors = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                        
                        st.markdown(f"### Risk Level: {colors.get(risk_level, '⚪')} {risk_level.upper()}")
                        st.metric("Risk Factors Found", risks.get("risk_factors_found", 0))
                        
                        if risks.get("findings"):
                            st.markdown("### Findings")
                            for finding in risks["findings"][:5]:
                                st.markdown(f"**{finding.get('title', '')}**")
                                st.markdown(finding.get('content', '')[:200])
                                st.markdown("---")
                                
                    except Exception as e:
                        st.error(f"Risk check failed: {e}")


# ============== Settings ==============

elif page == "⚙️ Settings":
    st.markdown("## ⚙️ Settings")
    
    tab1, tab2, tab3 = st.tabs(["System Status", "Configuration", "Knowledge Base"])
    
    with tab1:
        st.markdown("### System Status")
        
        with st.spinner("Checking system status..."):
            try:
                from src.llm.ollama_client import OllamaClient
                from src.config import settings
                
                client = OllamaClient()
                ollama_ok = run_async(client.health_check())
                models = run_async(client.list_models()) if ollama_ok else []
                run_async(client.close())
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### Ollama")
                    if ollama_ok:
                        st.success(f"✓ Connected ({settings.ollama_model})")
                        st.caption(f"Available models: {', '.join(models[:5])}")
                    else:
                        st.error("✗ Not connected")
                
                with col2:
                    st.markdown("### Tavily")
                    if settings.tavily_api_key:
                        st.success("✓ API key configured")
                    else:
                        st.warning("⚠ API key not set")
                        
            except Exception as e:
                st.error(f"Status check failed: {e}")
    
    with tab2:
        st.markdown("### Configuration")
        st.markdown("Current configuration values:")
        
        from src.config import settings
        
        config_data = {
            "Ollama Host": settings.ollama_host,
            "Ollama Model": settings.ollama_model,
            "Relevance Threshold": settings.relevance_threshold,
            "Max Web Searches": settings.max_web_searches,
            "Scoring Weights": settings.scoring_weights
        }
        
        for key, value in config_data.items():
            st.text(f"{key}: {value}")
    
    with tab3:
        st.markdown("### Knowledge Base")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 View Stats"):
                stats = get_stats()
                st.json(stats)
        
        with col2:
            if st.button("🗑️ Clear Cache"):
                try:
                    from src.storage.cache import get_cache
                    cache = get_cache()
                    count = run_async(cache.invalidate())
                    st.success(f"Cleared {count} cache entries")
                except Exception as e:
                    st.error(f"Failed: {e}")
