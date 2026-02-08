# 🏭 Sovereign Order Intelligence - CLI Commands

Complete reference for all SOI command-line interface commands.

---

## Quick Install & Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys (SERPER_API_KEY, GROQ_API_KEY, etc.)

# Verify installation
soi status
```

---

## 🎯 Lead Generation Commands

### `soi leads scrape` - Basic Lead Scraping

Scrape leads with emails, phones, and addresses from Google search results.

```bash
# Basic usage
soi leads scrape "dentists in Miami"

# Get 50 leads
soi leads scrape "coffee shops Austin" -n 50

# Save to JSON file
soi leads scrape "plumbers Los Angeles" -n 100 -o leads.json

# JSON output to stdout
soi leads scrape "lawyers NYC" --json
```

| Option | Description | Default |
|--------|-------------|---------|
| `-n, --max` | Maximum leads to find | 20 |
| `-o, --output` | Save results to JSON file | - |
| `--json` | Output as JSON to console | False |

---

### `soi leads smart` - 🧠 AI-Powered Lead Search

Uses **Groq LLM** to intelligently generate diverse search queries for maximum lead capture. Best for finding leads with verified contact info.

```bash
# Basic AI search
soi leads smart "dentists in Miami" -n 50

# More queries = more diverse results
soi leads smart "lawyers Los Angeles" -q 10 -n 100

# Save with all query metadata
soi leads smart "software agencies SF" -o leads.json
```

| Option | Description | Default |
|--------|-------------|---------|
| `-n, --max` | Maximum leads to find | 50 |
| `-q, --queries` | Number of LLM-generated search queries | 5 |
| `-o, --output` | Save results to JSON file | - |

**How it works:**
1. LLM generates diverse search queries (e.g., "orthodontists Miami", "pediatric dentists South Beach")
2. Each query fetches up to 100 URLs via Serper (paginated)
3. Auto-rotates to generate more queries if target not met
4. Extracts emails and phones from each webpage

---

### `soi leads linkedin` - 🔗 LinkedIn Profile Scraping

Searches LinkedIn profiles for B2B lead generation with Gmail extraction.

```bash
# Find LinkedIn profiles with Gmail
soi leads linkedin "dentists Miami" -n 50

# Get 100 profiles
soi leads linkedin "software engineers San Francisco" -n 100

# Save to JSON
soi leads linkedin "marketing managers NYC" -n 100 -o linkedin_leads.json
```

| Option | Description | Default |
|--------|-------------|---------|
| `-n, --max` | Maximum profiles to find | 50 |
| `-o, --output` | Save results to JSON file | - |

**Output includes:** Name, **Gmail**, Role, Company, LinkedIn URL

**How it works:**
- Searches `site:linkedin.com/in {query} "gmail"`
- Paginates through results until target met
- Uses query variations if more profiles needed
- Extracts Gmail from profile snippets

---

## 📦 Vendor Management Commands

### `soi vendors list` - List All Vendors

```bash
# List all vendors
soi vendors list

# Limit results
soi vendors list --limit 10
```

---

### `soi vendors add` - Add a Vendor

Add a new vendor to the knowledge base.

```bash
soi vendors add "Acme Corp" \
  --description "Industrial equipment supplier" \
  --website "https://acme.com" \
  --industry "Manufacturing" \
  --products "Motors" --products "Pumps"
```

| Option | Description |
|--------|-------------|
| `--description` | Vendor description |
| `--website` | Vendor website URL |
| `--industry` | Industry category |
| `--products` | Products (can repeat) |

---

### `soi vendors search` - Search Vendors

```bash
# Search by name or description
soi vendors search "industrial equipment"

# Limit results
soi vendors search "pumps" --limit 5
```

---

## 📄 Document Commands

### `soi docs process` - Process a Document

Extract structured data from invoices, contracts, or bids.

```bash
# Process an invoice
soi docs process invoice.pdf --type invoice

# Process a contract
soi docs process contract.pdf --type contract

# Process a bid document
soi docs process bid.pdf --type bid
```

| Option | Description | Values |
|--------|-------------|--------|
| `--type` | Document type | `invoice`, `contract`, `bid` |

---

### `soi docs add` - Add Document to Knowledge Base

Store a document in the vector database for RAG queries.

```bash
soi docs add report.pdf \
  --type report \
  --description "Q4 2024 vendor performance report"
```

---

### `soi docs list` - List All Documents

```bash
soi docs list
```

Shows all documents stored in the vector database with metadata.

---

## 🔍 Analysis & Research Commands

### `soi analyze` - Analyze a Query

Run the full Order Intelligence workflow on a query.

```bash
# Basic analysis
soi analyze "Who are the top packaging suppliers in Texas?"

# With specific criteria
soi analyze "Compare industrial valve manufacturers" \
  --criteria "price" --criteria "quality" --criteria "delivery"

# Save output
soi analyze "Best packaging solutions" --save

