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


if __name__ == "__main__":
    cli()
