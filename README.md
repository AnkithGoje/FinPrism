# 💎 FinPrism: Persona-Configurable Financial Analyst Agent

<div align="center">

[![Python](https://img.shields.io/badge/python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Protocol](https://img.shields.io/badge/Protocol-MCP%20JSON--RPC-blueviolet.svg?style=flat)](https://modelcontextprotocol.io)
[![Market](https://img.shields.io/badge/Equities-NSE%20%2F%20BSE%20(India)-orange.svg?style=flat)](https://www.nseindia.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE)

**Multi-lens AI equity research agent backed by Model Context Protocol (MCP) and Indian Market Fundamentals.**

[Quick Start](#-quick-start) •
[Architecture](#-architecture) •
[Personas](#-analyst-personas) •
[Sectors & Universe](#-sectors-and-universe-indian-equities) •
[API Docs](#-api-reference) •
[Design Write-Up](#-design-notes-assignment-write-up) •
[Evaluation](#-evaluation--verification)

</div>

---

## 📌 Overview

**FinPrism** is a production-grade, persona-configurable financial analyst agent that dynamically shifts its reasoning lens across **3 investment personas** and **3 industry sectors** in the Indian equity universe (NSE/BSE). 

Unlike typical wrapper agents that bundle hardcoded facts into prompts or query LLMs with open-ended web browsing, FinPrism enforces a **strict architectural boundary via Model Context Protocol (MCP)**:
- Reasoning is grounded strictly in a 4-table normalized SQLite database.
- Database access occurs exclusively across a subprocess stdio JSON-RPC protocol.
- Answers are accompanied by machine-readable metadata (referenced tickers, confidence scores, reasoning lenses, and auditable tool-call logs).

---

## 🚀 Quick Start

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/AnkithGoje/FinPrism.git
cd FinPrism
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` with your preferred model provider:

```ini
# --- Primary Option: Poolside AI ---
POOLSIDE_API_KEY=your_poolside_api_key_here
POOLSIDE_BASE_URL=https://api.poolside.ai/v1
POOLSIDE_MODEL=poolside-model-name

# --- Secondary Option: Groq (High-Speed Llama 3.3 70B) ---
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# --- Fallback: OpenAI / xAI ---
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. Build & Seed SQLite Database

```bash
python db/build_db.py
```

Expected verification output:
```text
Building financial_agent.db...
Schema applied: db/schema.sql
Sector metadata loaded.
Loading sector: tech (12 companies, 24 financials, 12 news records)
Loading sector: retail (12 companies, 24 financials, 12 news records)
Loading sector: manufacturing (12 companies, 24 financials, 12 news records)

=== Database Verification ===
  companies: 36 rows
  financials: 72 rows
  news_signals: 36 rows
  sector_meta: 3 rows
✅ Database build complete!
```

### 4. Launch User Interfaces

#### Streamlit Web App (Interactive Dashboard)
```bash
streamlit run ui/streamlit_app.py
```
Open **`http://localhost:8501`** to interact with persona selectors, sample Indian equity queries, and the expandable **🔧 MCP Tool Calls** panel.

#### FastAPI REST Server (Headless API)
```bash
uvicorn api.main:app --reload --port 8000
```
Interactive OpenAPI documentation is available at **`http://localhost:8000/docs`**.

---

## 🏗️ Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          User Presentation Layer                       │
│      ┌─────────────────────────┐      ┌─────────────────────────┐      │
│      │   Streamlit Web App     │      │   FastAPI REST API      │      │
│      │  (ui/streamlit_app.py)  │      │      (api/main.py)      │      │
│      └────────────┬────────────┘      └────────────┬────────────┘      │
└───────────────────│────────────────────────────────│───────────────────┘
                    └────────────────┬───────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FinPrism Agent Core Layer                       │
│                          (agent/agent.py)                              │
│  • Compiles persona prompt from agent/personas.py                      │
│  • Enforces currency conventions (₹ Crores) & reasoning guardrails    │
│  • Executes multi-turn tool-calling loop with tool_choice="required"   │
│  • Parses structured AgentResponse payload                             │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ Model Context Protocol (stdio)
                                     │ JSON-RPC 2.0 Client/Server
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     MCP Server (mcp_server/server.py)                  │
│  Exposes 5 scoped semantic tools:                                      │
│  ├── get_sector_summary(sector)                                        │
│  ├── list_companies(sector)                                            │
│  ├── get_company_financials(company_name, sector)                      │
│  ├── search_companies(query, sector)                                   │
│  └── get_news_signals(company_name, sector)                            │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ Parameterized SQL Queries
                                     │ (mcp_server/db_queries.py)
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     SQLite Database (db/financial_agent.db)            │
│  • companies (36 Indian equities)    • financials (FY23–FY24 metrics)  │
│  • news_signals (36 event signals)   • sector_meta (Nifty benchmarks)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🎭 Analyst Personas

Each persona enforces distinct analytical priorities, valuation methods, and return hurdles:

| Persona ID | Role | Core Analytical Focus | Valuation & Metrics Lens |
|---|---|---|---|
| `mutual_fund_analyst` | **Mutual Fund Analyst** | Benchmark-relative outperformance, portfolio risk, compounders | Relative valuation vs Nifty Sectoral Indices, revenue CAGR, ROE persistence |
| `equity_analyst` | **Sell-Side Equity Analyst** | Fundamental valuation, quarterly margin trajectory, price catalysts | P/E multiples, EV/EBITDA, margin expansion/compression, rating calls |
| `pe_analyst` | **Private Equity Associate** | Buyout viability, balance sheet deleveraging, operational turnarounds | Free cash flow conversion, debt-to-equity capacity, multiple arbitrage, IRR |

---

## 📊 Sectors and Universe (Indian Equities)

The database covers **36 actively traded large- and mid-cap Indian companies** across 3 primary sectors:

### 1. Technology (IT Services & Solutions)
- **Benchmark**: Nifty IT Index
- **Constituents (12)**: TCS, Infosys (`INFY`), HCLTech (`HCLTECH`), Wipro (`WIPRO`), Tech Mahindra (`TECHM`), LTIMindtree (`LTIM`), Persistent Systems (`PERSISTENT`), Coforge (`COFORGE`), Mphasis (`MPHASIS`), Tata Elxsi (`TATAELXSI`), KPIT Technologies (`KPITTECH`), Zensar Technologies (`ZENSARTECH`).

### 2. Consumer Retail & Discretionary
- **Benchmark**: Nifty India Consumption Index
- **Constituents (12)**: Avenue Supermarts / DMart (`DMART`), Trent (`TRENT`), Titan (`TITAN`), Reliance Retail Proxy (`RELIANCE`), Aditya Birla Fashion (`ABFRL`), Shoppers Stop (`SHOPERSTOP`), V-Mart (`VMART`), Metro Brands (`METROBRAND`), Vedant Fashions (`MANYAVAR`), Nykaa (`NYKAA`), Devyani International (`DEVYANI`), Spencer's Retail (`SPENCERS`).

### 3. Industrials & Capital Goods
- **Benchmark**: Nifty India Manufacturing Index
- **Constituents (12)**: Larsen & Toubro (`LT`), Tata Motors (`TATAMOTORS`), Mahindra & Mahindra (`M&M`), Bharat Electronics (`BEL`), Hindustan Aeronautics (`HAL`), Cummins India (`CUMMINSIND`), Siemens India (`SIEMENS`), ABB India (`ABB`), Bharat Forge (`BHARATFORG`), Thermax (`THERMAX`), Dixon Technologies (`DIXON`), AIA Engineering (`AIAENG`).

---

## 🔌 API Reference

### `POST /query`
Executes an analysis for a specified persona, sector, and analytical query.

#### Request
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which companies have the strongest EBITDA margins and cash conversion?",
    "persona": "pe_analyst",
    "sector": "manufacturing"
  }'
```

#### Response
```json
{
  "query": "Which companies have the strongest EBITDA margins and cash conversion?",
  "persona": "pe_analyst",
  "persona_display": "PE Analyst",
  "sector": "manufacturing",
  "sector_display": "Manufacturing",
  "answer": "Based on the FY24 financial data in the database, Cummins India and AIA Engineering demonstrate the strongest margin and cash conversion profiles...",
  "reasoning_lens": "PE deal lens: leverage capacity, EBITDA improvement, EV/EBITDA entry/exit, IRR scenarios",
  "companies_referenced": ["Cummins India", "AIA Engineering", "Larsen & Toubro"],
  "tool_calls_made": [
    {
      "tool_name": "get_sector_summary",
      "arguments": {"sector": "manufacturing"},
      "result_summary": "Sector: manufacturing, Avg P/E: 52.8"
    },
    {
      "tool_name": "list_companies",
      "arguments": {"sector": "manufacturing"},
      "result_summary": "Returned 12 companies"
    },
    {
      "tool_name": "get_company_financials",
      "arguments": {"company_name": "Cummins India", "sector": "manufacturing"},
      "result_summary": "Returned 2 financial records for Cummins India"
    }
  ],
  "confidence": "high",
  "data_coverage_note": "FY23 and FY24 reported figures verified.",
  "caveats": "Data sourced from public BSE/NSE filings as of FY24. All figures in INR Crores unless specified."
}
```

### Additional Endpoints
- `GET /health`: Health and service availability status.
- `GET /personas`: Lists available analyst personas and descriptions.
- `GET /sectors`: Lists supported sectors, ticker coverage, and benchmark indices.
- `GET /docs`: Interactive Swagger UI.

---

## 📁 Repository Structure

```text
FinPrism/
├── .env.example              # Sample environment configuration
├── .gitignore                # Git ignore patterns (DB, keys, caches)
├── requirements.txt          # Production dependencies
├── README.md                 # Project documentation and assignment write-up
│
├── agent/                    # Core Agent Logic
│   ├── agent.py              # LLM tool-calling loop and provider resolution
│   ├── personas.py           # Persona prompt definitions and sector metadata
│   ├── mcp_client.py         # Subprocess stdio JSON-RPC MCP client
│   └── schemas.py            # Pydantic request and response models
│
├── mcp_server/               # Model Context Protocol Server
│   ├── server.py             # Official MCP server exposing 5 analytical tools
│   └── db_queries.py         # Parameterized SQLite query implementations
│
├── db/                       # Database Construction & Seeding
│   ├── schema.sql            # DDL for 4 normalized SQLite tables
│   ├── build_db.py           # Python ETL pipeline for seeding database
│   ├── financial_agent.db    # SQLite database (generated)
│   └── seed_data/            # Sourced CSVs (Companies, Financials, Signals)
│       ├── tech_*.csv
│       ├── retail_*.csv
│       └── manufacturing_*.csv
│
├── api/                      # REST API Layer
│   └── main.py               # FastAPI application endpoints and CORS setup
│
├── ui/                       # Web Dashboard
│   └── streamlit_app.py      # Streamlit multi-lens chat application
│
├── docs/                     # Additional Documentation
│   └── schema_decisions.md   # Architectural design choices
│
└── tests/                    # Verification & Sanity Checks
    └── test_evaluation_queries.py # Pytest test suite for personas & MCP
```

---

## 📝 Design Notes (Assignment Write-Up)

### 1. Schema Decisions
The persistence layer uses a 4-table normalized SQLite schema designed to give the agent structured, multi-dimensional grounding without prompt hardcoding:
* **`companies`**: Master record of static entity attributes (`id`, `name`, `ticker`, `sector`, `employee_count`, `headquarters`, `founding_year`, `business_description`). Normalizing static metadata eliminates redundant string storage across reporting periods.
* **`financials`**: Multi-year time-series financial statements (`FY2023–FY2024`) containing Revenue, EBITDA, Net Income, Gross/EBITDA margins, P/E, EV/EBITDA, Debt/Equity, ROE, and Free Cash Flow. Multi-year reporting enables the Equity Analyst to examine margin trajectories and the PE Analyst to model cash flow stability.
* **`sector_meta`**: Sector-level benchmark indices (e.g. *Nifty IT Index*, *Nifty India Consumption Index*, *Nifty India Manufacturing Index*) and sector peer averages. This is retrieved dynamically via MCP at query execution and injected into the prompt, ensuring benchmark comparisons reflect database ground truth.
* **`news_signals`**: Event-driven signals categorized by type (`hiring`, `expansion`, `order_win`, `earnings_beat`). This directly supports data-grounding stress tests (e.g. headcount changes and strategic wins).

**Key Considerations:**
- **Unprofitable Companies**: Companies with negative earnings are stored with `pe_ratio = -1.0` (sentinel value) rather than `NULL` or 0, enabling the agent to distinguish between missing data and unprofitable growth names.
- **Indian Market Representation**: All financial figures are denominated in **₹ Crores** (standard Indian corporate reporting standard), with numbers formatted in the Indian numbering system (`₹2,40,890 Cr`).
- **Integrity Constraints**: DB-level `CHECK(sector IN ('tech', 'retail', 'manufacturing'))` prevents corrupted data entry.

---

### 2. MCP Protocol Boundary Design
Model Context Protocol (MCP) serves as the **strict architectural boundary** between the reasoning agent and data persistence:
* **Subprocess Stdio Transport**: Rather than importing SQLite queries inline as Python modules, `mcp_server/server.py` runs as an isolated child OS process. The agent communicates strictly over standard input/output using the official `mcp` SDK's JSON-RPC protocol (`StdioServerParameters`, `stdio_client`, `ClientSession`). This guarantees zero code coupling between the agent runtime and the database layer.
* **Semantic Scoped Tools vs. Generic SQL**:
  Instead of exposing an open `execute_sql` tool (which risks prompt injection, hallucinated schema queries, and unconstrained table scans), FinPrism exposes 5 purpose-built semantic tools:
  1. `get_sector_summary(sector)` — Macro overview and benchmark multiples.
  2. `list_companies(sector)` — High-level sector constituent screen.
  3. `get_company_financials(company_name, sector)` — Deep multi-year financial history with explicit `found: false` handling.
  4. `search_companies(query, sector)` — Fuzzy ticker and company name lookup.
  5. `get_news_signals(company_name, sector)` — Recent operational developments and headcount signals.
* **Single-Session Batching**: Parallel tool requests generated by the LLM are batched within a single MCP session context (`call_tools_batch_sync`), minimizing process spawning overhead.
* **Auditability & UI Transparency**: All MCP tool calls made during reasoning are recorded in `AgentResponse.tool_calls_made` and displayed in the Streamlit UI's expandable **🔧 MCP Tool Calls** panel.

---

### 3. One Thing I'd Improve With More Time
**Automated Real-Time Indian Exchange (NSE/BSE) API Ingestion**:
Currently, the database is seeded from audited annual reports and filings as of FY24. With additional time, I would build an event-driven ingestion pipeline connecting directly to the **NSE/BSE Corporate Filings APIs** and **Screener.in / Trendlyne feeds**:
* Automatically ingest quarterly results (Q1/Q2/Q3/Q4) and regulatory disclosures on release.
* Implement a vector RAG index over conference call earnings transcripts and annual report MD&A sections. This would allow the Mutual Fund and PE analysts to cite verbatim management commentary alongside quantitative balance sheet metrics, marrying structured SQL data with unstructured sentiment.

---

## 🧪 Evaluation & Verification

A dedicated automated test suite validates database integrity, all 9 persona × sector permutations, out-of-scope refusal handling, and data grounding:

```bash
python -m pytest tests/test_evaluation_queries.py -v
```
