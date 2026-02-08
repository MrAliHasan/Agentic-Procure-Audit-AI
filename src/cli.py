"""
Command Line Interface for Sovereign Order Intelligence
"""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🏭 Sovereign Order Intelligence - AI-Powered Supply Chain Management"""
    pass


# ============== Analyze Commands ==============

@cli.command()
@click.argument("query")
@click.option("--criteria", "-c", multiple=True, default=["price", "quality", "reliability", "risk"])
@click.option("--json-output", "-j", is_flag=True, help="Output as JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress logs")
@click.option("--save", "-s", is_flag=True, help="Save results to ./data/reports/")
def analyze(query: str, criteria: tuple, json_output: bool, verbose: bool, save: bool):
    """Analyze a query using the Order Intelligence workflow."""
    from src.graphs.order_intelligence import analyze_query
    import json
    from pathlib import Path
    from datetime import datetime
    
    async def run():
        if verbose:
            console.print(f"[cyan]Query:[/cyan] {query}")
            console.print(f"[cyan]Criteria:[/cyan] {', '.join(criteria)}")
            console.print("[dim]─" * 50 + "[/dim]")
            console.print("[yellow]Step 1:[/yellow] Retrieving from vector store...")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=verbose  # Disable spinner if verbose
        ) as progress:
            task = progress.add_task("Analyzing...", total=None)
            result = await analyze_query(query, list(criteria))
            progress.update(task, completed=True)
        
        if verbose:
            console.print(f"[green]✓[/green] Retrieved {result.get('sources', {}).get('vendors', 0)} vendors")
            console.print(f"[green]✓[/green] Retrieved {result.get('sources', {}).get('documents', 0)} documents")
            console.print(f"[yellow]Step 2:[/yellow] Grading relevance...")
            console.print(f"[green]✓[/green] Web searches performed: {result.get('web_searches_performed', 0)}")
            console.print(f"[green]✓[/green] Web results: {result.get('sources', {}).get('web_results', 0)}")
            console.print(f"[yellow]Step 3:[/yellow] Generating analysis with LLM...")
            console.print("[dim]─" * 50 + "[/dim]")
            
            # Show reasoning chain
            if result.get("reasoning_chain"):
                console.print("\n[bold cyan]Reasoning Chain:[/bold cyan]")
                for step in result.get("reasoning_chain", []):
                    console.print(f"  • {step}")
        
        return result
    
    result = asyncio.run(run())
    
    if json_output:
        console.print_json(data=result)
    else:
        console.print(Panel(Markdown(result.get("final_answer", "No result")), title="Analysis Result"))
        
        # Show extracted bid variables if present
        bid_vars = result.get("bid_variables", {})
        if bid_vars and any(v.get("value") for v in bid_vars.values()):
            console.print("\n[bold cyan]📋 Extracted Bid Variables:[/bold cyan]")
            
            bid_table = Table(show_header=True, header_style="bold magenta")
            bid_table.add_column("Field", style="cyan")
            bid_table.add_column("Value", style="green") 
            bid_table.add_column("Confidence", style="yellow")
            bid_table.add_column("Source", style="dim")
            
            field_labels = {
                "vendor_name": "Vendor",
                "total_price": "Total Price",
                "currency": "Currency",
                "bid_date": "Bid Date",
                "valid_until": "Valid Until",
                "specifications": "Specifications",
                "delivery_terms": "Delivery",
                "warranty": "Warranty",
                "tender_reference": "Reference",
            }
            
            for key, label in field_labels.items():
                field = bid_vars.get(key, {})
                value = field.get("value")
                if value is not None:
                    # Format price with commas
                    if key == "total_price" and isinstance(value, (int, float)):
                        value_str = f"{value:,.0f}"
                    else:
                        value_str = str(value)[:60]
                    
                    conf = field.get("confidence", 0)
                    conf_str = f"{conf:.0%}" if conf else "-"
                    source = field.get("source", "")[:30]
                    
                    bid_table.add_row(label, value_str, conf_str, source)
            
            console.print(bid_table)
        
        # Show sources
        sources = result.get("sources", {})
        console.print(f"\n[dim]Sources: {sources.get('vendors', 0)} vendors, {sources.get('documents', 0)} documents, {sources.get('web_results', 0)} web results[/dim]")
        
        # Show error if any
        if result.get("error"):
            console.print(f"\n[red]Error: {result.get('error')}[/red]")
    
    # Save results if requested
    if save:
        reports_dir = Path("./data/reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c if c.isalnum() else "_" for c in query[:30])
        filename = f"{timestamp}_{safe_query}.json"
        filepath = reports_dir / filename
        
        # Add metadata to saved report
        report = {
            "query": query,
            "criteria": list(criteria),
            "timestamp": datetime.now().isoformat(),
            "result": result
        }
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        console.print(f"\n[green]✓ Report saved:[/green] {filepath}")


@cli.command()
@click.argument("vendor_name")
@click.option("--web/--no-web", default=True, help="Include web research")
@click.option("--criteria", "-c", multiple=True, default=["price", "quality", "reliability", "risk"])
def grade(vendor_name: str, web: bool, criteria: tuple):
    """Grade a vendor on specified criteria."""
    from src.processors.vendor_grader import VendorGrader
    from src.tools.tavily_search import TavilySearchTool
    from src.processors.report_generator import ReportGenerator
    
    async def run():
        grader = VendorGrader()
        
        web_research = None
        if web:
            with console.status(f"Researching {vendor_name} online..."):
                try:
                    search_tool = TavilySearchTool()
                    research = await search_tool.search_vendor_info(vendor_name)
                    web_research = research.get("results", {})
                except Exception as e:
                    console.print(f"[yellow]Web research failed: {e}[/yellow]")
        
        with console.status("Grading vendor..."):
            analysis = await grader.grade(
                vendor_name,
                {"name": vendor_name},
                list(criteria),
                web_research
            )
        
        # Generate report
        reporter = ReportGenerator()
        report = await reporter.vendor_report(analysis)
        
        return analysis, report
    
    analysis, report = asyncio.run(run())
    
    console.print(Markdown(report))


# ============== Vendor Commands ==============

@cli.group()
def vendors():
    """Manage vendors in the knowledge base."""
    pass


@vendors.command("list")
@click.option("--limit", "-l", default=20, help="Maximum vendors to show")
def list_vendors(limit: int):
    """List all vendors."""
    from src.storage.chroma_store import get_vector_store
    
    async def run():
        store = get_vector_store()
        results = await store.similarity_search("vendor supplier", k=limit, collection="vendors")
        return results
    
    results = asyncio.run(run())
    
    if not results:
        console.print("[yellow]No vendors found. Add some with 'soi vendors add'[/yellow]")
        return
    
    table = Table(title="Vendors")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Score", justify="right")
    
    for vendor in results:
        meta = vendor.get("metadata", {})
        table.add_row(
            vendor.get("id", "")[:20],
            meta.get("name", "Unknown"),
            f"{vendor.get('score', 0):.2f}"
        )
    
    console.print(table)


@vendors.command("add")
@click.argument("name")
@click.option("--description", "-d", default="", help="Vendor description")
@click.option("--website", "-w", default="", help="Vendor website")
@click.option("--industry", "-i", default="", help="Industry category")
@click.option("--products", "-p", multiple=True, help="Products/services offered")
def add_vendor(name: str, description: str, website: str, industry: str, products: tuple):
    """Add a vendor to the knowledge base."""
    from src.storage.chroma_store import get_vector_store
    import uuid
    
    async def run():
        store = get_vector_store()
        vendor_id = f"v_{uuid.uuid4().hex[:12]}"
        
        text = f"{name}. {description}"
        if products:
            text += f" Products: {', '.join(products)}"
        
        metadata = {
            "vendor_id": vendor_id,
            "name": name,
            "website": website,
            "industry": industry,
            "products": ", ".join(products)
        }
        
        await store.add_documents(
            texts=[text],
            metadatas=[metadata],
            ids=[vendor_id],
            collection="vendors"
        )
        
        return vendor_id
    
    vendor_id = asyncio.run(run())
    console.print(f"[green]✓ Added vendor: {name} (ID: {vendor_id})[/green]")


@vendors.command("search")
@click.argument("query")
@click.option("--limit", "-l", default=5, help="Maximum results")
def search_vendors(query: str, limit: int):
    """Search for vendors."""
    from src.storage.chroma_store import get_vector_store
    
    async def run():
        store = get_vector_store()
        return await store.similarity_search(query, k=limit, collection="vendors")
    
    results = asyncio.run(run())
    
    if not results:
        console.print("[yellow]No vendors found matching query[/yellow]")
        return
    
    for vendor in results:
        meta = vendor.get("metadata", {})
        console.print(Panel(
            f"[bold]{meta.get('name', 'Unknown')}[/bold]\n"
            f"ID: {vendor.get('id', '')}\n"
            f"Score: {vendor.get('score', 0):.2f}\n"
            f"Website: {meta.get('website', 'N/A')}"
        ))


# ============== Document Commands ==============

@cli.group()
def docs():
    """Process and manage documents."""
    pass


@docs.command("process")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--type", "-t", "doc_type", default="auto", type=click.Choice(["auto", "invoice", "contract", "bid"]))
def process_doc(file_path: str, doc_type: str):
    """Process a document (invoice, contract, bid)."""
    from src.processors.document_processor import DocumentProcessor
    import json
    
    async def run():
        processor = DocumentProcessor()
        with console.status(f"Processing {file_path}..."):
            result = await processor.process(file_path, doc_type)
        return result
    
    result = asyncio.run(run())
    
    doc = result.document
    
    console.print(Panel(
        f"[bold]Document Processed[/bold]\n\n"
        f"Type: {doc.type}\n"
        f"Status: {doc.validation_status}\n"
        f"Confidence: {doc.confidence:.0%}\n"
        f"Processing Time: {result.processing_time_ms}ms\n"
        f"Extracted Fields: {len(doc.extracted_fields)}",
        title=doc.file_name or "Document"
    ))
    
    if doc.extracted_fields:
        console.print("\n[bold]Extracted Fields:[/bold]")
        console.print_json(data=doc.extracted_fields)
    
    if result.errors:
        console.print(f"\n[red]Errors: {', '.join(result.errors)}[/red]")
    
    if result.warnings:
        console.print(f"\n[yellow]Warnings: {', '.join(result.warnings)}[/yellow]")


@docs.command("add")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--type", "-t", "doc_type", default="general", 
              type=click.Choice(["general", "contract", "invoice", "bid", "report"]),
              help="Document type for categorization")
@click.option("--description", "-d", default="", help="Optional description")
def add_doc(file_path: str, doc_type: str, description: str):
    """Add a document to the knowledge base (vector store)."""
    from src.storage.chroma_store import VectorStore
    from src.tools.ocr import DocumentOCR
    from pathlib import Path
    import hashlib
    
    async def run():
        file = Path(file_path)
        
        # Extract text from document
        ocr = DocumentOCR()
        try:
            with console.status(f"Extracting text from {file.name}..."):
                text = await ocr.extract_text(str(file))
        except Exception as e:
            return {"success": False, "error": f"OCR failed: {str(e)}"}
        
        if not text or not text.strip():
            return {"success": False, "error": "No text extracted from document"}
        
        # Generate document ID
        doc_id = hashlib.md5(f"{file.name}_{text[:100]}".encode()).hexdigest()[:16]
        
        # Store in ChromaDB using VectorStore
        store = VectorStore()
        with console.status("Adding to vector store..."):
            # Add to documents collection with proper API
            await store.add_documents(
                texts=[text],
                metadatas=[{
                    "id": doc_id,
                    "file_name": file.name,
                    "file_path": str(file.absolute()),
                    "type": doc_type,
                    "description": description,
                }],
                ids=[doc_id],
                collection="documents"
            )
        
        return {
            "success": True,
            "doc_id": doc_id,
            "file_name": file.name,
            "text_length": len(text),
            "type": doc_type
        }
    
    result = asyncio.run(run())
    
    if result.get("success"):
        console.print(Panel(
            f"[bold green]✓ Document Added to Knowledge Base[/bold green]\n\n"
            f"📄 File: {result['file_name']}\n"
            f"🔑 ID: {result['doc_id']}\n"
            f"📝 Type: {result['type']}\n"
            f"📊 Text extracted: {result['text_length']:,} characters",
            title="Document Ingested"
        ))
    else:
        console.print(f"[red]Error: {result.get('error')}[/red]")


@docs.command("list")
def list_docs():
    """List all documents in the knowledge base."""
    from src.storage.chroma_store import VectorStore
    
    async def run():
        store = VectorStore()
        # Get all documents from documents collection
        results = await store.similarity_search(
            query="document contract bid report invoice",  # Broad query to get all
            k=100,
            collection="documents"
        )
        return results
    
    docs = asyncio.run(run())
    
    if not docs:
        console.print("[yellow]No documents in knowledge base.[/yellow]")
        return
    
    table = Table(title="Documents in Knowledge Base")
    table.add_column("ID", style="cyan")
    table.add_column("File Name", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("Score", style="dim")
    
    for doc in docs:
        meta = doc.get("metadata", {})
        table.add_row(
            meta.get("id", "")[:12],
            meta.get("file_name", "Unknown"),
            meta.get("type", "general"),
            f"{doc.get('score', 0):.2f}"
        )
    
    console.print(table)

@cli.group()
def research():
    """Web research and market intelligence."""
    pass


@research.command("vendor")
@click.argument("vendor_name")
def research_vendor(vendor_name: str):
    """Research a vendor online."""
    from src.tools.tavily_search import TavilySearchTool
    
    async def run():
        search_tool = TavilySearchTool()
        
        with console.status(f"Researching {vendor_name}..."):
            info = await search_tool.search_vendor_info(vendor_name)
        
        with console.status("Checking for risks..."):
            risks = await search_tool.search_vendor_risks(vendor_name)
        
        return info, risks
    
    info, risks = asyncio.run(run())
    
    console.print(Panel(f"[bold]Research: {vendor_name}[/bold]"))
    
    # Show findings
    for aspect, results in info.get("results", {}).items():
        console.print(f"\n[cyan]{aspect.upper()}[/cyan]")
        for r in results[:2]:
            console.print(f"  • {r.get('title', 'N/A')}")
            console.print(f"    [dim]{r.get('content', '')[:200]}...[/dim]")
    
    # Show risks
    risk_level = risks.get("risk_level", "unknown")
    risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(risk_level, "white")
    console.print(f"\n[{risk_color}]Risk Level: {risk_level.upper()}[/{risk_color}]")


@research.command("market")
@click.argument("category")
def research_market(category: str):
    """Research market trends for a category."""
    from src.tools.tavily_search import TavilySearchTool
    
    async def run():
        search_tool = TavilySearchTool()
        with console.status(f"Researching {category} market..."):
            return await search_tool.search_market_trends(category)
    
    results = asyncio.run(run())
    
    console.print(Panel(f"[bold]Market Research: {category}[/bold]"))
    
    for result in results.get("results", [])[:5]:
        console.print(f"\n• [bold]{result.get('title', 'N/A')}[/bold]")
        console.print(f"  {result.get('content', '')[:300]}...")
        console.print(f"  [dim]{result.get('url', '')}[/dim]")


@research.command("company")
@click.argument("company_name")
@click.option("--output", "-o", type=click.Path(), help="Save JSON to file")
@click.option("--markdown", "-m", type=click.Path(), help="Save markdown report")
def research_company_cmd(company_name: str, output: str, markdown: str):
    """
    🏢 Comprehensive company intelligence report.
    
    Generates strategic analysis: SWOT, market position, business model,
    investment thesis, key risks, opportunities, and contact strategy.
    
    Examples:
    
        soi research company "Stripe"
        
        soi research company "Tesla" -o tesla.json -m tesla_report.md
    """
    from src.tools.company_researcher import CompanyResearcher
    import json
    
    async def run():
        researcher = CompanyResearcher()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"🔍 Phase 1: Gathering data on {company_name}...", total=None)
            # Research happens here
            profile = await researcher.research(company_name)
            progress.update(task, description="✅ Research complete", completed=True)
        return profile, researcher.to_dict(profile), researcher.generate_markdown_report(profile)
    
    profile, profile_dict, md_report = asyncio.run(run())
    
    # ============ Display Comprehensive Report ============
    console.print(f"\n[bold cyan]══════════════════════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[bold cyan]    🏢 {profile.name} - Strategic Intelligence Report[/bold cyan]")
    console.print(f"[bold cyan]══════════════════════════════════════════════════════════════════[/bold cyan]")
    console.print(f"[dim]Research Date: {profile.research_date} | Queries: {profile.search_queries_used}[/dim]\n")
    
    # Executive Summary
    if profile.strategic_report:
        console.print(Panel(
            profile.strategic_report,
            title="[bold]📋 Executive Summary[/bold]",
            border_style="blue",
            padding=(1, 2)
        ))
    
    # Company Overview
    console.print(f"\n[bold magenta]📊 Company Overview[/bold magenta]")
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Field", style="dim", width=15)
    info_table.add_column("Value", style="white")
    
    if profile.website:
        info_table.add_row("Website", profile.website)
    if profile.industry:
        info_table.add_row("Industry", profile.industry)
    if profile.hq_location:
        info_table.add_row("Headquarters", profile.hq_location)
    if profile.founded:
        info_table.add_row("Founded", profile.founded)
    if profile.employees:
        info_table.add_row("Employees", profile.employees)
    console.print(info_table)
    
    if profile.description:
        console.print(f"\n[italic]{profile.description}[/italic]")
    
    # Business Model & Market Position
    if profile.business_model or profile.market_position:
        console.print(f"\n[bold green]💼 Business Model[/bold green]")
        if profile.business_model:
            console.print(f"  {profile.business_model}")
        
        console.print(f"\n[bold green]📈 Market Position[/bold green]")
        if profile.market_position:
            console.print(f"  {profile.market_position}")
        if profile.growth_trajectory:
            console.print(f"  [dim]Growth: {profile.growth_trajectory}[/dim]")
    
    # Financials
    if profile.funding:
        console.print(f"\n[bold yellow]💰 Financial Summary[/bold yellow]")
        for k, v in profile.funding.items():
            label = k.replace("_", " ").title()
            console.print(f"  • {label}: [bold]{v}[/bold]")
    
    # SWOT Analysis
    if profile.swot_analysis:
        console.print(f"\n[bold blue]🎯 SWOT Analysis[/bold blue]")
        swot_table = Table(show_header=True, header_style="bold", box=None)
        swot_table.add_column("Strengths ✅", style="green", width=35)
        swot_table.add_column("Weaknesses ⚠️", style="yellow", width=35)
        
        strengths = profile.swot_analysis.get("strengths", [])[:4]
        weaknesses = profile.swot_analysis.get("weaknesses", [])[:4]
        for i in range(max(len(strengths), len(weaknesses))):
            s = strengths[i][:35] if i < len(strengths) else ""
            w = weaknesses[i][:35] if i < len(weaknesses) else ""
            swot_table.add_row(s, w)
        console.print(swot_table)
        
        swot_table2 = Table(show_header=True, header_style="bold", box=None)
        swot_table2.add_column("Opportunities 🚀", style="cyan", width=35)
        swot_table2.add_column("Threats ⛔", style="red", width=35)
        
        opportunities = profile.swot_analysis.get("opportunities", [])[:4]
        threats = profile.swot_analysis.get("threats", [])[:4]
        for i in range(max(len(opportunities), len(threats))):
            o = opportunities[i][:35] if i < len(opportunities) else ""
            t = threats[i][:35] if i < len(threats) else ""
            swot_table2.add_row(o, t)
        console.print(swot_table2)
    
    # Key Risks & Opportunities
    if profile.key_risks:
        console.print(f"\n[bold red]🔴 Key Risks[/bold red]")
        for r in profile.key_risks[:5]:
            console.print(f"  • {r[:70]}")
    
    if profile.opportunities:
        console.print(f"\n[bold green]🟢 Opportunities[/bold green]")
        for o in profile.opportunities[:5]:
            console.print(f"  • {o[:70]}")
    
    # Investment Thesis
    if profile.investment_thesis:
        console.print(f"\n[bold cyan]💎 Investment Thesis[/bold cyan]")
        console.print(f"  {profile.investment_thesis}")
    
    # Competitive Landscape
    if profile.competitors:
        console.print(f"\n[bold yellow]⚔️ Competitors[/bold yellow]")
        console.print(f"  {', '.join(profile.competitors)}")
    
    # Key Executives
    if profile.executives:
        console.print(f"\n[bold magenta]👔 Key Executives ({len(profile.executives)})[/bold magenta]")
        exec_table = Table(show_header=True, header_style="bold")
        exec_table.add_column("Name", style="cyan", max_width=25)
        exec_table.add_column("Role", style="yellow", max_width=35)
        exec_table.add_column("LinkedIn", style="blue", max_width=50)
        
        for e in profile.executives[:8]:
            exec_table.add_row(
                e.name[:25],
                e.role[:35],
                e.linkedin_url[:50] if e.linkedin_url else "-"
            )
        console.print(exec_table)
    
    # Contact Strategy
    if profile.contact_strategy:
        console.print(f"\n[bold cyan]📧 Contact Strategy[/bold cyan]")
        console.print(f"  {profile.contact_strategy}")
    
    # Recent News with URLs
    if profile.recent_news:
        console.print(f"\n[bold blue]📰 Recent News & Signals[/bold blue]")
        news_table = Table(show_header=True, header_style="bold", box=None)
        news_table.add_column("#", style="dim", width=3)
        news_table.add_column("Title", style="white", max_width=50)
        news_table.add_column("Source", style="cyan", max_width=20)
        news_table.add_column("Date", style="dim", max_width=15)
        
        for i, n in enumerate(profile.recent_news[:6], 1):
            news_table.add_row(
                str(i),
                n.title[:50],
                n.source[:20],
                n.date or "-"
            )
        console.print(news_table)
        
        # Show URLs separately
        console.print(f"  [dim]URLs:[/dim]")
        for i, n in enumerate(profile.recent_news[:4], 1):
            console.print(f"    [dim]{i}. {n.url[:70]}[/dim]")
    
    # Hiring signals
    if profile.hiring_signals:
        console.print(f"\n[bold green]🎯 Hiring Signals[/bold green]")
        for s in profile.hiring_signals:
            console.print(f"  ✓ {s}")
    
    # === REAL-TIME DATA SOURCES ===
    if profile.data_sources:
        console.print(f"\n[bold cyan]🔗 Data Sources (Real-Time Search Results)[/bold cyan]")
        console.print(f"  [dim]Proof of live web search - not cached/training data[/dim]\n")
        
        sources_table = Table(show_header=True, header_style="bold", box=None)
        sources_table.add_column("#", style="dim", width=3)
        sources_table.add_column("Domain", style="cyan", max_width=25)
        sources_table.add_column("Title", style="white", max_width=35)
        sources_table.add_column("Key Data", style="dim", max_width=45)
        
        for i, src in enumerate(profile.data_sources[:8], 1):
            snippet = src.get('snippet', '')[:45] + '...' if len(src.get('snippet', '')) > 45 else src.get('snippet', '')
            sources_table.add_row(
                str(i),
                src.get('domain', '')[:25],
                src.get('title', '')[:35],
                snippet
            )
        console.print(sources_table)
        
        # Show full URLs
        console.print(f"\n  [dim]Source URLs:[/dim]")
        for i, src in enumerate(profile.data_sources[:5], 1):
            console.print(f"    [dim]{i}. {src.get('url', '')[:80]}[/dim]")
    
    # === RAW SEARCH SNIPPETS ===
    if profile.raw_search_snippets:
        console.print(f"\n[bold yellow]🔍 Raw Search Snippets[/bold yellow]")
        console.print(f"  [dim]Unprocessed data from live Google search:[/dim]\n")
        for snippet in profile.raw_search_snippets[:4]:
            console.print(f"  • [italic]{snippet[:100]}...[/italic]")
    
    # Metadata footer
    console.print(f"\n[dim]{'─' * 70}[/dim]")
    console.print(f"[dim]📊 Queries: {profile.search_queries_used} | Sources: {profile.sources_scraped} | Data: Real-time Serper API[/dim]")
    
    # Save outputs
    if output:
        with open(output, "w") as f:
            json.dump(profile_dict, f, indent=2)
        console.print(f"\n[green]💾 JSON saved to {output}[/green]")
    
    if markdown:
        with open(markdown, "w") as f:
            f.write(md_report)
        console.print(f"[green]📄 Markdown report saved to {markdown}[/green]")


# ============== Server Commands ==============

@cli.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind")
@click.option("--port", "-p", default=8000, help="Port to bind")
@click.option("--reload", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the API server."""
    import uvicorn
    
    console.print(f"[green]Starting Sovereign Order Intelligence API on {host}:{port}[/green]")
    uvicorn.run(
        "src.api.server:app",
        host=host,
        port=port,
        reload=reload
    )


