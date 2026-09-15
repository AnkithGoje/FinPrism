# FinPrism: Persona-Configurable Financial Analyst Agent
 
[![Python](https://img.shields.io/badge/python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40+-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Protocol](https://img.shields.io/badge/Protocol-MCP%20JSON--RPC-blueviolet.svg?style=flat)](https://modelcontextprotocol.io)
[![Market](https://img.shields.io/badge/Equities-NSE%20%2F%20BSE%20(India)-orange.svg?style=flat)](https://www.nseindia.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE)
 
An equity research agent that switches between three investment personas and three sectors of the Indian market (NSE/BSE), grounded entirely in a local SQLite database through the Model Context Protocol.
 
[Quick Start](#quick-start) • [Architecture](#architecture) • [Personas](#analyst-personas) • [Sectors](#sectors-and-universe-indian-equities) • [API Docs](#api-reference) • [Design Notes](#design-notes-assignment-write-up) • [Evaluation](#evaluation-and-verification)
 
---
 
## Overview
 
FinPrism is a financial analyst agent that answers questions about Indian equities from the perspective of three different roles: a mutual fund analyst, a sell-side equity analyst, and a private equity associate. Each persona reasons differently about the same underlying data, so the same question can produce very different answers depending on who's "asking."
 
Most agent demos let the model pull facts from wherever it wants, whether that's a hardcoded prompt or an open web search. FinPrism doesn't do that. Every answer has to come from a 4-table SQLite database, and the agent can only reach that database through a subprocess running over stdio JSON-RPC, using the Model Context Protocol. Every tool call the agent makes gets logged, along with a confidence score and the tickers it referenced, so you can see exactly where an answer came from.
 
---
 
## Quick Start
 
### 1. Clone the repo and set up your environment
 
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
 
### 2. Add your API keys
 
```bash
cp .env.example .env
```
 
Then edit `.env` with whichever model provider you're using:
 
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
 
### 3. Build and seed the database
 
```bash
python db/build_db.py
```
 
You should see something like this:
 
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
Database build complete!
```
 
### 4. Launch a UI
 
**Streamlit dashboard**
 
```bash
streamlit run ui/streamlit_app.py
```
 
Go to `http://localhost:8501` to pick a persona, try sample queries, and expand the MCP Tool Calls panel to see what the agent looked up.
 
**FastAPI server**
 
```bash
uvicorn api.main:app --reload --port 8000
```
 
Swagger docs are at `http://localhost:8000/docs`.
 
---
 
## Architecture
 
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
│  • Builds the persona prompt from agent/personas.py                    │
│  • Enforces currency conventions (₹ Crores) and reasoning guardrails   │
│  • Runs a multi-turn tool-calling loop with tool_choice="required"     │
│  • Parses the structured AgentResponse payload                         │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ Model Context Protocol (stdio)
                                     │ JSON-RPC 2.0 Client/Server
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     MCP Server (mcp_server/server.py)                  │
│  Exposes 5 scoped tools:                                                │
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
 
## Analyst Personas
 
Each persona looks at the same data with a different job in mind, so the valuation lens and the metrics it leans on change accordingly.
 
| Persona ID | Role | What it cares about | How it values things |
|---|---|---|---|
| `mutual_fund_analyst` | Mutual Fund Analyst | Beating the benchmark, portfolio risk, finding compounders | Valuation relative to Nifty sectoral indices, revenue CAGR, how consistent ROE has been |
| `equity_analyst` | Sell-Side Equity Analyst | Fundamental valuation, quarterly margin trends, what could move the stock | P/E, EV/EBITDA, margin expansion or compression, rating calls |
| `pe_analyst` | Private Equity Associate | Whether a buyout makes sense, deleveraging, operational turnarounds | Free cash flow conversion, how much debt the balance sheet can carry, multiple arbitrage, IRR |
 
---
 
## Sectors and Universe (Indian Equities)
 
The database covers 36 large and mid-cap Indian companies across three sectors.
 
### 1. Technology (IT Services & Solutions)
Benchmarked against the Nifty IT Index. Covers TCS, Infosys (`INFY`), HCLTech (`HCLTECH`), Wipro (`WIPRO`), Tech Mahindra (`TECHM`), LTIMindtree (`LTIM`), Persistent Systems (`PERSISTENT`), Coforge (`COFORGE`), Mphasis (`MPHASIS`), Tata Elxsi (`TATAELXSI`), KPIT Technologies (`KPITTECH`), and Zensar Technologies (`ZENSARTECH`).
 
### 2. Consumer Retail & Discretionary
Benchmarked against the Nifty India Consumption Index. Covers DMart (`DMART`), Trent (`TRENT`), Titan (`TITAN`), Reliance Retail Proxy (`RELIANCE`), Aditya Birla Fashion (`ABFRL`), Shoppers Stop (`SHOPERSTOP`), V-Mart (`VMART`), Metro Brands (`METROBRAND`), Vedant Fashions (`MANYAVAR`), Nykaa (`NYKAA`), Devyani International (`DEVYANI`), and Spencer's Retail (`SPENCERS`).
 
### 3. Industrials & Capital Goods
Benchmarked against the Nifty India Manufacturing Index. Covers Larsen & Toubro (`LT`), Tata Motors (`TATAMOTORS`), Mahindra & Mahindra (`M&M`), Bharat Electronics (`BEL`), Hindustan Aeronautics (`HAL`), Cummins India (`CUMMINSIND`), Siemens India (`SIEMENS`), ABB India (`ABB`), Bharat Forge (`BHARATFORG`), Thermax (`THERMAX`), Dixon Technologies (`DIXON`), and AIA Engineering (`AIAENG`).
 
---
 
## API Reference
 
### `POST /query`
 
Runs an analysis for a given persona, sector, and question.
 
**Request**
 
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Which companies have the strongest EBITDA margins and cash conversion?",
    "persona": "pe_analyst",
    "sector": "manufacturing"
  }'
```
 
**Response**
 
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
 
### Other endpoints
 
- `GET /health`, service status
- `GET /personas`, lists the available personas
- `GET /sectors`, lists supported sectors, tickers, and benchmark indices
- `GET /docs`, Swagger UI
---
 
## Repository Structure
 
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
 
## Design Notes (Assignment Write-Up)
 
### 1. Why the schema looks the way it does
 
The database is split into four normalized tables, mostly so the agent has structured data to reason over instead of facts baked into a prompt.
 
`companies` holds static attributes like name, ticker, sector, employee count, headquarters, founding year, and a short business description. Keeping this separate from the year-by-year numbers avoids repeating the same strings across every reporting period.
 
`financials` covers FY23 and FY24: revenue, EBITDA, net income, gross and EBITDA margins, P/E, EV/EBITDA, debt to equity, ROE, and free cash flow. Having two years of data lets the equity analyst persona actually look at a margin trend instead of a single snapshot, and gives the PE analyst something to model cash flow stability against.
 
`sector_meta` stores the benchmark index for each sector (Nifty IT, Nifty India Consumption, Nifty India Manufacturing) along with peer averages. This gets pulled in through MCP at query time, so benchmark comparisons are tied to what's actually in the database rather than something the model remembers.
 
`news_signals` tracks event-driven items like hiring, expansion, order wins, and earnings beats. This is what lets the agent answer questions about headcount changes or recent strategic moves without needing a live news feed.
 
A couple of smaller decisions worth flagging: companies with negative earnings get `pe_ratio = -1.0` instead of `NULL` or `0`, so the agent can tell the difference between "no data" and "unprofitable but growing." Everything is denominated in rupees crore, formatted the way Indian corporate filings actually format numbers (`₹2,40,890 Cr`). And there's a database-level check constraint on sector values so bad data can't sneak in.
 
### 2. Why MCP sits between the agent and the database
 
The main reason for using MCP here is to keep the agent from having any direct line into the database. `mcp_server/server.py` runs as its own OS process, and the agent talks to it only over stdin/stdout using JSON-RPC, through the official `mcp` SDK (`StdioServerParameters`, `stdio_client`, `ClientSession`). There's no shared Python import between the agent and the query layer, so the two can't drift into being coupled by accident.
 
The server also doesn't expose a generic `execute_sql` tool. That's deliberate: an open SQL tool invites prompt injection, made-up schema queries, and full table scans nobody asked for. Instead there are five narrow tools:
 
1. `get_sector_summary(sector)`, a macro view and benchmark multiples
2. `list_companies(sector)`, a high-level screen of sector constituents
3. `get_company_financials(company_name, sector)`, multi-year history with explicit `found: false` handling
4. `search_companies(query, sector)`, fuzzy lookup by ticker or name
5. `get_news_signals(company_name, sector)`, recent operational developments and headcount signals
When the model fires off several tool calls at once, they get batched into a single MCP session (`call_tools_batch_sync`) rather than spinning up a new process for each one. And every tool call the agent makes during a query gets logged into `AgentResponse.tool_calls_made`, which is what shows up in the Streamlit UI's expandable MCP Tool Calls panel.
 
### 3. What I'd build next if I had more time
 
Right now the database is seeded once from FY24 filings, so it's a snapshot rather than something that stays current. Given more time, I'd wire up an ingestion pipeline against the NSE/BSE corporate filings APIs and something like Screener.in or Trendlyne, so quarterly results and disclosures get pulled in as they're released.
 
I'd also want a vector index over earnings call transcripts and the MD&A sections of annual reports. That would let the mutual fund and PE personas quote actual management commentary alongside the balance sheet numbers, instead of relying on structured data alone.
 
---
 
## Evaluation and Verification
 
There's a test suite that checks database integrity, all nine persona and sector combinations, refusal handling for out-of-scope questions, and whether answers are actually grounded in the data.
 
```bash
python -m pytest tests/test_evaluation_queries.py -v
```
 
The four test suites cover MCP tool schemas, multi-turn reasoning limits, and query integrity, and none of them need a live LLM API key to run.