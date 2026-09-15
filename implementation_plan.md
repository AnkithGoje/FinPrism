# Configurable Financial Agent — Implementation Plan

## Project Overview

Build a single, configurable AI agent that switches between **3 financial analyst personas** (MF Analyst, Equity Analyst, PE Analyst) and **3 market sectors** (Tech, Retail, Manufacturing), backed by a real SQLite database queried live through **MCP (Model Context Protocol)**, with both a Streamlit UI and a REST API as interfaces.

---

## Understanding Lock ✅

> This section confirms shared understanding before any design is locked in.

**What is being built:**
- A persona-switchable financial analyst agent (9 valid persona×sector combos)
- A real SQLite database with hand-curated sector data (10–15 companies per sector)
- An MCP server as the protocol boundary for all DB tool calls
- A Streamlit chat UI for human use
- A FastAPI REST endpoint for programmatic use
- Both interfaces hit the **same** underlying agent logic

**Why it exists:** AI engineer take-home to assess system design, MCP usage, prompt engineering, and fullstack thinking.

**Key constraints:**
- Persona must change *reasoning*, not just tone
- DB must be queried live — no hardcoded facts in prompts
- MCP must be a real protocol boundary (not a fake wrapper)
- Agent must refuse to hallucinate about companies not in DB
- API response must be structured JSON, not raw text

**Explicit non-goals:**
- Exhaustive real-time market data (a few dozen well-sourced records per sector is fine)
- Production-grade auth, rate limiting, or multi-user session management
- Stock price prediction or trading signals

---

## Tech Stack Decisions

| Layer | Choice | Rationale |
|-------|--------|-----------|
| LLM | OpenAI GPT-4o (or Claude via Anthropic) | Strong function-calling / tool use |
| Agent Framework | Raw LLM API + tool loop (no LangChain) | Shows understanding; less magic |
| MCP Server | `mcp` Python SDK (stdio transport) | Matches spec intent; simplest locally |
| Database | SQLite | Spec says it's fine; zero infra overhead |
| REST API | FastAPI + Uvicorn | Async, fast, auto-generates OpenAPI docs |
| UI | Streamlit | Spec recommends it; fast to build |
| Data Scraping | `yfinance`, `requests`, manual CSVs | Reliable public financial data |
| Dependency Mgmt | `uv` or `pip` + `requirements.txt` | |
| Python version | 3.11+ | |

---

## Architecture Design

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
│              Agent Core (agent.py)               │
│  • Receives: query + persona + sector            │
│  • Builds system prompt from persona config      │
│  • Runs tool-calling LLM loop                    │
│  • Returns: structured AgentResponse             │
└────────────────────┬────────────────────────────┘
                     │ MCP tool calls (JSON-RPC)
                     ▼
┌─────────────────────────────────────────────────┐
│            MCP Server (mcp_server.py)            │
│  Tools exposed:                                  │
│  • query_companies(sector, filters?)             │
│  • get_company_detail(company_name, sector)      │
│  • get_sector_summary(sector)                    │
│  • search_companies(query, sector)               │
└────────────────────┬────────────────────────────┘
                     │ SQLite queries
                     ▼
