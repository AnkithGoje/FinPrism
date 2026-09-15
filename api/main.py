"""
main.py — FastAPI REST endpoint for the Configurable Financial Agent.

Endpoints:
  POST /query          — Main agent query endpoint
  GET  /health         — Health check
  GET  /personas       — List available personas
  GET  /sectors        — List available sectors

Run with:
    uvicorn api.main:app --reload --port 8000
"""

import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from agent.agent import run_agent
from agent.personas import PERSONAS, VALID_PERSONAS, VALID_SECTORS
from agent.schemas import AgentResponse, ErrorResponse, QueryRequest

# ─────────────────────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="FinPrism: Persona-Configurable Financial Agent API",
    description=(
        "FinPrism is a persona-configurable financial analyst agent with MCP-backed DB access. "
        "Supports Mutual Fund Analyst, Equity Analyst, and PE Analyst personas "
        "across Tech, Retail, and Manufacturing sectors."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Middleware — request timing
# ─────────────────────────────────────────────────────────────

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round(time.time() - start, 3)
    response.headers["X-Process-Time"] = str(elapsed)
    return response


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    # ponytail: automatically forward browser visits from root to interactive OpenAPI docs
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "finprism-api"}


@app.get("/personas", tags=["meta"])
async def list_personas() -> dict[str, Any]:
    """List all available analyst personas."""
    return {
        "personas": [
            {
                "id": pid,
                "name": config["name"],
                "short_name": config["short_name"],
                "output_emphasis": config["output_emphasis"],
            }
            for pid, config in PERSONAS.items()
        ]
    }


@app.get("/sectors", tags=["meta"])
async def list_sectors() -> dict[str, Any]:
    """List available sectors."""
    return {
        "sectors": [
            {"id": s, "display_name": s.title()} for s in VALID_SECTORS
        ]
    }


@app.post(
    "/query",
    response_model=AgentResponse,
    responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    tags=["agent"],
    summary="Query the financial agent",
    description=(
        "Submit a natural language question with a persona and sector. "
        "The agent will query the database via MCP and return a structured "
        "analytical response grounded in the actual data."
    ),
)
# ponytail: sync def runs in threadpool; keeps event loop unblocked
def query_agent(request: QueryRequest) -> AgentResponse:
    """
    Main agent endpoint.

    Example request body:
    ```json
    {
      "query": "Which companies look like attractive buyout targets?",
      "persona": "pe_analyst",
      "sector": "manufacturing"
    }
    ```
    """
    try:
        result = run_agent(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}. Check that the database has been built (python db/build_db.py).",
        )


# ─────────────────────────────────────────────────────────────
# Entry point for direct run
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
