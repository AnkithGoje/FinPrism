# FinPrism: Configurable Financial Analyst Agent

**FinPrism** is a single, configurable AI agent that switches between **3 financial analyst personas** and **3 market sectors** (Indian Equities: NSE/BSE), backed by a real SQLite database queried exclusively via **MCP (Model Context Protocol)**, with both a Streamlit chat UI and a FastAPI REST endpoint.

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd configureable-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your API key (Poolside, Groq, or OpenAI)
```

**Supported LLM Providers:**
- **Poolside AI (Primary)**: Set `POOLSIDE_API_KEY`, `POOLSIDE_BASE_URL` (optional), and `POOLSIDE_MODEL`.
- **Groq (Secondary / High-Speed)**: Set `GROQ_API_KEY` (default model: `llama-3.3-70b-versatile`).
- **xAI / OpenAI (Fallback)**: Set `XAI_API_KEY` or `OPENAI_API_KEY`.

### 3. Build the database

```bash
python db/build_db.py
```

Expected output:
```
Building financial_agent.db...
Schema applied: db/schema.sql
Sector metadata loaded.

Loading sector: tech
  Companies loaded: tech (12 rows)
  Financials loaded: tech
  News signals loaded: tech
...

=== Database Verification ===
  companies: 36 rows
  financials: 72 rows
  news_signals: ~49 rows
  sector_meta: 3 rows

✅ Database build complete!
```

### 4a. Run the Streamlit UI

```bash
streamlit run ui/streamlit_app.py
```

Opens at `http://localhost:8501`. Select persona + sector in the sidebar, then chat.

### 4b. Run the REST API

```bash
uvicorn api.main:app --reload --port 8000
```

Interactive API docs at `http://localhost:8000/docs`

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  User Interfaces                  │
│  ┌──────────────────┐    ┌──────────────────┐   │
│  │   Streamlit UI   │    │   FastAPI REST   │   │
│  │ (persona/sector  │    │  POST /query     │   │
│  │  dropdowns, chat)│    │  → JSON response │   │
│  └────────┬─────────┘    └────────┬─────────┘   │
└───────────│──────────────────────│──────────────┘
            └───────────┬──────────┘
                        ▼
┌─────────────────────────────────────────────────┐
│              Agent Core (agent/agent.py)          │
│  • Builds system prompt from persona config      │
│  • Runs OpenAI GPT-4o tool-calling loop          │
│  • Returns structured AgentResponse              │
└────────────────────┬────────────────────────────┘
                     │ MCP JSON-RPC (stdio)
                     ▼
┌─────────────────────────────────────────────────┐
│            MCP Server (mcp_server/server.py)     │
│  Tools: get_sector_summary, list_companies,      │
│         get_company_financials, search_companies,│
│         get_news_signals                         │
└────────────────────┬────────────────────────────┘
                     │ SQLite queries
                     ▼
┌─────────────────────────────────────────────────┐
│           db/financial_agent.db (SQLite)         │
│  36 companies × 3 sectors, FY2022–2024           │
└─────────────────────────────────────────────────┘
```

---

## Personas

| Persona ID | Display Name | Analytical Lens |
|-----------|-------------|-----------------|
| `mutual_fund_analyst` | Mutual Fund Analyst | Long-only, benchmark-relative, growth durability, valuation vs. index |
| `equity_analyst` | Equity Analyst | Earnings trends, margin trajectory, P/E and EV/EBITDA multiples |
| `pe_analyst` | PE Analyst | Leverage capacity, EBITDA margin upside, EV/EBITDA entry/exit, IRR scenarios |

The same question asked with different personas produces meaningfully different answers — different framing, different metrics emphasized, different conclusions.

---

## Sectors (Indian Equity Universe)

| Sector ID | Companies (NSE Tickers) | Benchmark |
|-----------|-------------------------|-----------|
| `tech` | TCS, Infosys (INFY), HCLTech (HCLTECH), Wipro (WIPRO), Tech Mahindra (TECHM), LTIMindtree (LTIM), Persistent Systems (PERSISTENT), Coforge (COFORGE), Mphasis (MPHASIS), Tata Elxsi (TATAELXSI), KPIT Technologies (KPITTECH), Zensar Technologies (ZENSARTECH) | Nifty IT Index |
| `retail` | Avenue Supermarts (DMART), Trent (TRENT), Titan (TITAN), Reliance Retail proxy (RELIANCE), Aditya Birla Fashion (ABFRL), Shoppers Stop (SHOPERSTOP), V-Mart (VMART), Metro Brands (METROBRAND), Vedant Fashions (MANYAVAR), Nykaa (NYKAA), Devyani International (DEVYANI), Spencer's (SPENCERS) | Nifty India Consumption Index |
| `manufacturing` | Larsen & Toubro (LT), Tata Motors (TATAMOTORS), Mahindra & Mahindra (M&M), Bharat Electronics (BEL), Hindustan Aeronautics (HAL), Cummins India (CUMMINSIND), Siemens India (SIEMENS), ABB India (ABB), Bharat Forge (BHARATFORG), Thermax (THERMAX), Dixon Tech (DIXON), AIA Engineering (AIAENG) | Nifty India Manufacturing Index |

---

## API Reference

### `POST /query`

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which companies look like attractive buyout targets?",
    "persona": "pe_analyst",
    "sector": "manufacturing"
  }'
```

