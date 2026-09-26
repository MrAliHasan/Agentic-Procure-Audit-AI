"""
Streamlit Web UI for Agentic Procure-Audit AI

Run with:  soi ui   (or: streamlit run src/ui/app.py)
"""
import asyncio
import json
import sys
import tempfile
import time
import uuid
from pathlib import Path

import streamlit as st

# Make `src` importable when launched directly with `streamlit run`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import settings  # noqa: E402
from src.ui import theme as ui  # noqa: E402

st.set_page_config(
    page_title="Procure-Audit AI",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject_css()


# ============== Helpers ==============

def run_async(coro):
    """Run a coroutine from Streamlit's script thread."""
    return asyncio.run(coro)


@st.cache_resource(show_spinner="Warming up the embedding model…")
def warm_up_embeddings() -> bool:
    """Load the embedding model once per server so the first search is instant."""
    try:
        from src.storage.chroma_store import get_vector_store
        run_async(get_vector_store().similarity_search("warm up", k=1, collection="vendors"))
        return True
    except Exception:
        return False


@st.cache_data(ttl=30, show_spinner=False)
def get_stats() -> dict:
    try:
        from src.storage.chroma_store import get_vector_store
        return run_async(get_vector_store().get_stats())
    except Exception:
        return {}


@st.cache_data(ttl=30, show_spinner=False)
def get_llm_status() -> tuple[bool, list[str]]:
    try:
        from src.llm.ollama_client import OllamaClient

        async def check():
            client = OllamaClient()
            try:
                ok = await client.health_check()
                return ok, (await client.list_models() if ok else [])
            finally:
                await client.close()

        return run_async(check())
    except Exception:
        return False, []


def llm_label() -> tuple[bool, str]:
    """Return (is_available, human label) for the active LLM backend."""
    ollama_ok, _ = get_llm_status()
    if ollama_ok:
        return True, f"Ollama · {settings.ollama_model}"
    if settings.openrouter_api_key:
        return True, f"OpenRouter · {settings.openrouter_model}"
    return False, "No LLM available"


def count(stats: dict, name: str) -> int:
    return stats.get(name, {}).get("count", 0)


PAGES = [
    "Overview",
    "Agent Analysis",
    "Vendor Grading",
    "Company Intelligence",
    "Document Intelligence",
    "Market Research",
    "Knowledge Base",
    "System",
]


def go_to(page: str):
    st.session_state.page = page


if "page" not in st.session_state:
    st.session_state.page = PAGES[0]

warm_up_embeddings()


# ============== Sidebar ==============

with st.sidebar:
    ui.render("""
    <div class="brand">
    <div class="mark">Procure<em>/</em>Audit</div>
    <div class="t2">Agentic procurement intelligence</div>
    </div>
    """)
    page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed")

    stats = get_stats()
    llm_ok, llm_name = llm_label()
    dot = ui.COLORS["green"] if llm_ok else ui.COLORS["red"]
    ui.render(f"""
    <div class="side-label">Knowledge base</div>
    <div class="side-stat"><span>Vendors</span><b>{count(stats, 'vendors')}</b></div>
    <div class="side-stat"><span>Documents</span><b>{count(stats, 'documents')}</b></div>
    <div class="side-label">Engine</div>
    <div class="side-stat"><span><span class="status-dot" style="background:{dot}"></span>LLM</span>
    <b style="font-size:0.78rem">{ui.esc(llm_name)}</b></div>
    <div class="side-stat"><span>Web search</span><b>{'Serper + Tavily' if settings.serper_api_key and settings.tavily_api_key else ('Tavily' if settings.tavily_api_key else ('Serper' if settings.serper_api_key else 'Off'))}</b></div>
    """)


# ============== Command Center ==============

def page_command_center():
    ui.render("""
    <div class="hero">
    <div class="eyebrow"><b>●</b> Local-first — Explainable — Agentic</div>
    <h1>Every vendor decision,<br><em>audited</em> by an agent.</h1>
    <p>Ask about vendors, bids or markets. The agent searches your private knowledge base,
    decides for itself whether it needs the web, and returns scores you can defend.</p>
    </div>
    """)

    llm_ok, llm_name = llm_label()
    web_on = bool(settings.tavily_api_key or settings.serper_api_key)
    cols = st.columns(4, gap="large")
    tiles = [
        ui.kpi("Vendors indexed", count(stats, "vendors"), "Semantic vendor memory"),
        ui.kpi("Documents indexed", count(stats, "documents"), "Bids · contracts · invoices"),
        ui.kpi("LLM engine", "Online" if llm_ok else "Offline", llm_name,
               ui.COLORS["green"] if llm_ok else ui.COLORS["red"]),
        ui.kpi("Web research", "Enabled" if web_on else "Disabled", "Serper + Tavily",
               ui.COLORS["green"] if web_on else ui.COLORS["amber"]),
    ]
    for col, tile in zip(cols, tiles):
        with col:
            ui.render(tile)

    ui.render(ui.section("How the agent thinks"))
    ui.render(ui.pipeline())

    ui.render(ui.section("Capabilities"))
    features = [
        ("01", "Agent Analysis", "Retrieve, grade, search and generate — streamed live.", PAGES[1]),
        ("02", "Vendor Grading", "Price, quality, reliability and risk, each with its reasoning.", PAGES[2]),
        ("03", "Company Intelligence", "Executive brief, SWOT, risks and market position.", PAGES[3]),
        ("04", "Document OCR", "Native and scanned PDFs or photos into structured fields.", PAGES[4]),
    ]
    cols = st.columns(4, gap="large")
    for col, (number, title, body, target) in zip(cols, features):
        with col:
            ui.render(ui.feature_card(number, title, body))
            st.button("Open  →", key=f"go_{title}", on_click=go_to, args=(target,), type="tertiary")


# ============== Agentic Analysis ==============

NODE_NOTES = {
    "retrieve": lambda u: u.get("reasoning_steps", [""])[-1] if u.get("reasoning_steps") else "Knowledge base searched",
    "grade": lambda u: u.get("reasoning_steps", [""])[-1] if u.get("reasoning_steps") else "Relevance graded",
    "web_search": lambda u: f"{len(u.get('web_results', []) or [])} web sources collected",
    "generate": lambda u: "Scores, reasoning and bid variables ready",
}


async def _stream_into(query: str, criteria: list[str], pipe_slot, log_slot) -> dict:
    from src.graphs.order_intelligence import stream_analysis

    states = {"retrieve": "active"}
    notes: dict = {}
    log: list[tuple[str, str]] = [("start", f'Query: "{query}"')]
    ui.render(ui.pipeline(states, notes), pipe_slot)
    ui.render(ui.reasoning_log(log), log_slot)
    started = time.perf_counter()

    result: dict = {}
    async for kind, node, payload in stream_analysis(query, criteria):
        if kind == "done":
            result = payload
            break
        states[node] = "done"
        notes[node] = NODE_NOTES.get(node, lambda u: "")(payload)
        for step in payload.get("reasoning_steps", []) or []:
            log.append((node, step))
        # Mark the next step as running. After GRADE the agent chooses its own path.
        if node == "retrieve":
            states["grade"] = "active"
        elif node == "grade":
            searching = payload.get("grade_decision") == "needs_search" or settings.always_web_search
            log.append(("route", "Local data insufficient → web research" if searching
                        else "Local data sufficient → skip web, generate"))
            if searching:
                states["web_search"] = "active"
            else:
                states["web_search"] = "skipped"
                notes["web_search"] = "Not needed: local knowledge was sufficient"
                states["generate"] = "active"
        elif node == "web_search":
            states["generate"] = "active"
        ui.render(ui.pipeline(states, notes), pipe_slot)
        ui.render(ui.reasoning_log(log[-14:]), log_slot)

    log.append(("done", f"Completed in {time.perf_counter() - started:.1f}s"))
    ui.render(ui.reasoning_log(log[-14:]), log_slot)
    st.session_state.analysis_trace = (states, notes, log[-14:])
    return result


def render_analysis_result(result: dict):
    analysis = result.get("analysis") or {}
    sources = result.get("sources", {})

    if result.get("error"):
        st.error(result["error"])

    left, right = st.columns([1.05, 1.95], gap="large")
    with left:
        ui.render(ui.score_summary(
            analysis.get("overall_score", 0),
            analysis.get("recommendation", "REVIEW"),
            analysis.get("confidence"),
            "Overall assessment",
        ))
        st.write("")
        c1, c2, c3 = st.columns(3)
        with c1:
            ui.render(ui.kpi("Vendors", sources.get("vendors", 0)))
        with c2:
            ui.render(ui.kpi("Docs", sources.get("documents", 0)))
        with c3:
            ui.render(ui.kpi("Web", sources.get("web_results", 0)))
        findings = analysis.get("key_findings") or []
        if findings:
            ui.render(ui.section("Key findings"))
            ui.render('<div class="card">' + "".join(
                f'<p style="margin:8px 0;color:var(--ink)"><span style="color:var(--accent)">—</span>&nbsp; {ui.esc(f)}</p>' for f in findings) + "</div>")
    with right:
        ui.render(ui.section("Score breakdown — every number is explained"))
        if analysis.get("breakdown"):
            ui.render(ui.criteria_breakdown(analysis["breakdown"]))
        elif result.get("final_answer"):
            st.markdown(result["final_answer"])

    bid_vars = result.get("bid_variables") or {}
    if any((v or {}).get("value") for v in bid_vars.values() if isinstance(v, dict)):
        ui.render(ui.section("Extracted bid variables"))
        ui.render(ui.extracted_fields(bid_vars))

    st.write("")
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.expander("Raw analysis JSON"):
            st.json(result)
    with c2:
        st.download_button(
            "Download report (JSON)",
            data=json.dumps(result, indent=2, default=str),
            file_name=f"analysis_{time.strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )


def page_analysis():
    ui.render(ui.page_header(
        "Feature 01 · LangGraph agent",
        "Agent Analysis",
        "Watch the agent retrieve, grade, research and score, one node at a time.",
    ))

    examples = [
        "Compare pricing from Mouser vs DigiKey for electronic components",
        "What is the total price and warranty in the desktop computer bid?",
        "Which of our vendors is the lowest-risk supplier for semiconductors?",
    ]
    ex_cols = st.columns(len(examples))
    for col, ex in zip(ex_cols, examples):
        with col:
            if st.button(ex, key=f"ex_{hash(ex)}", use_container_width=True):
                st.session_state.analysis_query = ex

    query = st.text_area(
        "Your procurement question",
        key="analysis_query",
        placeholder="e.g. Evaluate Aidco's desktop computer pricing against the market",
        height=90,
    )
    c1, c2 = st.columns([3, 1])
    with c1:
        criteria = st.pills(
            "Criteria",
            ["price", "quality", "reliability", "risk", "delivery", "support"],
            default=["price", "quality", "reliability", "risk"],
            selection_mode="multi",
        )
    with c2:
        st.write("")
        run = st.button("Run agent  →", type="primary", use_container_width=True)

    ui.render(ui.section("Live pipeline"))
    pipe_slot = st.empty()
    log_slot = st.empty()

    if run:
        if not query.strip():
            st.warning("Enter a question first.")
            return
        try:
            result = run_async(_stream_into(query.strip(), list(criteria or []), pipe_slot, log_slot))
            st.session_state.analysis_result = result
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            return
    else:
        states, notes, log = st.session_state.get("analysis_trace", ({}, {}, []))
        ui.render(ui.pipeline(states, notes), pipe_slot)
        ui.render(ui.reasoning_log(log), log_slot)

    if st.session_state.get("analysis_result"):
        ui.render(ui.section("Result"))
        render_analysis_result(st.session_state.analysis_result)


# ============== Vendor Grading ==============

def page_grading():
    ui.render(ui.page_header(
        "Feature 02 · Explainable AI",
        "Vendor Grading",
        "Weighted multi-criteria scoring. Every score comes with the reasoning an auditor needs.",
    ))
    tab1, tab2 = st.tabs(["Grade a vendor", "Compare vendors"])

    with tab1:
        c1, c2 = st.columns([3, 1])
        with c1:
            vendor_name = st.text_input("Vendor name", placeholder="e.g. Digital Systems Inc")
        with c2:
            st.write("")
            include_web = st.toggle("Live web evidence", value=True)
        criteria = st.pills("Criteria", ["price", "quality", "reliability", "risk"],
                            default=["price", "quality", "reliability", "risk"],
                            selection_mode="multi", key="grade_criteria")

        if st.button("Grade vendor  →", type="primary"):
            if not vendor_name.strip():
                st.warning("Enter a vendor name.")
            else:
                with st.status(f"Grading {vendor_name}…", expanded=True) as status:
                    try:
                        from src.processors.vendor_grader import VendorGrader
                        from src.processors.report_generator import ReportGenerator

                        web_research = None
                        if include_web and settings.tavily_api_key:
                            st.write("Collecting web evidence…")
                            from src.tools.tavily_search import TavilySearchTool
                            try:
                                research = run_async(TavilySearchTool().search_vendor_info(vendor_name))
                                web_research = research.get("results", {})
                            except Exception as e:
                                st.write(f"Web evidence unavailable: {e}")
                        st.write("Scoring with the LLM…")
                        analysis = run_async(VendorGrader().grade(
                            vendor_name, {"name": vendor_name}, list(criteria or []), web_research))
                        st.write("Writing report…")
                        report = run_async(ReportGenerator().vendor_report(analysis))
                        st.session_state.grade_result = (analysis, report)
                        status.update(label="Grading complete", state="complete", expanded=False)
                    except Exception as e:
                        status.update(label="Grading failed", state="error")
                        st.error(str(e))

        if st.session_state.get("grade_result"):
            analysis, report = st.session_state.grade_result
            left, right = st.columns([1.05, 1.95], gap="large")
            with left:
                ui.render(ui.score_summary(analysis.overall_score, analysis.recommendation,
                                           analysis.confidence, analysis.vendor_name))
                ui.render(ui.section("Weights"))
                ui.render('<div class="card">' + "".join(
                    f'<div class="side-stat"><span style="text-transform:capitalize">{ui.esc(k)}</span>'
                    f'<b>{v:.0%}</b></div>' for k, v in settings.scoring_weights.items()) + "</div>")
            with right:
                ui.render(ui.section("Score breakdown"))
                ui.render(ui.criteria_breakdown(analysis.breakdown))
            with st.expander("Full audit report (Markdown)"):
                st.markdown(report)
            st.download_button("Download report", report, file_name=f"{analysis.vendor_name}_grade.md")

    with tab2:
        vendors_input = st.text_area("Vendors to compare (one per line)",
                                     placeholder="Aidco\nShirazi Traders\nDigital Systems Inc", height=110)
        if st.button("Compare  →", type="primary"):
            vendors = [v.strip() for v in vendors_input.splitlines() if v.strip()]
            if len(vendors) < 2:
                st.warning("Enter at least two vendors.")
            else:
                with st.spinner("Scoring every vendor on the same criteria…"):
                    try:
                        from src.processors.vendor_grader import VendorGrader
                        comparison = run_async(VendorGrader().compare([(v, {"name": v}) for v in vendors]))
                        st.session_state.compare_result = comparison
                    except Exception as e:
                        st.error(f"Comparison failed: {e}")

        comparison = st.session_state.get("compare_result")
        if comparison:
            ui.render(ui.section("Leaderboard"))
            for rank, a in enumerate(comparison.get("analyses", []), 1):
                score = a.get("overall_score", 0)
                color = ui.score_color(score)
                medal = f"{rank:02d}"
                ui.render(f"""
                <div class="card" style="display:flex;align-items:center;gap:18px;margin-bottom:10px;padding:14px 20px">
                <div style="font-family:var(--serif);font-size:1.8rem;width:44px;color:{'var(--accent)' if rank == 1 else 'var(--faint)'}">{medal}</div>
                <div style="flex:1"><b>{ui.esc(a.get('vendor_name', ''))}</b>
                <div class="bar"><span style="width:{score}%;background:{color}"></span></div></div>
                <div style="font-variant-numeric:tabular-nums;font-weight:600;font-size:1.15rem;color:{color};width:56px;text-align:right">{score}</div>
                <div style="width:150px;text-align:right">{ui.recommendation_pill(a.get('recommendation', ''))}</div>
                </div>
                """)


# ============== Company Intelligence ==============

def page_company():
    ui.render(ui.page_header(
        "Feature 03 · Due diligence",
        "Company Intelligence",
        "~20 targeted searches synthesized into an executive brief, SWOT and risk profile.",
    ))
    c1, c2 = st.columns([3, 1])
    with c1:
        company = st.text_input("Company", placeholder="e.g. Stripe")
    with c2:
        st.write("")
        run = st.button("Generate report  →", type="primary", use_container_width=True)

    if run:
        if not company.strip():
            st.warning("Enter a company name.")
        else:
            with st.status(f"Researching {company}…", expanded=True) as status:
                st.write("Phase 1 — running targeted web searches (overview, funding, competitors, reviews, news)…")
                st.write("Phase 2 — AI synthesis into a strategic report…")
                try:
                    from src.tools.company_researcher import CompanyResearcher
                    researcher = CompanyResearcher()
                    profile = run_async(researcher.research(company.strip()))
                    st.session_state.company_result = (
                        profile, researcher.generate_markdown_report(profile))
                    status.update(label=f"Report ready · {profile.search_queries_used} queries",
                                  state="complete", expanded=False)
                except Exception as e:
                    status.update(label="Research failed", state="error")
                    st.error(str(e))

    if not st.session_state.get("company_result"):
        return
    p, md = st.session_state.company_result

    facts = [("Industry", p.industry), ("Headquarters", p.hq_location), ("Founded", p.founded),
             ("Employees", p.employees)]
    ui.render(f"""
    <div class="card" style="margin-top:8px">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap">
    <div><div style="font-family:var(--serif);font-size:2.6rem;line-height:1">{ui.esc(p.name)}</div>
    <div style="color:var(--muted);margin-top:4px">{ui.esc(p.website)}</div></div>
    <div>{ui.pill(f'{p.search_queries_used} queries · {p.sources_scraped} sources', 'violet')}</div>
    </div>
    <div class="fields" style="margin-top:16px">{''.join(
        f'<div class="field"><div class="k">{k}</div><div class="v" style="margin-bottom:0">{ui.esc(v or "—")}</div></div>'
        for k, v in facts)}</div>
    </div>
    """)

    if p.strategic_report:
        ui.render(ui.section("Executive summary"))
        ui.render(ui.text_card("Strategic overview", p.strategic_report, "violet"))

    c1, c2 = st.columns(2)
    with c1:
        if p.business_model:
            ui.render(ui.section("Business model"))
            ui.render(ui.text_card("How they make money", p.business_model, "cyan"))
    with c2:
        if p.market_position:
            ui.render(ui.section("Market position"))
            ui.render(ui.text_card("Where they stand", p.market_position + (
                f"\n\nGrowth: {p.growth_trajectory}" if p.growth_trajectory else ""), "cyan"))

    funding = {k: v for k, v in (p.funding or {}).items() if v and not isinstance(v, list)}
    if funding:
        ui.render(ui.section("Financials"))
        cols = st.columns(min(4, len(funding)))
        for col, (k, v) in zip(cols * 2, funding.items()):
            with col:
                ui.render(ui.kpi(k.replace("_", " "), v))

    if p.swot_analysis:
        ui.render(ui.section("SWOT analysis"))
        ui.render(ui.swot_grid(p.swot_analysis))

    c1, c2 = st.columns(2)
    with c1:
        if p.key_risks:
            ui.render(ui.section("Key risks"))
            ui.render('<div class="card">' + "".join(
                f'<p style="margin:7px 0;color:var(--ink)"><span style="color:var(--red)">●</span> {ui.esc(r)}</p>'
                for r in p.key_risks[:6]) + "</div>")
    with c2:
        if p.opportunities:
            ui.render(ui.section("Opportunities"))
            ui.render('<div class="card">' + "".join(
                f'<p style="margin:7px 0;color:var(--ink)"><span style="color:var(--green)">●</span> {ui.esc(o)}</p>'
                for o in p.opportunities[:6]) + "</div>")

    if p.competitors:
        ui.render(ui.section("Competitive landscape"))
        ui.render(ui.chips(p.competitors[:12]))
    if p.investment_thesis:
        ui.render(ui.section("Investment thesis"))
        ui.render(ui.text_card("Thesis", p.investment_thesis, "green"))
    if p.data_sources:
        with st.expander(f"Sources ({len(p.data_sources)})"):
            ui.render(ui.result_list(p.data_sources, limit=25, snippet_len=180))
    st.download_button("Download full report (Markdown)", md, file_name=f"{p.name}_intelligence.md")


# ============== Document Intelligence ==============

def page_documents():
    ui.render(ui.page_header(
        "Feature 04 · OCR + extraction",
        "Document Intelligence",
        "Native PDFs are read directly; scanned PDFs and photos fall back to Tesseract OCR.",
    ))
    uploaded = st.file_uploader("Drop a bid, contract or invoice",
                                type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"])
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        doc_type = st.selectbox("Document type", ["auto", "bid", "contract", "invoice"])
    with c2:
        st.write("")
        save = st.toggle("Add to knowledge base", value=True)
    with c3:
        st.write("")
        run = st.button("Extract  →", type="primary", use_container_width=True, disabled=uploaded is None)

    if run and uploaded:
        tmp_path = None
        with st.status("Processing document…", expanded=True) as status:
            try:
                from src.processors.document_processor import DocumentProcessor

                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded.name).suffix) as tmp:
                    tmp.write(uploaded.getvalue())
                    tmp_path = tmp.name
                st.write("Reading text layer (OCR fallback for scanned pages)…")
                result = run_async(DocumentProcessor().process(tmp_path, doc_type))
                doc = result.document
                if save and doc.extracted_text:
                    st.write("Embedding into ChromaDB…")
                    from src.storage.chroma_store import get_vector_store
                    run_async(get_vector_store().add_documents(
                        texts=[doc.extracted_text],
                        metadatas=[{"type": doc.type, "file_name": uploaded.name,
                                    "extracted_fields": json.dumps(doc.extracted_fields, default=str)}],
                        ids=[doc.id],
                        collection="documents",
                    ))
                    get_stats.clear()
                st.session_state.doc_result = (uploaded.name, result)
                status.update(label="Extraction complete", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Processing failed", state="error")
                st.error(str(e))
            finally:
                if tmp_path:
                    Path(tmp_path).unlink(missing_ok=True)

    if st.session_state.get("doc_result"):
        name, result = st.session_state.doc_result
        doc = result.document
        cols = st.columns(4)
        tiles = [
            ui.kpi("File", name[:22]),
            ui.kpi("Detected type", str(doc.type).upper()),
            ui.kpi("Confidence", f"{doc.confidence:.0%}", color=ui.score_color(doc.confidence * 100)),
            ui.kpi("Validation", str(doc.validation_status).title()),
        ]
        for col, tile in zip(cols, tiles):
            with col:
                ui.render(tile)
        ui.render(ui.section("Extracted fields"))
        ui.render(ui.extracted_fields(doc.extracted_fields or {}))
        for w in result.warnings:
            st.warning(w)
        for e in result.errors:
            st.error(e)
        with st.expander(f"Extracted text ({len(doc.extracted_text or ''):,} characters)"):
            st.code((doc.extracted_text or "")[:4000], language=None)


# ============== Research ==============

def page_research():
    ui.render(ui.page_header(
        "Feature 05 · Live web intelligence",
        "Market & Vendor Research",
        "Real-time research with cited sources, straight from the web.",
    ))
    if not settings.tavily_api_key:
        st.info("Set TAVILY_API_KEY in .env to enable live research.")
    tab1, tab2, tab3 = st.tabs(["Vendor research", "Market trends", "Risk scan"])

    with tab1:
        vendor = st.text_input("Vendor", placeholder="e.g. Texas Instruments", key="rv")
        if st.button("Research vendor  →", type="primary", key="rv_btn") and vendor.strip():
            with st.spinner(f"Researching {vendor}…"):
                try:
                    from src.tools.tavily_search import TavilySearchTool
                    info = run_async(TavilySearchTool().search_vendor_info(vendor.strip()))
                    for aspect, results in info.get("results", {}).items():
                        ui.render(ui.section(aspect))
                        ui.render(ui.result_list(results, limit=3))
                except Exception as e:
                    st.error(f"Research failed: {e}")

    with tab2:
        category = st.text_input("Market category", placeholder="e.g. industrial automation equipment", key="rm")
        if st.button("Research market  →", type="primary", key="rm_btn") and category.strip():
            with st.spinner(f"Scanning the {category} market…"):
                try:
                    from src.tools.tavily_search import TavilySearchTool
                    trends = run_async(TavilySearchTool().search_market_trends(category.strip()))
                    ui.render(ui.section("Market signals"))
                    ui.render(ui.result_list(trends.get("results", []), limit=6))
                except Exception as e:
                    st.error(f"Research failed: {e}")

    with tab3:
        vendor = st.text_input("Vendor", placeholder="e.g. Acme Corp", key="rr")
        if st.button("Scan for risks  →", type="primary", key="rr_btn") and vendor.strip():
            with st.spinner(f"Scanning {vendor} for litigation, recalls and financial distress…"):
                try:
                    from src.tools.tavily_search import TavilySearchTool
                    risks = run_async(TavilySearchTool().search_vendor_risks(vendor.strip()))
                    level = str(risks.get("risk_level", "unknown")).lower()
                    color = {"low": "green", "medium": "amber", "high": "red"}.get(level, "violet")
                    c1, c2 = st.columns(2)
                    with c1:
                        ui.render(ui.kpi("Risk level", level.upper(), color=ui.COLORS[color]))
                    with c2:
                        ui.render(ui.kpi("Risk signals found", risks.get("risk_factors_found", 0)))
                    ui.render(ui.section("Findings"))
                    ui.render(ui.result_list(risks.get("findings", []), limit=5))
                except Exception as e:
                    st.error(f"Risk scan failed: {e}")


# ============== Knowledge Base ==============

def page_knowledge_base():
    ui.render(ui.page_header(
        "Feature 06 · Vector memory",
        "Knowledge Base",
        "Vendors are stored as embeddings, so search matches meaning rather than keywords.",
    ))
    from src.storage.chroma_store import get_vector_store
    store = get_vector_store()

    left, right = st.columns([1.3, 1], gap="large")
    with left:
        ui.render(ui.section("Semantic search"))
        q = st.text_input("Search vendors by meaning", placeholder="e.g. semiconductor chips")
        if q.strip():
            results = run_async(store.similarity_search(q.strip(), k=8, collection="vendors"))
            rows = []
            for r in results:
                meta = r.get("metadata", {})
                score = max(0.0, float(r.get("score", 0))) * 100
                rows.append(f"""
                <div class="crit">
                <div class="top"><span class="nm" style="text-transform:none">{ui.esc(meta.get('name', r.get('id')))}</span>
                <span class="sc" style="color:{ui.score_color(score)}">{score / 100:.2f}</span></div>
                <div class="bar"><span style="width:{score:.0f}%;background:var(--ink)"></span></div>
                <div class="why">{ui.esc(meta.get('industry', ''))} {('· ' + ui.esc(meta.get('products'))) if meta.get('products') else ''}</div>
                </div>
                """)
            ui.render('<div class="card">' + ("".join(rows) or "<p>No vendors yet.</p>") + "</div>")

        ui.render(ui.section("All vendors"))
        vendors = run_async(store.similarity_search("vendor supplier", k=50, collection="vendors"))
        if vendors:
            st.dataframe(
                [{"Name": v["metadata"].get("name", ""), "Industry": v["metadata"].get("industry", ""),
                  "Products": v["metadata"].get("products", ""), "Website": v["metadata"].get("website", ""),
                  "ID": v["id"]} for v in vendors],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("No vendors yet — add one on the right.")

    with right:
        ui.render(ui.section("Add vendor"))
        with st.form("add_vendor", clear_on_submit=True):
            name = st.text_input("Name*")
            description = st.text_area("Description", height=80)
            website = st.text_input("Website")
            industry = st.text_input("Industry")
            products = st.text_input("Products (comma separated)")
            submitted = st.form_submit_button("Add to knowledge base", type="primary", use_container_width=True)
        if submitted:
            if not name.strip():
                st.warning("Name is required.")
            else:
                vendor_id = f"v_{uuid.uuid4().hex[:12]}"
                text = f"{name}. {description}" + (f" Products: {products}" if products else "")
                run_async(store.add_documents(
                    texts=[text],
                    metadatas=[{"vendor_id": vendor_id, "name": name, "website": website,
                                "industry": industry, "products": products}],
                    ids=[vendor_id],
                    collection="vendors",
                ))
                get_stats.clear()
                st.success(f"Added {name}")
                st.rerun()


# ============== System ==============

def page_system():
    ui.render(ui.page_header("Configuration", "System", "Engine health, integrations and scoring configuration."))
    ollama_ok, models = get_llm_status()
    c1, c2 = st.columns(2)
    with c1:
        ui.render(ui.status_row("Ollama (local LLM)", ollama_ok,
                                f"{settings.ollama_host} · {', '.join(models[:4]) or settings.ollama_model}",
                                warn=not ollama_ok and bool(settings.openrouter_api_key)))
        ui.render(ui.status_row("Tavily search", bool(settings.tavily_api_key),
                                "AI-optimized web search", warn=True))
    with c2:
        ui.render(ui.status_row("OpenRouter fallback", bool(settings.openrouter_api_key),
                                settings.openrouter_model, warn=True))
        ui.render(ui.status_row("Serper (Google results)", bool(settings.serper_api_key),
                                "Deep research & company intelligence", warn=True))

    ui.render(ui.section("Agent configuration"))
    config = {
        "Relevance threshold": settings.relevance_threshold,
        "Max web searches": settings.max_web_searches,
        "Always web search": "On" if settings.always_web_search else "Off",
        "API key protection": "On" if settings.api_key else "Off",
    }
    cols = st.columns(4)
    for col, (k, v) in zip(cols, config.items()):
        with col:
            ui.render(ui.kpi(k, v))

    ui.render(ui.section("Scoring weights"))
    cols = st.columns(len(settings.scoring_weights))
    for col, (k, v) in zip(cols, settings.scoring_weights.items()):
        with col:
            ui.render(ui.kpi(k, f"{v:.0%}"))

    ui.render(ui.section("Maintenance"))
    if st.button("Clear query cache"):
        try:
            from src.storage.cache import get_cache
            cleared = run_async(get_cache().invalidate())
            st.success(f"Cleared {cleared} cache entries")
        except Exception as e:
            st.error(f"Failed: {e}")


# ============== Router ==============

{
    PAGES[0]: page_command_center,
    PAGES[1]: page_analysis,
    PAGES[2]: page_grading,
    PAGES[3]: page_company,
    PAGES[4]: page_documents,
    PAGES[5]: page_research,
    PAGES[6]: page_knowledge_base,
    PAGES[7]: page_system,
}[page]()
