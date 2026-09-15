"""
agent.py — Core agent loop for the Configurable Financial Agent.

Flow:
  1. Build system prompt from persona + sector context (fetched via MCP)
  2. Run OpenAI tool-calling loop (model decides which MCP tools to call)
  3. Execute each tool call through MCP client (the protocol boundary)
  4. Feed results back to model until it produces a final answer
  5. Parse and return structured AgentResponse

This file contains NO direct DB access — all data comes through MCP.
"""

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from agent.mcp_client import call_tools_batch_sync, call_tool_sync
from agent.personas import PERSONAS, build_system_prompt, get_persona
from agent.schemas import AgentResponse, QueryRequest, ToolCall

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Grok (xAI) client — OpenAI-compatible endpoint
# ─────────────────────────────────────────────────────────────
# LLM client — Poolside (Primary) with Groq (Secondary) fallback
# ─────────────────────────────────────────────────────────────
def get_llm_config() -> tuple[OpenAI, str]:
    # ponytail: Poolside & Groq both speak OpenAI JSON-RPC; prioritize Poolside, fallback to Groq
    load_dotenv(override=True)

    # 1. Primary: Poolside
    if os.getenv("POOLSIDE_API_KEY"):
        api_key = os.environ["POOLSIDE_API_KEY"]
        base_url = os.getenv("POOLSIDE_BASE_URL", "https://api.poolside.ai/v1")
        model = os.getenv("POOLSIDE_MODEL", "poolside")
        return OpenAI(api_key=api_key, base_url=base_url), model

    # 2. Secondary: Groq
    if os.getenv("GROQ_API_KEY"):
        api_key = os.environ["GROQ_API_KEY"]
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return OpenAI(api_key=api_key, base_url=base_url), model

    # 3. Fallbacks: xAI / OpenAI
    api_key = os.getenv("XAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No API key found. Please set POOLSIDE_API_KEY or GROQ_API_KEY in your .env file.")

    base_url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1") if os.getenv("XAI_API_KEY") else None
    model = os.getenv("XAI_MODEL", "grok-beta") if os.getenv("XAI_API_KEY") else os.getenv("OPENAI_MODEL", "gpt-4o")
    return OpenAI(api_key=api_key, base_url=base_url), model

MAX_TOOL_ROUNDS = 6  # prevent infinite loops

# ─────────────────────────────────────────────────────────────
# Tool schema exposed to the LLM (mirrors MCP tools)
# ─────────────────────────────────────────────────────────────

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sector_summary",
            "description": (
                "Returns high-level metadata and aggregate statistics for a sector. "
                "Call this first to understand the sector context."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                    }
                },
                "required": ["sector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_companies",
            "description": (
                "Returns all companies in a sector with latest financial metrics. "
                "Use to survey the full landscape before focusing on specific companies."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                    }
                },
                "required": ["sector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_financials",
            "description": (
                "Returns full financial history and recent news for a specific company. "
                "If company not found, the result will clearly say so — "
                "you MUST relay this honestly rather than fabricating data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                    },
                },
                "required": ["company_name", "sector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_companies",
            "description": "Fuzzy-searches companies by partial name or ticker in a sector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                    },
                },
                "required": ["query", "sector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_signals",
            "description": (
                "Returns recent news signals (hiring, layoffs, earnings beats/misses, "
                "expansions) for a specific company. Use for headcount or momentum questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string"},
                    "sector": {
                        "type": "string",
                        "enum": ["tech", "retail", "manufacturing"],
                    },
                },
                "required": ["company_name"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────
# Tool execution via MCP
# ─────────────────────────────────────────────────────────────

def execute_tool_calls(
    tool_calls: list[Any],
) -> tuple[list[dict], list[ToolCall]]:
    """
    Execute a batch of OpenAI tool calls through the MCP client.
    Returns (openai_tool_messages, ToolCall records for audit log).
    """
    # Build batch for efficient single-session MCP call
    batch = [(tc.function.name, json.loads(tc.function.arguments)) for tc in tool_calls]
    results = call_tools_batch_sync(batch)

    openai_messages = []
    audit_log = []

    for tc, (tool_name, arguments), result in zip(tool_calls, batch, results):
        result_text = json.dumps(result, indent=2)

        openai_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result_text,
        })

        # Brief result summary for audit log
        if isinstance(result, dict) and "error" in result:
            summary = f"Error: {result['error']}"
        elif isinstance(result, list):
            summary = f"Returned {len(result)} items"
        elif isinstance(result, dict):
            summary = f"OK — keys: {list(result.keys())[:5]}"
        else:
            summary = "OK"

        audit_log.append(ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result_summary=summary,
        ))

    return openai_messages, audit_log