# ============== Status Commands ==============

@cli.command()
def status():
    """Check system status and health."""
    from src.llm.ollama_client import OllamaClient
    from src.storage.chroma_store import get_vector_store
    from src.config import settings
    
    async def run():
        # Check Ollama
        client = OllamaClient()
        ollama_ok = await client.health_check()
        models = await client.list_models() if ollama_ok else []
        await client.close()
        
        # Check vector store
        try:
            store = get_vector_store()
            stats = await store.get_stats()
            vector_ok = True
        except Exception:
            vector_ok = False
            stats = {}
        
        return ollama_ok, models, vector_ok, stats
    
    ollama_ok, models, vector_ok, stats = asyncio.run(run())
    
    table = Table(title="System Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details")
    
    table.add_row(
        "Ollama",
        "[green]✓ OK[/green]" if ollama_ok else "[red]✗ Error[/red]",
        f"Model: {settings.ollama_model}"
    )
    
    table.add_row(
        "Vector Store",
        "[green]✓ OK[/green]" if vector_ok else "[red]✗ Error[/red]",
        str(stats)
    )
    
    table.add_row(
        "Tavily API",
        "[green]✓ Configured[/green]" if settings.tavily_api_key else "[yellow]⚠ Not set[/yellow]",
        "Web search enabled" if settings.tavily_api_key else "Set TAVILY_API_KEY"
    )
    
    console.print(table)
    
    if models:
        console.print(f"\n[dim]Available models: {', '.join(models[:5])}[/dim]")


