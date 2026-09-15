# Schema Decisions & Data Sourcing Notes

## Schema Design

### Why 4 tables?

| Table | Purpose | Design Decision |
|-------|---------|-----------------|
| `companies` | One row per company, static attributes | Normalized to avoid repeating company metadata in every financial row |
| `financials` | One row per company per fiscal year | Allows multi-year trend analysis (margin improvement, growth trajectory) |
| `sector_meta` | Sector-level benchmark context | Injected into system prompt to give the LLM benchmark reference points without hardcoding |
| `news_signals` | Recent events: hiring, layoffs, earnings beats/misses | Covers "headcount stress test" queries and momentum signals |

### Key Schema Decisions

**Nullable financials with -1 as P/E sentinel:** Unprofitable companies (negative earnings) are stored with `pe_ratio = -1.0` to distinguish "no meaningful P/E" from missing data. The agent is instructed to interpret this correctly.

**Sector enum at DB level:** SQLite CHECK constraint enforces `sector IN ('tech','retail','manufacturing')` at the DB layer — prevents silent data corruption if the seed script is modified.

**Ticker as secondary key:** Companies are primarily looked up by fuzzy name match (`LIKE`), not ticker, because the agent receives natural language queries. Ticker is stored for cross-referencing and display.

**No time-series granularity below annual:** Quarterly data would add value but requires significantly more sourcing effort and storage. Annual FY data is sufficient for strategic analysis (the use case here).

---

## Data Sourcing (Indian Equities — NSE/BSE)

### Tech Sector (12 Indian IT Companies)
- **Sources:** Annual Reports, Investor Presentations, BSE/NSE filings, and Screener.in for TCS, Infosys, HCLTech, Wipro, Tech Mahindra, LTIMindtree, Persistent Systems, Coforge, Mphasis, Tata Elxsi, KPIT Technologies, Zensar Technologies.
- **Fiscal years:** FY2023 and FY2024 (Indian fiscal years ending March 31).
- **Known caveats:**
  - Tech Mahindra FY24 margins contracted significantly (~11.9%) due to telecom client weakness and restructuring provisions under project Fortius.
  - Mid-cap ER&D leaders (KPIT, Persistent, Tata Elxsi) trade at sharp valuation multiples (50x–70x P/E) reflecting autonomous and EV software growth premiums relative to legacy tier-1 IT firms (~25x–32x).

### Retail Sector (12 Indian Retail Companies)
- **Sources:** Company Annual Reports, BSE/NSE investor disclosures, and corporate presentations for DMart, Trent, Titan, Reliance Retail, ABFRL, Shoppers Stop, V-Mart, Metro Brands, Vedant Fashions, Nykaa, Devyani International, Spencer's.
- **Fiscal years:** FY2023 and FY2024.
- **Known caveats:**
  - Reliance Retail Ventures numbers reflect the standalone retail business proxy within consolidated Reliance Industries (RIL) filings.
  - Aditya Birla Fashion (ABFRL), Shoppers Stop, V-Mart, and Spencer's recorded negative net income in FY24, reflected via `pe_ratio = -1.0`.
  - Trent shows exceptionally high P/E multiples (~170x) driven by 50%+ YoY revenue growth from the Zudio format expansion.

### Manufacturing Sector (12 Indian Industrials & Auto Companies)
- **Sources:** Annual Reports and BSE/NSE filings for Larsen & Toubro, Tata Motors, M&M, BEL, HAL, Cummins India, Siemens India, ABB India, Bharat Forge, Thermax, Dixon Technologies, AIA Engineering.
- **Fiscal years:** FY2023 and FY2024.
- **Known caveats:**
  - Siemens India follows an October–September fiscal year ending in September; figures are mapped to the prevailing fiscal year convention.
  - Tata Motors figures include consolidated global results from Jaguar Land Rover (JLR); net debt was substantially reduced in FY24 due to record Defender/Range Rover operating cash flow.
  - Defense PSUs (HAL, BEL) operate with virtually zero long-term debt (`debt_equity ~0.00`) and elevated advance payment balances from the Ministry of Defence.

---

## MCP Design Decisions

### Why stdio transport?
The MCP spec supports multiple transports (stdio, HTTP/SSE). We chose stdio (subprocess) because:
1. **True protocol boundary:** The agent process and the DB server are separate OS processes — there is no way to "cheat" by calling DB functions directly
2. **Zero infrastructure:** No port management, no HTTP server to start separately
3. **Canonical MCP pattern:** This is the recommended transport for local tool servers in the MCP reference implementation

### Why 5 tools instead of 1 generic SQL tool?
A single `execute_sql(query)` tool would technically work but:
- Creates SQL injection risk if the LLM generates malicious queries
- Gives no guardrails on what data the model can access
- Provides no semantic hints to the model about intended usage

Our 5 tools (`get_sector_summary`, `list_companies`, `get_company_financials`, `search_companies`, `get_news_signals`) each have a specific, semantically named purpose that guides the model toward correct usage patterns.

---

## What I'd Improve With More Time

1. **Real-time data integration:** Connect to a financial data API (Polygon.io, Yahoo Finance API, or SEC EDGAR XBRL) to auto-refresh the DB with live financials rather than static CSVs

2. **Quarterly granularity:** Expand the schema to store quarterly financials, enabling momentum analysis ("Q/Q margin improvement") and earnings beat/miss context

3. **Multi-turn conversation memory:** The current agent is stateless (each call is independent). Adding a conversation ID + message history would allow follow-up questions like "compare that to the second company you mentioned"

4. **Confidence calibration via RAG:** Store the raw source documents (10-K text, earnings call transcripts) in a vector store and have the agent cite specific passages, reducing hallucination risk and improving verifiability

5. **Structured persona output validation:** Add a post-processing step that checks whether the answer contains persona-specific language (e.g., PE Analyst answers should mention leverage capacity), auto-retrying if a persona check fails