# ─────────────────────────────────────────────────────────────
# Post-processing helpers
# ─────────────────────────────────────────────────────────────

def extract_companies_referenced(answer: str, companies: list[dict]) -> list[str]:
    """Find which company names from the DB appear in the answer text."""
    referenced = []
    answer_lower = answer.lower()
    for company in companies:
        name = company.get("name", "")
        ticker = company.get("ticker", "")
        if name and name.lower() in answer_lower:
            referenced.append(name)
        elif ticker and ticker.lower() in answer_lower:
            referenced.append(name or ticker)
    return list(dict.fromkeys(referenced))  # deduplicate, preserve order


def assess_confidence(tool_calls_made: list[ToolCall], answer: str) -> str:
    """Heuristically assess confidence based on data retrieved."""
    if not tool_calls_made:
        return "low"
    tool_names = {tc.tool_name for tc in tool_calls_made}
    has_company_data = "get_company_financials" in tool_names or "list_companies" in tool_names
    has_sector_data = "get_sector_summary" in tool_names
    if has_company_data and has_sector_data:
        return "high"
    if has_company_data or has_sector_data:
        return "medium"
    return "low"


def build_reasoning_lens(persona_id: str, sector: str) -> str:
    """Build a one-line description of the reasoning lens applied."""
    lens_map = {
        "mutual_fund_analyst": f"MF long-only lens: benchmark-relative valuation, growth durability, portfolio fit ({sector})",
        "equity_analyst": f"Equity fundamental lens: earnings trends, margin trajectory, valuation multiples ({sector})",
        "pe_analyst": f"PE deal lens: leverage capacity, EBITDA improvement potential, EV/EBITDA entry/exit scenarios ({sector})",
    }
    return lens_map.get(persona_id, f"{persona_id} lens on {sector}")


# ─────────────────────────────────────────────────────────────
# Main agent entry point
# ─────────────────────────────────────────────────────────────

def run_agent(request: QueryRequest) -> AgentResponse:
    """
    Run the full agent loop for a given query + persona + sector.
    Returns a structured AgentResponse.
    """
    persona_config = get_persona(request.persona)

    # Step 1: Fetch sector metadata via MCP to inject into system prompt
    sector_meta = call_tool_sync("get_sector_summary", {"sector": request.sector})
    system_prompt = build_system_prompt(request.persona, request.sector, sector_meta)

    # Step 2: Initialize conversation
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.query},
    ]

    all_tool_calls_made: list[ToolCall] = []
    companies_in_sector: list[dict] = []
    llm_client, model_name = get_llm_config()

    # Step 3: Tool-calling loop
    for round_num in range(MAX_TOOL_ROUNDS):
        # ponytail: force tool call on round 0 to guarantee grounding; auto thereafter
        choice = "required" if round_num == 0 else "auto"
        try:
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice=choice,
            )
        except Exception:
            response = llm_client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=OPENAI_TOOLS,
                tool_choice="auto",
            )

        message = response.choices[0].message

        # If the model called tools, execute them via MCP
        if message.tool_calls:
            messages.append(message)  # add assistant message with tool_calls

            tool_messages, audit_entries = execute_tool_calls(message.tool_calls)
            messages.extend(tool_messages)
            all_tool_calls_made.extend(audit_entries)

            # Cache company list if we fetched it (for post-processing)
            for tc in message.tool_calls:
                if tc.function.name == "list_companies":
                    for tm in tool_messages:
                        if tm.get("tool_call_id") == tc.id:
                            try:
                                companies_in_sector = json.loads(tm["content"])
                            except Exception:
                                pass

        else:
            # Model gave a final answer — exit loop
            final_answer = message.content or ""
            break
    else:
        # Fallback if we hit MAX_TOOL_ROUNDS
        final_answer = (
            "I retrieved data from the database but ran into a processing issue. "
            "Please try rephrasing your question."
        )

    # Step 4: Assemble structured response
    referenced = extract_companies_referenced(final_answer, companies_in_sector)
    confidence = assess_confidence(all_tool_calls_made, final_answer)
    reasoning_lens = build_reasoning_lens(request.persona, request.sector)

    data_note = ""
    if not all_tool_calls_made:
        data_note = "Warning: no DB tool calls were made. Answer may not be grounded in database data."

    return AgentResponse(
        query=request.query,
        persona=request.persona,
        persona_display=persona_config["name"],
        sector=request.sector,
        sector_display=sector_meta.get("display_name", request.sector.title()),
        answer=final_answer,
        reasoning_lens=reasoning_lens,
        companies_referenced=referenced,
        tool_calls_made=all_tool_calls_made,
        confidence=confidence,
        data_coverage_note=data_note,
    )