@cli.command()
@click.option("--port", "-p", default=8501, help="Port to run Streamlit on")
def ui(port: int):
    """🖥️ Launch the Streamlit web interface."""
    import subprocess
    import sys
    
    console.print(f"[cyan]Starting Streamlit UI on port {port}...[/cyan]")
    console.print(f"[green]Open http://localhost:{port} in your browser[/green]")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "src/ui/app.py",
            "--server.port", str(port),
            "--server.headless", "true"
        ], check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]UI stopped[/yellow]")
    except FileNotFoundError:
        console.print("[red]Error: Streamlit not installed. Run: pip install streamlit[/red]")


@cli.command()
@click.option("--host", "-h", default="0.0.0.0", help="Host to bind to")
@click.option("--port", "-p", default=8000, help="Port to run server on")
@click.option("--reload", "-r", is_flag=True, help="Enable auto-reload for development")
def serve(host: str, port: int, reload: bool):
    """🚀 Start the FastAPI server."""
    import subprocess
    import sys
    
    console.print(f"[cyan]Starting FastAPI server on {host}:{port}...[/cyan]")
    console.print(f"[green]API docs: http://localhost:{port}/docs[/green]")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "src.api.server:app",
        "--host", host,
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except FileNotFoundError:
        console.print("[red]Error: Uvicorn not installed. Run: pip install uvicorn[/red]")