Response:
```json
{
  "query": "Which companies look like attractive buyout targets?",
  "persona": "pe_analyst",
  "persona_display": "PE Analyst",
  "sector": "manufacturing",
  "sector_display": "Manufacturing",
  "answer": "Based on the data in the database...",
  "reasoning_lens": "PE deal lens: leverage capacity, EBITDA improvement, EV/EBITDA entry/exit",
  "companies_referenced": ["Cummins India", "AIA Engineering"],
  "tool_calls_made": [
    {"tool_name": "get_sector_summary", "arguments": {"sector": "manufacturing"}, "result_summary": "OK"},
    {"tool_name": "list_companies", "arguments": {"sector": "manufacturing"}, "result_summary": "Returned 12 items"}
  ],
  "confidence": "high",
  "data_coverage_note": "",
  "caveats": "Data sourced from public filings as of mid-2024. Not investment advice."
}
```

### Other endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/personas` | List all personas |
| `GET` | `/sectors` | List all sectors |
| `GET` | `/docs` | Swagger UI |

---

## Project Structure

```
configureable-agent/
├── README.md
├── .env.example
├── requirements.txt
│
├── db/
│   ├── schema.sql              # DDL for all 4 tables
│   ├── build_db.py             # Builds SQLite from seed CSVs
│   ├── financial_agent.db      # SQLite DB (built by build_db.py)
│   └── seed_data/
│       ├── tech_companies.csv
│       ├── tech_financials.csv
│       ├── tech_news.csv
│       ├── retail_companies.csv
│       ├── retail_financials.csv
│       ├── retail_news.csv
│       ├── manufacturing_companies.csv
│       ├── manufacturing_financials.csv
│       └── manufacturing_news.csv
│
├── mcp_server/
│   ├── server.py               # MCP stdio server (5 tools exposed)
│   └── db_queries.py           # SQLite queries (only used by MCP server)
│
├── agent/
│   ├── agent.py                # Core LLM tool-calling loop
│   ├── personas.py             # Persona configs + system prompt builder
│   ├── mcp_client.py           # Subprocess MCP client
│   └── schemas.py              # Pydantic request/response models
│
├── api/
│   └── main.py                 # FastAPI REST API
│
├── ui/
│   └── streamlit_app.py        # Streamlit chat interface
│
└── docs/
    └── schema_decisions.md     # Data sourcing + design notes
```

---

## Design Notes (Assignment Write-Up)

### 1. Schema Decisions
The database uses a 4-table normalized SQLite schema designed to give the agent structured, multi-dimensional grounding without prompt hardcoding:
* **`companies`**: Master record of static company attributes (name, ticker, sector, employee headcount, headquarters, founding year, business description). Normalized to eliminate redundant string storage across reporting periods.
* **`financials`**: Multi-year time-series financial statements (FY2022–FY2024) including Revenue, EBITDA, Net Income, Gross/EBITDA margins, P/E, EV/EBITDA, Debt/Equity, ROE, and Free Cash Flow. Storing multi-year data allows the Equity Analyst to analyze margin trajectories and the PE Analyst to model historical cash conversion.
* **`sector_meta`**: Sector-level benchmark indices (e.g., NASDAQ-100 for Tech, XLI for Manufacturing) and peer averages (avg P/E, avg EV/EBITDA). This is fetched dynamically via MCP at the start of every query and interpolated into the system prompt, guaranteeing that benchmark references reflect the DB rather than model hallucinations.
* **`news_signals`**: Event-driven signals categorized by type (`hiring`, `layoffs`, `expansion`, `earnings_beat`, `acquisition`). This directly supports data-grounding stress tests (e.g., headcount and hiring signals).

**Key Schema Considerations:**
* **Unprofitable Companies**: Companies with negative earnings are stored with `pe_ratio = -1.0` (sentinel value) rather than `NULL` or 0, enabling the agent to distinguish between missing data and unprofitable high-growth names.
* **Integrity Constraints**: DB-level `CHECK(sector IN ('tech', 'retail', 'manufacturing'))` prevents corrupted data entry.
* **Scope Trade-offs**: Annual data was chosen over quarterly to provide sufficient strategic depth for all three personas while keeping data compilation auditable and transparent.

---

