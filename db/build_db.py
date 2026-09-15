"""
build_db.py — Creates and populates the financial_agent.db SQLite database
from the seed CSV files in db/seed_data/.

Run from the project root:
    python db/build_db.py
"""

import csv
import os
import sqlite3
from pathlib import Path

# Paths
DB_DIR = Path(__file__).parent
PROJECT_ROOT = DB_DIR.parent
DB_PATH = DB_DIR / "financial_agent.db"
SCHEMA_PATH = DB_DIR / "schema.sql"
SEED_DIR = DB_DIR / "seed_data"

SECTORS = ["tech", "retail", "manufacturing"]

SECTOR_META = {
    "tech": {
        "display_name": "Indian Information Technology",
        "description": (
            "Global IT export services, enterprise cloud transformation, engineering R&D (ER&D), and digital solutions. "
            "Characterized by high free cash flow conversion, net-cash balance sheets, and steady dividend payouts."
        ),
        "benchmark_index": "Nifty IT Index",
        "avg_pe": 28.5,
        "avg_ev_ebitda": 19.5,
        "notes": (
            "Sector navigating an enterprise spending pause in US/European BFSI while scaling GenAI delivery capabilities. "
            "Mid-tier ER&D and automotive engineering pure-plays trading at growth premiums over tier-1 legacy exporters."
        ),
    },
    "retail": {
        "display_name": "Indian Consumer Retail",
        "description": (
            "Organized modern grocery retail, branded value apparel, lifestyle jewelry, and omnichannel QSR chains. "
            "Benefiting from India's consumption formalization, rising disposable incomes, and tier-2/3 store expansions."
        ),
        "benchmark_index": "Nifty India Consumption Index",
        "avg_pe": 48.0,
        "avg_ev_ebitda": 26.0,
        "notes": (
            "Premium multiples sustained by multi-decade secular runway for organized penetration. "
            "Rapid expansion in value fast-fashion (Zudio) and organized bridal wear outpaces traditional department stores."
        ),
    },
    "manufacturing": {
        "display_name": "Indian Industrials & Manufacturing",
        "description": (
            "Heavy civil infrastructure (EPC), automotive OEMs, defense aerospace systems, power gensets, and electronics EMS. "
            "Key beneficiary of domestic public capex, PLI incentive schemes, and China+1 supply chain diversification."
        ),
        "benchmark_index": "Nifty India Manufacturing Index",
        "avg_pe": 34.0,
        "avg_ev_ebitda": 22.0,
        "notes": (
            "Record order backlogs in defense PSUs and capital goods. Heavy industrial automation and data center backup power "
            "are driving high-single-digit margin expansion across tier-1 manufacturers."
        ),
    },
}


def create_database() -> sqlite3.Connection:
    """Create fresh DB and apply schema."""
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"Removed existing DB: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

    print(f"Schema applied: {SCHEMA_PATH}")
    return conn


def load_sector_meta(conn: sqlite3.Connection) -> None:
    """Populate sector_meta table."""
    for sector, data in SECTOR_META.items():
        conn.execute(
            """
            INSERT INTO sector_meta (sector, display_name, description, benchmark_index,
                                     avg_pe, avg_ev_ebitda, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sector,
                data["display_name"],
                data["description"],
                data["benchmark_index"],
                data["avg_pe"],
                data["avg_ev_ebitda"],
                data["notes"],
            ),
        )
    conn.commit()
    print("Sector metadata loaded.")


def load_companies(conn: sqlite3.Connection, sector: str) -> dict[str, int]:
    """Load companies CSV and return {ticker: company_id} map."""
    csv_path = SEED_DIR / f"{sector}_companies.csv"
    ticker_to_id: dict[str, int] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur = conn.execute(
                """
                INSERT INTO companies (name, ticker, sector, description, market_cap_bn,
                                       employees, headquarters, founded_year, source_url, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["name"].strip(),
                    row["ticker"].strip(),
                    row["sector"].strip(),
                    row.get("description", "").strip(),
                    float(row["market_cap_bn"]) if row["market_cap_bn"] else None,
                    int(row["employees"]) if row["employees"] else None,
                    row.get("headquarters", "").strip(),
                    int(row["founded_year"]) if row["founded_year"] else None,
                    row.get("source_url", "").strip(),
                    row.get("last_updated", "").strip(),
                ),
            )
            ticker_to_id[row["ticker"].strip()] = cur.lastrowid  # type: ignore[assignment]

    conn.commit()
    print(f"  Companies loaded: {sector} ({len(ticker_to_id)} rows)")
    return ticker_to_id