┌─────────────────────────────────────────────────┐
│              SQLite Database (db/)               │
│  companies table + financials table              │
│  + sector_meta table + news_signals table        │
└─────────────────────────────────────────────────┘
```

---

## Database Schema

### `companies` table
```sql
CREATE TABLE companies (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    ticker          TEXT,
    sector          TEXT NOT NULL,   -- 'tech' | 'retail' | 'manufacturing'
    description     TEXT,
    market_cap_bn   REAL,            -- USD billions
    employees       INTEGER,
    headquarters    TEXT,
    founded_year    INTEGER,
    source_url      TEXT,
    last_updated    TEXT             -- ISO date
);
```

### `financials` table
```sql
CREATE TABLE financials (
    id              INTEGER PRIMARY KEY,
    company_id      INTEGER REFERENCES companies(id),
    fiscal_year     INTEGER,
    revenue_bn      REAL,
    ebitda_bn       REAL,
    net_income_bn   REAL,
    ebitda_margin   REAL,           -- percentage
    pe_ratio        REAL,
    ev_ebitda       REAL,
    debt_equity     REAL,
    roe             REAL,
    revenue_growth  REAL            -- YoY %
);
```

### `sector_meta` table
```sql
CREATE TABLE sector_meta (
    sector          TEXT PRIMARY KEY,
    description     TEXT,
    benchmark_index TEXT,           -- e.g. "NASDAQ-100" for tech
    avg_pe          REAL,
    notes           TEXT
);
```

### `news_signals` table
```sql
CREATE TABLE news_signals (
    id              INTEGER PRIMARY KEY,
    company_id      INTEGER REFERENCES companies(id),
    signal_type     TEXT,           -- 'hiring' | 'layoff' | 'expansion' | 'earnings'
    headline        TEXT,
    date            TEXT,
    source_url      TEXT
);
```

---

## MCP Server Design

**Transport:** stdio (subprocess-based) — agent spawns MCP server as a child process and communicates via stdin/stdout JSON-RPC 2.0.

### Tools Exposed

| Tool Name | Parameters | Returns |
|-----------|-----------|---------|
| `list_companies` | `sector: str` | List of companies with basic info |
| `get_company_financials` | `company_name: str, sector: str` | Full financials for a company |
| `get_sector_summary` | `sector: str` | Sector-level aggregates + benchmark |
| `search_companies` | `query: str, sector: str` | Fuzzy-match companies by name |
| `get_news_signals` | `company_name: str` | Recent hiring/earnings signals |

**Why stdio over HTTP?** Simpler local setup, no port management, and it's the canonical MCP transport. HTTP can be added later.

---

## Persona System Design

Each persona is a config object that injects:
1. A **role-specific system prompt prefix** that defines the analyst's lens, priorities, and communication style
2. A **reasoning framework** embedded in the prompt (e.g. PE lens = EBITDA multiples, leverage, exit timelines)
3. **Output formatting preferences** (e.g. MF Analyst references benchmark weights; PE Analyst talks exit scenarios)

```python
PERSONAS = {
    "mutual_fund_analyst": {
        "name": "Mutual Fund Analyst",
        "system_prompt": """You are a long-only mutual fund analyst focused on benchmark-relative performance.
Your lens: sustainable growth, valuation vs. index (benchmark: {benchmark}), portfolio fit, and risk-adjusted returns.
Reason through: index weight, relative P/E vs. sector average, revenue growth durability, moat strength.
Avoid: leverage-heavy scenarios, short-term trading ideas, or private-market framing.""",
        "output_emphasis": ["benchmark_comparison", "growth_durability", "valuation_vs_index"]
    },
    "equity_analyst": {
        "name": "Equity Analyst",
        "system_prompt": """You are a sell-side equity analyst focused on fundamental analysis.
Your lens: earnings quality, margin trajectory, competitive positioning, and price targets.
Reason through: EPS trends, EBITDA margins, industry position, P/E vs. peers, and forward estimates.
Avoid: portfolio construction framing or PE deal mechanics.""",
        "output_emphasis": ["earnings_trends", "margin_analysis", "valuation_multiples"]
    },
    "pe_analyst": {
        "name": "PE Analyst",
        "system_prompt": """You are a private equity analyst focused on deal mechanics and operational value creation.
Your lens: buyout feasibility, leverage capacity (Debt/EBITDA), operational improvement levers, and exit multiples.
Reason through: free cash flow, EBITDA margin expansion potential, EV/EBITDA entry vs. exit, IRR scenarios.
Avoid: public-market benchmarking or long-only portfolio framing.""",
        "output_emphasis": ["leverage_capacity", "operational_levers", "exit_scenarios"]
    }
}
```

---

## Agent Response Schema (API)

```json
{
  "query": "Which companies look like attractive buyout targets?",
  "persona": "pe_analyst",
  "sector": "logistics",
  "answer": "Based on the data in the database, ...",
  "companies_referenced": ["Company A", "Company B"],
  "data_sources": ["financials_2023", "news_signals_2024"],
  "confidence": "high",
  "reasoning_lens": "PE buyout analysis: leverage capacity, EBITDA margins, exit multiples",
  "caveats": "Data sourced from public filings as of Q3 2024. Not investment advice."
}
```

---

## Project Structure

```
configureable-agent/
├── README.md
├── .env.example
├── requirements.txt
│
├── db/
│   ├── schema.sql              # DDL for all tables
│   ├── seed_data/
│   │   ├── {tech,retail,manufacturing}_companies.csv
│   │   ├── {tech,retail,manufacturing}_financials.csv
│   │   └── {tech,retail,manufacturing}_news.csv
│   ├── build_db.py             # Script to create + populate SQLite from CSVs
│   └── financial_agent.db     # The SQLite file (committed as sample)
│
├── mcp_server/
│   ├── __init__.py
│   ├── server.py               # MCP stdio server, exposes all tools
│   └── db_queries.py           # Raw SQLite query functions (used only by MCP server)
│
├── agent/
│   ├── __init__.py
│   ├── agent.py                # Core agent loop (LLM + MCP tool calls)
│   ├── personas.py             # PERSONAS config dict
│   ├── mcp_client.py           # Subprocess MCP client (spawns server, sends JSON-RPC)
│   └── schemas.py              # Pydantic models for AgentResponse
│
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI app with POST /query endpoint
│
├── ui/
│   └── streamlit_app.py        # Streamlit chat interface
│
└── docs/
    └── schema_decisions.md     # Data sourcing notes, caveats
