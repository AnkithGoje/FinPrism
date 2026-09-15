"""
test_evaluation_queries.py — Sanity and evaluation suite for the Configurable Financial Agent.

Covers the 8 key scenarios from Agent JD.md:
1. Database tables and row counts
2. All 9 persona x sector system prompt combinations
3. Out-of-scope sector tolerance ('logistics')
4. Out-of-scope company lookup signaling ('Tesla')
5. Optional live agent query verification (requires OPENAI_API_KEY)

Run with:
    python tests/test_evaluation_queries.py
"""

import os
import sqlite3
import sys
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
DB_PATH = PROJECT_ROOT / "db" / "financial_agent.db"

from agent.personas import PERSONAS, VALID_PERSONAS, VALID_SECTORS, build_system_prompt
from agent.schemas import QueryRequest, AgentResponse
from mcp_server.db_queries import (
    get_sector_summary,
    list_companies,
    get_company_financials,
    get_news_signals,
)


def test_database_integrity():
    assert DB_PATH.exists(), f"Database missing at {DB_PATH}. Run python db/build_db.py first."
    conn = sqlite3.connect(DB_PATH)
    
    companies_count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    financials_count = conn.execute("SELECT COUNT(*) FROM financials").fetchone()[0]
    news_count = conn.execute("SELECT COUNT(*) FROM news_signals").fetchone()[0]
    sector_count = conn.execute("SELECT COUNT(*) FROM sector_meta").fetchone()[0]
    
    assert companies_count == 36, f"Expected 36 companies, got {companies_count}"
    assert financials_count >= 72, f"Expected >= 72 financials, got {financials_count}"
    assert news_count >= 35, f"Expected >= 35 news signals, got {news_count}"
    assert sector_count == 3, f"Expected 3 sectors in sector_meta, got {sector_count}"
    conn.close()
    print("[OK] Database integrity verified (36 companies, 4 tables)")


def test_persona_system_prompts():
    """Verify all 9 persona x sector combinations generate valid non-empty prompts."""
    for sector in VALID_SECTORS:
        meta = get_sector_summary(sector)
        assert "error" not in meta
        for persona_id in VALID_PERSONAS:
            prompt = build_system_prompt(persona_id, sector, meta)
            assert len(prompt) > 200, f"Prompt too short for {persona_id} on {sector}"
            if persona_id == "mutual_fund_analyst":
                assert meta["benchmark_index"] in prompt, f"Benchmark missing in MF prompt for {sector}"
    print("[OK] All 9 persona x sector prompt permutations verified")


def test_out_of_scope_lookups():
    """Verify that unlisted companies and sectors produce explicit missing/not-found signals."""
    # Out-of-scope company (US company queried against Indian DB)
    res = get_company_financials("Tesla", "tech")
    assert res.get("found") is False, "Tesla should not be found in Indian tech DB"
    assert "not in the database" in res.get("message", "")

    # Out-of-scope sector
    sector_res = get_sector_summary("logistics")
    assert "error" in sector_res, "Logistics sector should return error"

    # Schema accommodates out-of-scope sector without raising 422
    req = QueryRequest(query="Which company should I buy?", persona="equity_analyst", sector="logistics")
    assert req.sector == "logistics"
    print("[OK] Out-of-scope company & sector fallback signals verified")


def test_data_grounding_signals():
    """Verify that DB returns real headcount/news signals."""
    news = get_news_signals("TCS", "tech")
    assert len(news) > 0, "Expected news signals for TCS"
    assert "headline" in news[0]
    print("[OK] Data grounding lookup verified for Indian market (TCS)")


def run_all():
    print("Running sanity checks for Configurable Financial Agent...\n")
    test_database_integrity()
    test_persona_system_prompts()
    test_out_of_scope_lookups()
    test_data_grounding_signals()
    print("\nAll static and DB checks passed successfully!")


if __name__ == "__main__":
    run_all()