def load_financials(
    conn: sqlite3.Connection, sector: str, ticker_to_id: dict[str, int]
) -> None:
    """Load financials CSV for a given sector."""
    csv_path = SEED_DIR / f"{sector}_financials.csv"

    def _safe_float(val: str) -> float | None:
        try:
            return float(val) if val not in ("", "None", "null") else None
        except ValueError:
            return None

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["ticker"].strip()
            company_id = ticker_to_id.get(ticker)
            if not company_id:
                print(f"  WARNING: No company_id for ticker '{ticker}' — skipping")
                continue

            conn.execute(
                """
                INSERT INTO financials (company_id, fiscal_year, revenue_bn, ebitda_bn,
                    net_income_bn, ebitda_margin, gross_margin, pe_ratio, ev_ebitda,
                    debt_equity, roe, revenue_growth, free_cash_flow_bn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    int(row["fiscal_year"]),
                    _safe_float(row.get("revenue_bn", "")),
                    _safe_float(row.get("ebitda_bn", "")),
                    _safe_float(row.get("net_income_bn", "")),
                    _safe_float(row.get("ebitda_margin", "")),
                    _safe_float(row.get("gross_margin", "")),
                    _safe_float(row.get("pe_ratio", "")),
                    _safe_float(row.get("ev_ebitda", "")),
                    _safe_float(row.get("debt_equity", "")),
                    _safe_float(row.get("roe", "")),
                    _safe_float(row.get("revenue_growth", "")),
                    _safe_float(row.get("free_cash_flow_bn", "")),
                ),
            )

    conn.commit()
    print(f"  Financials loaded: {sector}")


def load_news(
    conn: sqlite3.Connection, sector: str, ticker_to_id: dict[str, int]
) -> None:
    """Load news signals CSV for a given sector."""
    csv_path = SEED_DIR / f"{sector}_news.csv"

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["ticker"].strip()
            company_id = ticker_to_id.get(ticker)
            if not company_id:
                print(f"  WARNING: No company_id for ticker '{ticker}' — skipping")
                continue

            conn.execute(
                """
                INSERT INTO news_signals (company_id, signal_type, headline, summary, date, source_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    row["signal_type"].strip(),
                    row["headline"].strip(),
                    row.get("summary", "").strip(),
                    row["date"].strip(),
                    row.get("source_url", "").strip(),
                ),
            )

    conn.commit()
    print(f"  News signals loaded: {sector}")


def verify_database(conn: sqlite3.Connection) -> None:
    """Print row counts for sanity check."""
    print("\n=== Database Verification ===")
    for table in ["companies", "financials", "news_signals", "sector_meta"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    print("\n  Companies by sector:")
    for row in conn.execute(
        "SELECT sector, COUNT(*) as n FROM companies GROUP BY sector"
    ):
        print(f"    {row[0]}: {row[1]} companies")

    print(f"\nDatabase saved at: {DB_PATH}")


def main() -> None:
    print("Building financial_agent.db...\n")

    conn = create_database()

    try:
        load_sector_meta(conn)

        for sector in SECTORS:
            print(f"\nLoading sector: {sector}")
            ticker_to_id = load_companies(conn, sector)
            load_financials(conn, sector, ticker_to_id)
            load_news(conn, sector, ticker_to_id)

        verify_database(conn)
        print("\n[OK] Database build complete!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        conn.close()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