# ============== Lead Scraping Commands (NEW) ==============

@cli.group()
def leads():
    """🎯 Lead generation - scrape businesses with contact info."""
    pass


@leads.command("scrape")
@click.argument("query")
@click.option("--max", "-n", "max_results", default=20, help="Maximum leads to find")
@click.option("--output", "-o", type=click.Path(), help="Save to JSON file")
@click.option("--json", "-j", "json_output", is_flag=True, help="Output as JSON")
def scrape_leads_cmd(query: str, max_results: int, output: str, json_output: bool):
    """
    Scrape leads for any query with emails, phones, addresses.
    
    Examples:
    
        soi leads scrape "dentists in Miami"
        
        soi leads scrape "coffee shops Austin" -n 50 -o leads.json
        
        soi leads scrape "plumbers Los Angeles" --json
    """
    from src.tools.lead_scraper import LeadScraper
    import json
    
    async def run():
        scraper = LeadScraper()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"Searching: {query}...", total=None)
            result = await scraper.search_leads(query, max_results=max_results)
            progress.update(task, completed=True)
        
        return result
    
    result = asyncio.run(run())
    
    # Stats
    console.print(f"\n[green]✅ Found {len(result.leads)} leads with contact info[/green]")
    console.print(f"[dim]Search: {result.search_time:.1f}s | Scrape: {result.scrape_time:.1f}s | Total URLs: {result.total_found}[/dim]\n")
    
    if json_output:
        from src.tools.lead_scraper import LeadScraper
        scraper = LeadScraper.__new__(LeadScraper)
        scraper.leads_to_json = lambda r: [
            {"name": l.name, "email": l.email, "phone": l.phone, "address": l.address, "website": l.website}
            for l in r.leads
        ]
        console.print_json(data=scraper.leads_to_json(result))
    else:
        # Pretty table output
        table = Table(show_header=True, header_style="bold magenta", title="🎯 Leads Found")
        table.add_column("#", style="dim", width=3)
        table.add_column("Name", style="cyan", max_width=30)
        table.add_column("Email", style="green", max_width=28)
        table.add_column("Phone", style="yellow", max_width=14)
        table.add_column("URL", style="blue", max_width=35)
        
        for i, lead in enumerate(result.leads, 1):
            table.add_row(
                str(i),
                lead.name[:30] if lead.name else "-",
                lead.email or "-",
                lead.phone or "-",
                lead.website[:35] if lead.website else "-",
            )
        
        console.print(table)
    
    # Save to file
    if output:
        leads_data = [
            {
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "address": lead.address,
                "website": lead.website,
                "snippet": lead.snippet,
            }
            for lead in result.leads
        ]
        
        with open(output, "w") as f:
            json.dump({"query": query, "leads": leads_data}, f, indent=2)
        
        console.print(f"\n[green]💾 Saved to {output}[/green]")
    
    if result.errors:
        console.print(f"\n[yellow]⚠️ Errors: {len(result.errors)}[/yellow]")


