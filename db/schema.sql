PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- sectors
CREATE TABLE IF NOT EXISTS sectors (
    sector_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_name TEXT NOT NULL UNIQUE,
    sector_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- companies
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    ticker TEXT NOT NULL UNIQUE,
    sector_id INTEGER NOT NULL,
    bse_code TEXT,
    nse_symbol TEXT,
    isin_code TEXT,
    website_url TEXT,
    founded_year INTEGER,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sector_id) REFERENCES sectors(sector_id)
);

-- profitandloss
CREATE TABLE IF NOT EXISTS profitandloss (
    pl_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    revenue REAL,
    cost_of_goods_sold REAL,
    gross_profit REAL,
    operating_expenses REAL,
    operating_profit REAL,
    operating_profit_margin REAL,
    ebitda REAL,
    ebitda_margin REAL,
    depreciation REAL,
    interest_expense REAL,
    other_income REAL,
    profit_before_tax REAL,
    tax_expense REAL,
    net_profit REAL,
    eps REAL,
    dividend REAL,
    dividend_payout_ratio REAL,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- balancesheet
CREATE TABLE IF NOT EXISTS balancesheet (
    bs_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    share_capital REAL,
    reserves_and_surplus REAL,
    shareholders_equity REAL,
    long_term_debt REAL,
    short_term_debt REAL,
    total_debt REAL,
    current_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    intangible_assets REAL,
    current_assets REAL,
    investments REAL,
    cash_and_equivalents REAL,
    total_assets REAL,
    book_value_per_share REAL,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- cashflow
CREATE TABLE IF NOT EXISTS cashflow (
    cf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    cash_from_operations REAL,
    cash_from_investing REAL,
    cash_from_financing REAL,
    net_cash_flow REAL,
    cash_and_equivalents REAL,
    free_cash_flow REAL,
    capital_expenditure REAL,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- analysis
CREATE TABLE IF NOT EXISTS analysis (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    return_on_equity REAL,
    return_on_assets REAL,
    return_on_capital_employed REAL,
    current_ratio REAL,
    quick_ratio REAL,
    debt_to_equity REAL,
    interest_coverage_ratio REAL,
    asset_turnover_ratio REAL,
    inventory_turnover_ratio REAL,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- documents
CREATE TABLE IF NOT EXISTS documents (
    doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL UNIQUE,
    annual_report_url TEXT,
    corporate_governance_url TEXT,
    shareholding_pattern_url TEXT,
    credit_rating_report_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- prosandcons
CREATE TABLE IF NOT EXISTS prosandcons (
    pc_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL UNIQUE,
    pros TEXT,
    cons TEXT,
    key_highlights TEXT,
    risks TEXT,
    management_quality_rating TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- stock_prices
CREATE TABLE IF NOT EXISTS stock_prices (
    price_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    adjusted_close REAL,
    volume INTEGER,
    bse_price REAL,
    nse_price REAL,
    UNIQUE(company_id, date),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- financial_ratios
CREATE TABLE IF NOT EXISTS financial_ratios (
    ratio_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    operating_profit_margin REAL,
    net_profit_margin REAL,
    ebitda_margin REAL,
    debt_to_equity_ratio REAL,
    current_ratio REAL,
    return_on_equity REAL,
    return_on_assets REAL,
    price_to_earning REAL,
    price_to_book REAL,
    dividend_yield REAL,
    earnings_yield REAL,
    UNIQUE(company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

-- peer_groups
CREATE TABLE IF NOT EXISTS peer_groups (
    peer_group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    peer_company_id INTEGER NOT NULL,
    group_name TEXT,
    similarity_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_id, peer_company_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id),
    FOREIGN KEY (peer_company_id) REFERENCES companies(company_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_pl_company_year ON profitandloss(company_id, year);
CREATE INDEX IF NOT EXISTS idx_bs_company_year ON balancesheet(company_id, year);
CREATE INDEX IF NOT EXISTS idx_cf_company_year ON cashflow(company_id, year);
CREATE INDEX IF NOT EXISTS idx_analysis_company_year ON analysis(company_id, year);
CREATE INDEX IF NOT EXISTS idx_stock_prices_company_date ON stock_prices(company_id, date);
CREATE INDEX IF NOT EXISTS idx_financial_ratios_company_year ON financial_ratios(company_id, year);
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector_id);
CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