```

---

## Build Phases

### Phase 1: Database + Data (Day 1 — ~3 hrs)
- [ ] Design and create `schema.sql`
- [ ] Research and compile data for Tech sector (10-15 companies)
- [ ] Research and compile data for Retail sector (10-15 companies)
- [ ] Research and compile data for Manufacturing sector (10-15 companies)
- [ ] Write `build_db.py` to load CSVs into SQLite
- [ ] Verify all 4 tables populated correctly
- [ ] Write `docs/schema_decisions.md`

### Phase 2: MCP Server (Day 1–2 — ~3 hrs)
- [ ] Set up `mcp` Python SDK
- [ ] Implement `mcp_server/db_queries.py` (pure SQLite functions)
- [ ] Implement `mcp_server/server.py` with all 5 tools exposed via MCP
- [ ] Test each tool manually (stdin/stdout JSON-RPC calls)
- [ ] Implement `agent/mcp_client.py` to spawn server and call tools

### Phase 3: Agent Core (Day 2 — ~4 hrs)
- [ ] Implement `agent/personas.py` with all 3 persona configs
- [ ] Implement `agent/schemas.py` (Pydantic AgentResponse model)
- [ ] Implement `agent/agent.py` — LLM tool-calling loop with:
  - System prompt assembly (persona + sector injected)
  - MCP tool call dispatch
  - Out-of-scope company detection
  - Structured response assembly
- [ ] Write persona differentiation tests (same question, all 3 personas)

### Phase 4: REST API (Day 2–3 — ~2 hrs)
- [ ] Implement `api/main.py` with FastAPI
- [ ] POST `/query` endpoint accepting `{query, persona, sector}`
- [ ] Returns structured `AgentResponse` JSON
- [ ] Add basic input validation + error handling
- [ ] Test with `curl` / httpx

### Phase 5: Streamlit UI (Day 3 — ~2 hrs)
- [ ] Implement `ui/streamlit_app.py`
- [ ] Persona selector (dropdown) + sector selector (dropdown)
- [ ] Chat history display
- [ ] Calls same agent core as API
- [ ] Show companies referenced + caveats in UI

### Phase 6: Polish + README (Day 3 — ~2 hrs)
- [ ] Write README (setup, schema decisions, MCP design, one thing to improve)
- [ ] Create `.env.example`
- [ ] Ensure `build_db.py` is a clean reproducible script
- [ ] Run all sample queries from JD spec and verify differentiation
- [ ] Optional: Loom recording

---

## Decision Log

| # | Decision | Alternatives | Rationale |
|---|----------|-------------|-----------|
| 1 | stdio MCP transport | HTTP/SSE | Simpler local setup; closest to spec intent |
| 2 | Raw LLM API (no LangChain) | LangChain, LlamaIndex | Demonstrates understanding of agent loops; less "magic" |
| 3 | FastAPI for REST | Flask, Django | Async, Pydantic-native, auto-generates OpenAPI spec |
| 4 | Tech + Retail + Manufacturing | Any 3 sectors | Good diversity; public data abundant for all three |
| 5 | SQLite as DB | PostgreSQL, DuckDB | Spec explicitly allows it; zero infra overhead |
| 6 | OpenAI GPT-4o as LLM | Anthropic Claude, Gemini | Best function-calling performance; widely known |
| 7 | Pydantic for response schema | Dataclasses, dict | Type safety; FastAPI native; grader-friendly |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| MCP stdio process hangs | Add timeout + subprocess kill on error |
| LLM hallucinates DB facts | System prompt explicitly instructs: "Only state facts from tool call results. If a company is not in the DB, say so." |
| Persona differentiation is cosmetic | Test all 3 personas on identical questions before submission; tune prompts |
| Data quality gaps | Document all caveats in README + DB `notes` field |
| API returns non-JSON-parseable response | Pydantic validation at API layer; fallback error schema |

---

## Verification Plan

**Before submission, run all JD sample queries:**
1. ✅ PE Analyst + Logistics: "Which companies look like attractive buyout targets?"
2. ✅ Tech sector, all 3 personas: "Is this sector a good place to put money to work?"
3. ✅ MF Analyst + Retail: "Core holding vs. name to avoid?"
4. ✅ Equity + Manufacturing: "Walk me through the margin profile"
5. ✅ PE + Tech: "Which one company to take private?"
6. ✅ Data grounding: "Most recent headcount/hiring signal for [company]?" → must show real DB lookup
7. ✅ Out-of-scope: Ask about a company NOT in DB → must get honest refusal
8. ✅ API test: POST with equity_analyst + logistics → structured JSON with `companies_referenced`

---

## Open Questions for User

> Please confirm or correct before I proceed to implementation:

1. **LLM provider preference:** OpenAI GPT-4o, Anthropic Claude, or Gemini? *(Default: OpenAI GPT-4o)*
2. **Sector preference:** Tech, Retail, Manufacturing confirmed? Or swap one for Logistics?
3. **MCP transport:** stdio (subprocess) confirmed? Or prefer HTTP/SSE for easier debugging?
4. **Python version:** 3.11+ is fine?
5. **Any existing API keys** already set up in the project? (`.env` approach confirmed)