@leads.command("linkedin")
@click.argument("query")
@click.option("--max", "-n", "max_results", default=50, help="Maximum profiles to find")
@click.option("--output", "-o", type=click.Path(), help="Save to JSON file")
def linkedin_leads_cmd(query: str, max_results: int, output: str):
    """
    🔗 Scrape LinkedIn profiles for a specific role/industry.
    
    Searches only LinkedIn profiles (site:linkedin.com/in) for targeted lead gen.
    
    Examples:
    
        soi leads linkedin "dentists Miami"
        
        soi leads linkedin "software engineers San Francisco" -n 100
        
        soi leads linkedin "marketing manager NYC" -o leads.json
    """
    from src.tools.lead_scraper import LeadScraper
    from src.config import settings
    import json
    import httpx
    import re
    
    async def search_linkedin(query: str, start: int = 0):
        """Search LinkedIn profiles via Serper."""
        url = "https://google.serper.dev/search"
        
        # Add site filter for LinkedIn profiles + gmail for emails
        linkedin_query = f'site:linkedin.com/in {query} "gmail"'
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json={"q": linkedin_query, "num": 10, "start": start, "gl": "us", "hl": "en"},
                    headers={"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"}
                )
                response.raise_for_status()
                return response.json().get("organic", [])
        except:
            return []
    
    def extract_email(text: str):
        """Extract Gmail from text."""
        email_pattern = r'[\w\.-]+@gmail\.com'
        matches = re.findall(email_pattern, text.lower())
        return matches[0] if matches else ""
    
    async def run():
        all_results = []
        seen_urls = set()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"🔗 Searching LinkedIn: {query}...", total=None)
            
            # Paginate to get requested number of profiles
            # Use different start offsets to get more results
            pages_needed = (max_results + 9) // 10
            
            for page in range(min(pages_needed, 10)):  # Max 10 pages = 100 results per query variant
                results = await search_linkedin(query, page * 10)
                for r in results:
                    url = r.get("link", "")
                    if url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
                
                if len(all_results) >= max_results:
                    break
            
            # If we still need more, try query variations
            if len(all_results) < max_results:
                variations = [
                    f"{query} email",
                    f"{query} contact",
                    f'"{query}"',
                ]
                for variant in variations:
                    if len(all_results) >= max_results:
                        break
                    for page in range(3):  # 3 pages per variant
                        results = await search_linkedin(variant, page * 10)
                        for r in results:
                            url = r.get("link", "")
                            if url not in seen_urls:
                                seen_urls.add(url)
                                all_results.append(r)
                        if len(all_results) >= max_results:
                            break
            
            progress.update(task, completed=True)
        
        return all_results[:max_results]
    
    import asyncio
    results = asyncio.run(run())
    
    # Parse LinkedIn profiles
    leads = []
    for r in results:
        url = r.get("link", "")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        
        # Extract name from title (format: "Name - Title | LinkedIn")
        name = title.split(" - ")[0].strip() if " - " in title else title.split(" | ")[0].strip()
        
        # Extract Gmail from snippet
        email = extract_email(snippet) or extract_email(title)
        
        # Try to extract role/company from title
        role = ""
        company = ""
        if " - " in title:
            parts = title.split(" - ")
            if len(parts) >= 2:
                role_company = parts[1].replace(" | LinkedIn", "").strip()
                
                # Check for "@ Company" pattern (e.g., "Software Engineer @ Google")
                if " @ " in role_company:
                    role, company = role_company.split(" @ ", 1)
                    role = role.strip()
                    company = company.strip()
                # Check for "at Company" pattern
                elif " at " in role_company.lower():
                    idx = role_company.lower().find(" at ")
                    role = role_company[:idx].strip()
                    company = role_company[idx+4:].strip()
                else:
                    role = role_company
        
        leads.append({
            "name": name,
            "email": email,
            "role": role,
            "company": company,
            "linkedin_url": url,
        })
    
    # Stats
    emails_found = len([l for l in leads if l["email"]])
    console.print(f"\n[green]✅ Found {len(leads)} LinkedIn profiles ({emails_found} with Gmail)[/green]\n")
    
    # Pretty table output
    table = Table(show_header=True, header_style="bold magenta", title="🔗 LinkedIn Leads")
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="cyan", max_width=22)
    table.add_column("Email", style="green", max_width=25)
    table.add_column("Role", style="yellow", max_width=22)
    table.add_column("Company", style="white", max_width=15)
    table.add_column("LinkedIn URL", style="blue", max_width=35)
    
    for i, lead in enumerate(leads, 1):
        table.add_row(
            str(i),
            lead["name"][:22] if lead["name"] else "-",
            lead["email"] or "-",
            lead["role"][:22] if lead["role"] else "-",
            lead["company"][:15] if lead["company"] else "-",
            lead["linkedin_url"][:35] if lead["linkedin_url"] else "-",
        )
    
    console.print(table)
    
    # Save to file
    if output:
        with open(output, "w") as f:
            json.dump({"query": query, "total": len(leads), "emails_found": emails_found, "linkedin_leads": leads}, f, indent=2)
        console.print(f"\n[green]💾 Saved to {output}[/green]")