### 2. MCP Protocol Boundary Design
Model Context Protocol (MCP) serves as the **strict architectural boundary** between the reasoning agent and data persistence:
* **Subprocess Stdio Transport**: Rather than importing SQLite queries inline as Python functions, `mcp_server/server.py` runs as an isolated child OS process. The agent communicates strictly over standard input/output using the official `mcp` SDK's JSON-RPC protocol (`StdioServerParameters`, `stdio_client`, `ClientSession`). This guarantees zero code coupling between the agent runtime and the database layer.
* **Semantic Scoped Tools vs. Generic SQL**:
  Instead of exposing an open `execute_sql` tool (which invites SQL injection, hallucinated schema queries, and unconstrained table scans), we exposed 5 purpose-built semantic tools:
  1. `get_sector_summary(sector)` — Macro overview and benchmark multiples.
  2. `list_companies(sector)` — High-level sector screen.
  3. `get_company_financials(company_name, sector)` — Deep multi-year financial history with explicit `found: false` handling.
  4. `search_companies(query, sector)` — Fuzzy ticker and company name lookup.
  5. `get_news_signals(company_name, sector)` — Recent operational developments and headcount signals.
* **Single-Session Batching**: Parallel tool requests generated by the LLM are batched within a single MCP session context (`call_tools_batch_sync`), reducing OS subprocess handshakes while preserving strict protocol boundaries.
* **Auditability & UI Transparency**: All MCP tool calls made during reasoning are recorded in `AgentResponse.tool_calls_made` and displayed in the Streamlit UI's expandable **🔧 MCP Tool Calls** panel.

---

### 3. One Thing I'd Improve With More Time
**Automated Real-Time SEC EDGAR & Market API Ingestion**:
Currently, the database is compiled from public filings (10-Ks, investor relations disclosures) as of mid-2024. With additional time, I would build an event-driven ingestion pipeline connecting directly to the **SEC EDGAR XBRL API** and **Polygon.io/Financial Modeling Prep**:
* Automatically ingest quarterly 10-Q filings and 8-K operational updates on release.
* Implement a vector RAG index over raw earnings call transcripts and 10-K Item 7 (MD&A) sections. This would allow the Mutual Fund and PE analysts to cite verbatim management commentary alongside quantitative balance sheet metrics, marrying structured SQL data with unstructured sentiment.

---

## LLM Configuration

The agent uses the OpenAI-compatible API interface and dynamically selects providers configured in `.env`:
* **Poolside AI (Primary)**: Configure `POOLSIDE_API_KEY`, `POOLSIDE_BASE_URL`, and `POOLSIDE_MODEL`.
* **Groq (Secondary / High-Speed)**: Configure `GROQ_API_KEY` (defaulting to `llama-3.3-70b-versatile` with native tool-calling).
* **xAI Grok / OpenAI (Fallback)**: Supports `XAI_API_KEY` (`grok-beta`) or `OPENAI_API_KEY` (`gpt-4o`).

---

## Data Quality Caveats

- **Time Horizon**: Sourced from public 10-K filings, Yahoo Finance, and company investor relations disclosures as of **mid-2024**.
- **Negative P/E Sentinel**: P/E ratios listed as `-1.0` designate unprofitable companies with negative net income.
- **Segment Approximations**: Amazon's retail business is estimated by isolating AWS segment revenue and operating margin from consolidated figures.
- **Capital Structure Adjustments**: Retailers like Home Depot and Lowe's maintain negative book equity due to extensive historical share repurchases; their Debt/Equity ratios reflect leveraged capital structures rather than insolvency.
- **Disclaimer**: This software is designed for analytical demonstration purposes and does not constitute formal investment advice.

---

## Evaluation & Sanity Checks

Run the automated evaluation suite verifying database integrity, prompt permutations, out-of-scope refusals, and grounding signals:
```bash
python tests/test_evaluation_queries.py
```

### Recommended 3–5 Minute Video Walkthrough Outline
1. **Introduction (30s)**: Overview of the 3 personas, 3 sectors, and SQLite MCP architecture.
2. **Persona Comparison (90s)**: Ask *"Is this sector a good place to be putting money to work right now?"* in Tech under **Mutual Fund Analyst** (benchmark-relative, index weight) vs. **PE Analyst** (entry EV/EBITDA, leverage capacity, exit horizons).
3. **MCP Tool Transparency (45s)**: Expand the **🔧 MCP Tool Calls** panel in Streamlit to show live JSON-RPC tool invocations.
4. **Data Grounding & Anti-Hallucination (45s)**:
   - Ask for NVIDIA's headcount signal to show real database retrieval.
   - Ask about an unlisted company (e.g. *"What do you think about Tesla?"*) to show honest refusal without hallucination.
5. **REST API (30s)**: Submit a `curl` query to `POST /query` showing structured JSON with `companies_referenced`, `confidence`, and `reasoning_lens`.
#   F i n P r i s m  
 