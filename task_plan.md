# Task Plan — Configurable Financial Agent

## Goal
Build a persona-configurable financial analyst agent with MCP tool protocol, SQLite DB, Streamlit UI, and FastAPI REST endpoint.

## Defaults (approved)
- LLM: OpenAI GPT-4o
- Sectors: Tech, Retail, Manufacturing
- MCP Transport: stdio subprocess
- Python: 3.11+

---

## Phase 1: Database + Data [ status: COMPLETE ✅ ]
- [x] Project folder structure
- [x] db/schema.sql — 4 tables with indexes
- [x] db/seed_data/tech_companies.csv + tech_financials.csv + tech_news.csv
- [x] db/seed_data/retail_companies.csv + retail_financials.csv + retail_news.csv
- [x] db/seed_data/manufacturing_companies.csv + manufacturing_financials.csv + manufacturing_news.csv
- [x] db/build_db.py — loads CSVs, verifies row counts
- [x] docs/schema_decisions.md

## Phase 2: MCP Server [ status: COMPLETE ✅ ]
- [x] mcp_server/__init__.py
- [x] mcp_server/db_queries.py — 5 query functions, sqlite3 only, no direct imports
- [x] mcp_server/server.py — MCP stdio server, 5 tools exposed
- [x] agent/mcp_client.py — subprocess MCP client, batch calls supported

## Phase 3: Agent Core [ status: COMPLETE ✅ ]
- [x] agent/__init__.py
- [x] agent/personas.py — 3 persona configs, build_system_prompt()
- [x] agent/schemas.py — QueryRequest, AgentResponse, ToolCall Pydantic models
- [x] agent/agent.py — full OpenAI tool-calling loop via MCP

## Phase 4: REST API [ status: COMPLETE ✅ ]
- [x] api/__init__.py
- [x] api/main.py — FastAPI with /query, /health, /personas, /sectors

## Phase 5: Streamlit UI [ status: COMPLETE ✅ ]
- [x] ui/streamlit_app.py — persona/sector selectors, chat, tool call transparency

## Phase 6: Polish [ status: COMPLETE ✅ ]
- [x] requirements.txt
- [x] .env.example
- [x] README.md — full setup, architecture, API docs, design notes

---

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| Terminal command denied | 1 | Writing files directly via write_to_file |