# JSON output
soi analyze "Vendor comparison" --json
```

| Option | Description |
|--------|-------------|
| `--criteria` | Evaluation criteria (can repeat) |
| `--json` | Output as JSON |
| `--save` | Save to file |
| `--verbose` | Detailed output |

---

### `soi grade` - Grade a Vendor

Grade a specific vendor on evaluation criteria.

```bash
# Grade with web research
soi grade "Acme Corp" --web

# Grade on specific criteria
soi grade "Acme Corp" --criteria "reliability" --criteria "pricing"
```

---

### `soi research vendor` - Research a Vendor Online

Deep web research on a specific vendor.

```bash
soi research vendor "Tesla Inc"
```

---

### `soi research market` - Market Research

Research market trends for a category.

```bash
soi research market "renewable energy"
```

---

### `soi research company` - 🏢 Deep Company Research

Comprehensive research on any company with executives, news, funding, market data, and competitors. Uses **20 Serper API queries** for maximum data coverage.

```bash
# Research a company
soi research company "Salesforce"

# Save to JSON
soi research company "Stripe" -o stripe.json

# Save JSON + Markdown report
soi research company "Anthropic" -o anthropic.json -m anthropic_report.md
```

| Option | Description |
|--------|-------------|
| `-o, --output` | Save results to JSON file |
| `-m, --markdown` | Save markdown report file |

**Output includes:**

| Category | Data Points |
|----------|-------------|
| **Company Info** | Website, industry, HQ city/country, employees, founded year |
| **Executives** | CEO, founders, VPs with LinkedIn URLs (up to 11) |
| **Financials** | Total raised, last round, valuation, investors |
| **Market Data** | Market share, TAM/SAM (if available) |
| **Hiring Intelligence** | Open positions, key roles, tech stack, hiring locations |
| **Recent News** | Tagged by type: funding, product, partnership, acquisition |
| **Competitors** | List of similar companies |
| **Strategic Analysis** | SWOT, business model, investment thesis |
| **Data Sources** | Real-time URLs with snippets proving live search |

**Sample JSON Output:**
```json
{
  "overview": {
    "website": "salesforce.com",
    "hq_city": "San Francisco",
    "hq_country": "USA"
  },
  "financials": {
    "total_raised": "$13B",
    "valuation": "$350B",
    "investors": ["Sequoia", "Lightspeed"]
  },
  "market_data": {
    "market_share": "54%"
  },
  "hiring_details": {
    "total_openings": 411,
    "key_roles": ["Engineering", "AI/ML"],
    "tech_stack": ["Python", "Rust", "Go"]
  }
}
```

---

## 🖥️ Server & UI Commands

### `soi serve` - Start API Server

Launch the FastAPI backend server.

```bash
# Default (localhost:8000)
soi serve

# Custom host/port
soi serve --host 0.0.0.0 --port 3000

# Hot reload for development
soi serve --reload
```

---

### `soi ui` - Launch Web Interface

Start the Streamlit web dashboard.

```bash
# Default port 8501
soi ui

# Custom port
soi ui --port 8080
```

---

### `soi status` - Check System Status

Verify all services and API connections.

```bash
soi status
```

Shows:
- ✅ Ollama connection
- ✅ ChromaDB status
- ✅ Serper API key
- ✅ Groq API key

---

## 🔧 Environment Variables

Required API keys in `.env`:

```bash
# Required for lead scraping
SERPER_API_KEY=your_serper_key

# Required for AI-powered search
GROQ_API_KEY=your_groq_key

# Optional
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
TAVILY_API_KEY=your_tavily_key
```

---

## 📊 Quick Examples

```bash
# Find 100 dentists in Miami with emails
soi leads smart "dentists in Miami" -n 100 -o dentists.json

# Scrape LinkedIn marketing managers
soi leads linkedin "marketing managers Los Angeles" -n 50

# Analyze vendor landscape
soi analyze "Top solar panel manufacturers in California"

# Add vendor to database
soi vendors add "SolarCity" --industry "Energy" --website "https://solarcity.com"

# Process and store an invoice
soi docs process invoice.pdf --type invoice
soi docs add invoice.pdf --description "Vendor invoice Q1 2024"
```

---

## 📁 Output Formats

### Lead Scraping JSON Output

```json
{
  "query": "dentists in Miami",
  "queries_used": [...],
  "leads": [
    {
      "name": "Miami Dental Clinic",
      "email": "info@miamidental.com",
      "phone": "(305) 555-1234",
      "address": "123 Main St, Miami, FL",
      "website": "https://miamidental.com"
    }
  ]
}
```

### LinkedIn JSON Output

```json
{
  "query": "marketing managers NYC",
  "profiles": [
    {
      "name": "John Doe",
      "title": "Marketing Manager",
      "company": "Acme Inc",
      "location": "New York, NY",
      "linkedin_url": "https://linkedin.com/in/johndoe"
    }
  ]
}
```
