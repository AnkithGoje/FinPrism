"""
db_queries.py — Raw SQLite query functions used exclusively by the MCP server.
These functions MUST NOT be imported anywhere else (agent, API, UI).
The MCP protocol boundary enforces that all DB access goes through the server.
"""

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "db" / "financial_agent.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────────────────────
# Sector-level queries
# ─────────────────────────────────────────────────────────────

def get_sector_summary(sector: str) -> dict[str, Any]:
    """Return sector metadata + aggregate stats."""
    sector = sector.lower()
    with _get_conn() as conn:
        meta = conn.execute(
            "SELECT * FROM sector_meta WHERE sector = ?", (sector,)
        ).fetchone()

        if not meta:
            return {"error": f"Unknown sector: {sector}"}

        aggs = conn.execute(
            """
            SELECT
                COUNT(DISTINCT c.id)          AS company_count,
                AVG(f.revenue_bn)             AS avg_revenue_bn,
                AVG(f.ebitda_margin)          AS avg_ebitda_margin,
                AVG(f.pe_ratio)               AS avg_pe_ratio,
                AVG(f.ev_ebitda)              AS avg_ev_ebitda,
                AVG(f.revenue_growth)         AS avg_revenue_growth,
                AVG(f.debt_equity)            AS avg_debt_equity
            FROM companies c
            JOIN financials f ON f.company_id = c.id
            WHERE c.sector = ?
              AND f.fiscal_year = (SELECT MAX(fiscal_year) FROM financials WHERE company_id = c.id)
            """,
            (sector,),
        ).fetchone()

        return {
            "sector": sector,
            "display_name": meta["display_name"],
            "description": meta["description"],
            "benchmark_index": meta["benchmark_index"],
            "sector_avg_pe": meta["avg_pe"],
            "sector_avg_ev_ebitda": meta["avg_ev_ebitda"],
            "notes": meta["notes"],
            "aggregate_stats": {
                "company_count": aggs["company_count"],
                "avg_revenue_bn": round(aggs["avg_revenue_bn"] or 0, 2),
                "avg_ebitda_margin_pct": round(aggs["avg_ebitda_margin"] or 0, 1),
                "avg_pe_ratio": round(aggs["avg_pe_ratio"] or 0, 1),
                "avg_ev_ebitda": round(aggs["avg_ev_ebitda"] or 0, 1),
                "avg_revenue_growth_pct": round(aggs["avg_revenue_growth"] or 0, 1),
                "avg_debt_equity": round(aggs["avg_debt_equity"] or 0, 2),
            },
        }


# ─────────────────────────────────────────────────────────────
# Company listing
# ─────────────────────────────────────────────────────────────

def list_companies(sector: str) -> list[dict[str, Any]]:
    """Return all companies in a sector with latest financials summary."""
    sector = sector.lower()
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                c.id, c.name, c.ticker, c.market_cap_bn, c.employees,
                c.headquarters, c.description,
                f.fiscal_year, f.revenue_bn, f.ebitda_margin,
                f.pe_ratio, f.ev_ebitda, f.debt_equity,
                f.revenue_growth, f.net_income_bn, f.free_cash_flow_bn
            FROM companies c
            JOIN financials f ON f.company_id = c.id
            WHERE c.sector = ?
              AND f.fiscal_year = (SELECT MAX(fiscal_year) FROM financials WHERE company_id = c.id)
            ORDER BY c.market_cap_bn DESC NULLS LAST
            """,
            (sector,),
        ).fetchall()

        return [dict(row) for row in rows]


# ─────────────────────────────────────────────────────────────
# Company detail
# ─────────────────────────────────────────────────────────────

def get_company_financials(company_name: str, sector: str) -> dict[str, Any]:
    """Return full financial history for a specific company."""
    sector = sector.lower()
    with _get_conn() as conn:
        company = conn.execute(
            """
            SELECT * FROM companies
            WHERE sector = ?
              AND (LOWER(name) LIKE ? OR LOWER(ticker) = ?)
            LIMIT 1
            """,
            (sector, f"%{company_name.lower()}%", company_name.lower()),
        ).fetchone()

        if not company:
            return {
                "found": False,
                "company_name": company_name,
                "sector": sector,
                "message": (
                    f"No data found for '{company_name}' in the {sector} sector. "
                    "The agent should acknowledge this company is not in the database."
                ),
            }

        financials = conn.execute(
            """
            SELECT * FROM financials
            WHERE company_id = ?
            ORDER BY fiscal_year DESC
            """,
            (company["id"],),
        ).fetchall()

        news = conn.execute(
            """
            SELECT * FROM news_signals
            WHERE company_id = ?
            ORDER BY date DESC
            LIMIT 5
            """,
            (company["id"],),
        ).fetchall()

        return {
            "found": True,
            "company": dict(company),
            "financials": [dict(f) for f in financials],
            "recent_news": [dict(n) for n in news],
        }


# ─────────────────────────────────────────────────────────────
# Search / fuzzy lookup
# ─────────────────────────────────────────────────────────────

def search_companies(query: str, sector: str) -> list[dict[str, Any]]:
    """Fuzzy-search companies by name or ticker in a sector."""
    sector = sector.lower()
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, name, ticker, market_cap_bn, description
            FROM companies
            WHERE sector = ?
              AND (LOWER(name) LIKE ? OR LOWER(ticker) LIKE ?)
            ORDER BY market_cap_bn DESC NULLS LAST
            LIMIT 10
            """,
            (sector, f"%{query.lower()}%", f"%{query.lower()}%"),
        ).fetchall()

        return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────
# News signals
# ─────────────────────────────────────────────────────────────

def get_news_signals(company_name: str, sector: str | None = None) -> list[dict[str, Any]]:
    """Return recent news/hiring signals for a company."""
    with _get_conn() as conn:
        where_extra = "AND c.sector = ?" if sector else ""
        params: tuple = (
            (f"%{company_name.lower()}%", company_name.lower(), sector)
            if sector
            else (f"%{company_name.lower()}%", company_name.lower())
        )

        rows = conn.execute(
            f"""
            SELECT ns.signal_type, ns.headline, ns.summary, ns.date, ns.source_url,
                   c.name AS company_name, c.ticker
            FROM news_signals ns
            JOIN companies c ON c.id = ns.company_id
            WHERE (LOWER(c.name) LIKE ? OR LOWER(c.ticker) = ?)
              {where_extra}
            ORDER BY ns.date DESC
            LIMIT 10
            """,
            params,
        ).fetchall()

        return [dict(r) for r in rows]
