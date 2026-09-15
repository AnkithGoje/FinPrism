-- ============================================================
-- Configurable Financial Agent — SQLite Schema
-- ============================================================

-- Core company registry
CREATE TABLE IF NOT EXISTS companies (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    ticker          TEXT,
    sector          TEXT NOT NULL CHECK(sector IN ('tech', 'retail', 'manufacturing')),
    description     TEXT,
    market_cap_bn   REAL,        -- USD billions
    employees       INTEGER,
    headquarters    TEXT,
    founded_year    INTEGER,
    source_url      TEXT,
    last_updated    TEXT         -- ISO date YYYY-MM-DD
);

-- Annual financials per company
CREATE TABLE IF NOT EXISTS financials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    fiscal_year     INTEGER NOT NULL,
    revenue_bn      REAL,        -- USD billions
    ebitda_bn       REAL,
    net_income_bn   REAL,
    ebitda_margin   REAL,        -- percentage e.g. 28.5
    gross_margin    REAL,
    pe_ratio        REAL,
    ev_ebitda       REAL,        -- EV/EBITDA multiple
    debt_equity     REAL,        -- Debt-to-equity ratio
    roe             REAL,        -- Return on equity %
    revenue_growth  REAL,        -- YoY revenue growth %
    free_cash_flow_bn REAL
);

-- Sector-level metadata for benchmark context
CREATE TABLE IF NOT EXISTS sector_meta (
    sector          TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    description     TEXT,
    benchmark_index TEXT,        -- e.g. 'NASDAQ-100', 'S&P Retail ETF'
    avg_pe          REAL,        -- Sector average P/E
    avg_ev_ebitda   REAL,
    notes           TEXT
);

-- Recent news signals (hiring, layoffs, expansion, earnings beats/misses)
CREATE TABLE IF NOT EXISTS news_signals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id      INTEGER NOT NULL REFERENCES companies(id),
    signal_type     TEXT NOT NULL CHECK(signal_type IN ('hiring','layoff','expansion','contraction','earnings_beat','earnings_miss','acquisition','divestiture')),
    headline        TEXT NOT NULL,
    summary         TEXT,
    date            TEXT NOT NULL,  -- ISO date
    source_url      TEXT
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_companies_sector    ON companies(sector);
CREATE INDEX IF NOT EXISTS idx_financials_company  ON financials(company_id);
CREATE INDEX IF NOT EXISTS idx_financials_year     ON financials(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_news_company        ON news_signals(company_id);
CREATE INDEX IF NOT EXISTS idx_news_type           ON news_signals(signal_type);