@leads.command("smart")
@click.argument("query")
@click.option("--max", "-n", "max_leads", default=50, help="Maximum leads to find")
@click.option("--queries", "-q", "num_queries", default=5, help="Number of LLM-generated search queries")
@click.option("--output", "-o", type=click.Path(), help="Save to JSON file")
def smart_leads_cmd(query: str, max_leads: int, num_queries: int, output: str):
    """
    🧠 AI-powered lead search using Groq LLM for intelligent queries.
    
    Uses LLM to generate diverse search queries that find more leads
    with email addresses and phone numbers.
    
    Examples:
    
        soi leads smart "dentists in Miami" -n 100
        
        soi leads smart "lawyers Los Angeles" -q 10 -o leads.json
    """
    from src.tools.intelligent_scraper import IntelligentLeadScraper
    import json
    
    async def run():
        scraper = IntelligentLeadScraper()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(f"🧠 AI searching: {query}...", total=None)
            result = await scraper.search(query, max_leads=max_leads, num_search_queries=num_queries)
            progress.update(task, completed=True)
        
        return result
    
    result = asyncio.run(run())
    
    # Stats (no query display - cleaner output)
    console.print(f"\n[green]✅ Found {len(result.leads)} leads with contact info[/green]")
    console.print(f"[dim]LLM: {result.llm_time:.1f}s | Search: {result.search_time:.1f}s | Scrape: {result.scrape_time:.1f}s | URLs: {result.total_urls_found} | Queries: {len(result.queries_generated)}[/dim]\n")
    
    # Pretty table output
    table = Table(show_header=True, header_style="bold magenta", title="🎯 Leads Found (AI-Powered)")
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="cyan", max_width=30)
    table.add_column("Email", style="green", max_width=28)
    table.add_column("Phone", style="yellow", max_width=14)
    table.add_column("URL", style="blue", max_width=35)
    
    for i, lead in enumerate(result.leads, 1):
        table.add_row(
            str(i),
            lead.name[:30] if lead.name else "-",
            lead.email or "-",
            lead.phone or "-",
            lead.website[:35] if lead.website else "-",
        )
    
    console.print(table)
    
    # Save to file
    if output:
        leads_data = [
            {
                "name": lead.name,
                "email": lead.email,
                "phone": lead.phone,
                "address": lead.address,
                "website": lead.website,
            }
            for lead in result.leads
        ]
        
        with open(output, "w") as f:
            json.dump({
                "query": query,
                "queries_used": result.queries_generated,
                "leads": leads_data
            }, f, indent=2)
        
        console.print(f"\n[green]💾 Saved to {output}[/green]")
    
    if result.errors:
        console.print(f"\n[yellow]⚠️ Errors: {len(result.errors)}[/yellow]")


if __name__ == "__main__":
    cli()


