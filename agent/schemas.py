"""
schemas.py — Pydantic models for request and response validation.
Used by both the FastAPI layer and the agent core.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., description="The natural language question to ask the agent.", min_length=5)
    persona: Literal["mutual_fund_analyst", "equity_analyst", "pe_analyst"] = Field(
        ..., description="The analyst persona to use."
    )
    # ponytail: accept str so out-of-scope sector queries get an honest structured response instead of a raw 422
    sector: str = Field(
        ..., description="The sector to analyze (e.g. 'tech', 'retail', 'manufacturing')."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Which companies look like attractive buyout targets based on the data you have?",
                "persona": "pe_analyst",
                "sector": "manufacturing",
            }
        }


# ─────────────────────────────────────────────────────────────
# Response models
# ─────────────────────────────────────────────────────────────

class ToolCall(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    result_summary: str  # brief summary of what the tool returned


class AgentResponse(BaseModel):
    query: str = Field(..., description="The original query.")
    persona: str = Field(..., description="Persona ID used.")
    persona_display: str = Field(..., description="Human-readable persona name.")
    sector: str = Field(..., description="Sector ID used.")
    sector_display: str = Field(..., description="Human-readable sector name.")

    answer: str = Field(..., description="The agent's full analytical answer.")
    reasoning_lens: str = Field(
        ..., description="One-line summary of the reasoning framework applied."
    )

    companies_referenced: list[str] = Field(
        default_factory=list,
        description="Names of companies explicitly referenced in the answer.",
    )
    tool_calls_made: list[ToolCall] = Field(
        default_factory=list,
        description="MCP tool calls made during reasoning (for transparency).",
    )

    confidence: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Agent's self-assessed confidence based on data availability.",
    )
    data_coverage_note: str = Field(
        default="",
        description="Any caveats about data completeness or freshness.",
    )
    caveats: str = Field(
        default="Data sourced from public filings and news as of mid-2024. Not investment advice.",
        description="Standard disclaimer.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Which companies look like attractive buyout targets?",
                "persona": "pe_analyst",
                "persona_display": "PE Analyst",
                "sector": "manufacturing",
                "sector_display": "Manufacturing",
                "answer": "Based on the database, Cummins Inc (CMI) stands out...",
                "reasoning_lens": "PE buyout: leverage capacity, EBITDA margins, EV/EBITDA entry, exit scenarios",
                "companies_referenced": ["Cummins Inc", "Rockwell Automation", "Nucor Corporation"],
                "tool_calls_made": [],
                "confidence": "high",
                "data_coverage_note": "Financials through FY2024 for most companies.",
                "caveats": "Data sourced from public filings. Not investment advice.",
            }
        }


class ErrorResponse(BaseModel):
    error: str
    detail: str = ""
    persona: str = ""
    sector: str = ""
