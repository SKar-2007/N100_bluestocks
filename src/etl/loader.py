import csv
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from src.etl.normaliser import normalize_ticker, normalize_year
from src.etl.validator import Validator

load_dotenv()

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DB_PATH', 'nifty100.db')
SCHEMA_PATH = os.getenv('DB_SCHEMA', 'db/schema.sql')
DATA_DIR = Path(os.getenv('DATA_DIR', 'data/'))
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'output/'))
LOAD_AUDIT_PATH = Path(os.getenv('LOAD_AUDIT_PATH', 'output/load_audit.csv'))
VALIDATION_FAILURES_PATH = Path(os.getenv('VALIDATION_FAILURES_PATH', 'output/validation_failures.csv'))
LOAD_ORDER = os.getenv('LOAD_ORDER', 'sectors,companies,profitandloss,balancesheet,cashflow,analysis,documents,prosandcons,stock_prices,financial_ratios,peer_groups').split(',')

SOURCE_FILES = {
    'companies': 'companies.xlsx',
    'profitandloss': 'profitandloss.xlsx',
    'balancesheet': 'balancesheet.xlsx',
    'cashflow': 'cashflow.xlsx',
    'analysis': 'analysis.xlsx',
    'documents': 'documents.xlsx',
    'prosandcons': 'prosandcons.xlsx',
    'sectors': 'sectors.xlsx',
    'stock_prices': 'stock_prices.xlsx',
    'financial_ratios': 'financial_ratios.xlsx',
    'peer_groups': 'peer_groups.xlsx',
}

CORE_TABLES = {'companies', 'profitandloss', 'balancesheet', 'cashflow', 'analysis', 'documents', 'prosandcons'}

# source_col -> target_col. None means skip.
COL_MAP = {
    'profitandloss': {
        'sales': 'revenue', 'operating_profit': 'operating_profit',
        'opm_percentage': 'operating_profit_margin', 'other_income': 'other_income',
        'interest': 'interest_expense', 'depreciation': 'depreciation',
        'profit_before_tax': 'profit_before_tax', 'tax_percentage': 'tax_expense',
        'net_profit': 'net_profit', 'eps': 'eps', 'dividend_payout': 'dividend_payout_ratio',
    },
    'balancesheet': {
        'equity_capital': 'share_capital', 'reserves': 'reserves_and_surplus',
        'borrowings': 'total_debt', 'other_liabilities': 'current_liabilities',
        'total_liabilities': 'total_liabilities', 'fixed_assets': 'fixed_assets',
        'investments': 'investments', 'total_assets': 'total_assets',
    },
    'cashflow': {
        'operating_activity': 'cash_from_operations',
        'investing_activity': 'cash_from_investing',
        'financing_activity': 'cash_from_financing',
        'net_cash_flow': 'net_cash_flow',
    },
    'stock_prices': {
        'open_price': 'open', 'high_price': 'high', 'low_price': 'low',
        'close_price': 'close', 'adjusted_close': 'adjusted_close', 'volume': 'volume',
    },
    'financial_ratios': {
        'net_profit_margin_pct': 'net_profit_margin',
        'operating_profit_margin_pct': 'operating_profit_margin',
        'return_on_equity_pct': 'return_on_equity',
        'debt_to_equity': 'debt_to_equity_ratio',
    },
    'documents': {
        'annual_report': 'annual_report_url',
    },
    'prosandcons': {
        'pros': 'pros', 'cons': 'cons',
    },
    'peer_groups': {
        'peer_group_name': 'group_name',
    },
}


def _clean_url(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    if s.lower() == 'null' or s.lower() == 'none' or s.lower() == 'nan':
        return None
    if not s.startswith(('http://', 'https://', '//')):
        s = 'https://' + s
    return s


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_database(conn):
    if not Path(SCHEMA_PATH).exists():
        logger.error(f"Schema file not found: {SCHEMA_PATH}")
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_PATH}")
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    logger.info("Database schema initialized successfully")


def read_source(table_name):
    path = DATA_DIR / SOURCE_FILES[table_name]
    if not path.exists():
        logger.warning(f"File not found: {path}, skipping {table_name}")
        return None
    try:
        if table_name in CORE_TABLES:
            raw = pd.read_excel(path, header=None)
            if len(raw) < 2:
                return None
            cols = [str(c).strip() if pd.notna(c) else f'c{i}' for i, c in enumerate(raw.iloc[1])]
            df = raw.iloc[2:].copy()
            df.columns = cols
            df = df.reset_index(drop=True)
        else:
            df = pd.read_excel(path)
        return df
    except Exception as e:
        logger.error(f"Failed to read {path}: {e}")
        return None


def apply_col_map(df, table_name):
    if table_name not in COL_MAP:
        return df
    mapping = COL_MAP[table_name]
    lowered = {str(c).strip().lower(): str(c).strip() for c in df.columns}
    rename = {}
    keep = {'company_id', 'year', 'date'}
    for src_lc, tgt in mapping.items():
        if src_lc in lowered:
            actual = lowered[src_lc]
            if tgt is not None:
                rename[actual] = tgt
    # Also normalize identity column names (Year -> year, etc.)
    identity_rename = {}
    for col in df.columns:
        cl = str(col).strip().lower()
        if cl in keep:
            target = cl
            if str(col).strip() != target:
                identity_rename[str(col).strip()] = target
    df = df.rename(columns={**rename, **identity_rename})
    # Per-table identity column exclusions
    exclude_id = set()
    if table_name in ('documents', 'prosandcons'):
        exclude_id.add('year')
    rename_values = set(rename.values()) | set(identity_rename.values())
    cols_to_keep = [str(c).strip() for c in df.columns
                    if (str(c).strip() in rename_values
                    or str(c).strip().lower() in keep)
                    and str(c).strip().lower() not in exclude_id]
    if not cols_to_keep:
        return df
    return df[cols_to_keep]


def load_sectors_table(conn):
    df = read_source('sectors')
    if df is None or df.empty:
        return 0, 0
    count = 0
    for name in df['broad_sector'].unique():
        if pd.notna(name):
            conn.execute("INSERT OR IGNORE INTO sectors (sector_name) VALUES (?)", (str(name).strip(),))
            count += 1
    conn.commit()
    logger.info(f"Loaded {count} sectors")
    return count, 0


def load_companies_table(conn):
    df = read_source('companies')
    if df is None or df.empty:
        return 0, 0

    sectors_df = read_source('sectors')
    ticker_sector = {}
    if sectors_df is not None:
        for _, r in sectors_df.iterrows():
            t = normalize_ticker(str(r['company_id']))
            if t:
                ticker_sector[t] = str(r['broad_sector']).strip()

    sid_map = dict(conn.execute("SELECT sector_id, sector_name FROM sectors").fetchall())
    sid_map = {v: k for k, v in sid_map.items()}

    count = 0
    for _, r in df.iterrows():
        raw_ticker = r.get('id') or r.get('company_id')
        if pd.isna(raw_ticker):
            continue
        ticker = normalize_ticker(str(raw_ticker))
        if not ticker:
            continue
        name = str(r.get('company_name', ticker)).strip().replace('\n', ' ') if pd.notna(r.get('company_name')) else ticker
        website = str(r.get('website', '')).strip() if pd.notna(r.get('website')) else None
        bs = ticker_sector.get(ticker)
        sid = sid_map.get(bs, 1)
        try:
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_name, ticker, sector_id, website_url, nse_symbol) VALUES (?,?,?,?,?)",
                (name, ticker, sid, website, ticker)
            )
            count += 1
        except Exception as e:
            logger.debug(f"Company insert error {ticker}: {e}")
    conn.commit()
    logger.info(f"Loaded {count} companies")
    return count, 0


def get_ticker_id_map(conn):
    return dict(conn.execute("SELECT ticker, company_id FROM companies").fetchall())


def ensure_companies_exist(conn, ticker_map, df, table_name):
    ticker_cols = [c for c in df.columns if 'company_id' in c.lower()]
    if not ticker_cols:
        return ticker_map
    tc = ticker_cols[0]
    new_count = 0
    for v in df[tc].unique():
        if pd.isna(v):
            continue
        t = normalize_ticker(str(v))
        if t and t not in ticker_map:
            conn.execute(
                "INSERT OR IGNORE INTO companies (company_name, ticker, sector_id, nse_symbol) VALUES (?,?,?,?)",
                (t, t, 1, t)
            )
            ticker_map[t] = conn.execute("SELECT company_id FROM companies WHERE ticker = ?", (t,)).fetchone()[0]
            new_count += 1
    if new_count:
        conn.commit()
        logger.info(f"Auto-created {new_count} company records from {table_name} data")
    return ticker_map


def parse_analysis_value(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    m = re.search(r'([\d.]+)', s)
    if m:
        return float(m.group(1))
    return None


def load_analysis_table(conn, df, ticker_map, validator):
    if df is None or df.empty:
        return 0, 0
    df = df.copy()
    ticker_map = ensure_companies_exist(conn, ticker_map, df, 'analysis')
    successful = 0
    for _, r in df.iterrows():
        raw_ticker = r.get('company_id')
        if pd.isna(raw_ticker):
            continue
        t = normalize_ticker(str(raw_ticker))
        if not t or t not in ticker_map:
            continue
        cid = ticker_map[t]
        roe = parse_analysis_value(r.get('roe'))
        sales_gr = parse_analysis_value(r.get('compounded_sales_growth'))
        profit_gr = parse_analysis_value(r.get('compounded_profit_growth'))
        price_cagr = parse_analysis_value(r.get('stock_price_cagr'))
        try:
            conn.execute(
                "INSERT OR IGNORE INTO analysis (company_id, year, return_on_equity, return_on_assets, return_on_capital_employed) VALUES (?,?,?,?,?)",
                (cid, 2024, roe, sales_gr, profit_gr)
            )
            successful += 1
        except Exception as e:
            logger.debug(f"Analysis insert error {t}: {e}")
    conn.commit()
    loaded = conn.execute("SELECT COUNT(*) FROM analysis").fetchone()[0]
    logger.info(f"Loaded {loaded} rows into analysis")
    return loaded, 0


def load_peer_groups(conn, df, ticker_map):
    df['company_id'] = df['company_id'].apply(lambda v: ticker_map.get(normalize_ticker(str(v))) if pd.notna(v) else None)
    df = df[df['company_id'].notna()].copy()

    benchmarks = {}
    for _, r in df.iterrows():
        gname = str(r['peer_group_name']).strip()
        if str(r.get('is_benchmark', '')).strip().lower() == 'true':
            benchmarks[gname] = r['company_id']

    count = 0
    for _, r in df.iterrows():
        gname = str(r['peer_group_name']).strip()
        peer_id = benchmarks.get(gname)
        if peer_id is None or r['company_id'] == peer_id:
            continue
        try:
            conn.execute(
                "INSERT OR IGNORE INTO peer_groups (company_id, peer_company_id, group_name) VALUES (?,?,?)",
                (int(r['company_id']), int(peer_id), gname)
            )
            count += 1
        except Exception as e:
            logger.debug(f"peer_groups insert error: {e}")
    conn.commit()
    logger.info(f"Loaded {count} rows into peer_groups")
    return count, 0


def load_financial_table(conn, table_name, ticker_map, validator):
    df = read_source(table_name)
    if df is None or df.empty:
        return 0, 0

    if table_name == 'analysis':
        before = len(df)
        df = df.drop_duplicates(subset=['company_id'], keep='first')
        return load_analysis_table(conn, df, ticker_map, validator)

    if table_name == 'peer_groups':
        return load_peer_groups(conn, df, ticker_map)

    # Auto-create company records for tickers in this table that don't exist yet
    ticker_map = ensure_companies_exist(conn, ticker_map, df, table_name)

    df = apply_col_map(df, table_name)

    # Normalize year
    if 'year' in df.columns:
        df['year'] = df['year'].apply(lambda v: normalize_year(str(v)) if pd.notna(v) else None)

    # Resolve ticker -> company_id for all ticker columns
    ticker_cols = [c for c in df.columns if 'company_id' in c.lower()]
    for tc in ticker_cols:
        raw_ids = df[tc]
        resolved = []
        for v in raw_ids:
            if pd.isna(v):
                resolved.append(None)
            else:
                t = normalize_ticker(str(v))
                resolved.append(ticker_map.get(t))
        df[tc] = resolved

    # Drop duplicate (company_id, year) combos before validation to prevent DQ-01
    if 'year' in df.columns and 'company_id' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['company_id', 'year'], keep='first')
        if len(df) < before:
            logger.debug(f"Dropped {before - len(df)} duplicate (company_id, year) rows from {table_name}")
    elif 'company_id' in df.columns and table_name in ('documents', 'prosandcons', 'peer_groups'):
        before = len(df)
        df = df.drop_duplicates(subset=['company_id'], keep='first')
        if len(df) < before:
            logger.debug(f"Dropped {before - len(df)} duplicate company_id rows from {table_name}")
    elif 'company_id' in df.columns and 'date' in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=['company_id', 'date'], keep='first')
        if len(df) < before:
            logger.debug(f"Dropped {before - len(df)} duplicate (company_id, date) rows from {table_name}")

    # Drop rows with no company_id
    before = len(df)
    df = df[df['company_id'].notna()].copy()
    if len(df) < before:
        logger.debug(f"Dropped {before - len(df)} rows with unmapped company_id from {table_name}")

    # Drop rows with no year for tables that require year
    if 'year' in df.columns:
        before = len(df)
        df = df[df['year'].notna()].copy()
        if len(df) < before:
            logger.debug(f"Dropped {before - len(df)} rows with null year from {table_name}")

    df = df.apply(lambda col: col.map(lambda x: None if isinstance(x, float) and pd.isna(x) else x))

    # Clean URL fields for documents table
    if table_name == 'documents':
        for col in df.columns:
            if 'url' in col.lower() or 'link' in col.lower() or 'website' in col.lower():
                df[col] = df[col].apply(_clean_url)

    df = validator.validate_table(table_name, df)

    successful = 0
    rejected = 0
    for _, row in df.iterrows():
        rec = {k: v for k, v in row.items() if pd.notna(v) or k in ('company_id', 'year', 'date')}
        rec = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in rec.items()}
        try:
            cols = ', '.join(rec.keys())
            ph = ', '.join(['?'] * len(rec))
            conn.execute(f"INSERT OR IGNORE INTO {table_name} ({cols}) VALUES ({ph})", list(rec.values()))
            successful += 1
        except Exception as e:
            rejected += 1
            logger.debug(f"Insert error {table_name}: {e}")
    conn.commit()
    logger.info(f"Loaded {successful} rows into {table_name} ({rejected} rejected)")
    return successful, rejected


def write_audit(records):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fns = ['table_name', 'source_file', 'expected_rows', 'loaded_rows', 'rejected_rows', 'load_timestamp', 'status']
    with open(LOAD_AUDIT_PATH, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fns)
        w.writeheader()
        w.writerows(records)
    logger.info(f"Audit written to {LOAD_AUDIT_PATH}")


def check_fk(conn):
    return conn.execute("PRAGMA foreign_key_check;").fetchall()


def load_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validator = Validator(VALIDATION_FAILURES_PATH)
    conn = get_connection()
    try:
        init_database(conn)
        audit = []

        # 1. Sectors
        l, r = load_sectors_table(conn)
        audit.append(dict(table_name='sectors', source_file='sectors.xlsx', expected_rows=10, loaded_rows=l, rejected_rows=r,
                          load_timestamp=datetime.now().isoformat(), status='SUCCESS'))

        # 2. Companies
        l, r = load_companies_table(conn)
        audit.append(dict(table_name='companies', source_file='companies.xlsx', expected_rows=92, loaded_rows=l, rejected_rows=r,
                          load_timestamp=datetime.now().isoformat(), status='SUCCESS'))

        ticker_map = get_ticker_id_map(conn)
        logger.info(f"Built ticker map with {len(ticker_map)} entries")

        # 3. Financial tables in order
        fin_tables = ['profitandloss', 'balancesheet', 'cashflow', 'analysis', 'documents', 'prosandcons',
                      'stock_prices', 'financial_ratios', 'peer_groups']
        exp_counts = {'profitandloss': 1276, 'balancesheet': 1312, 'cashflow': 1187, 'stock_prices': 5520,
                      'analysis': 92, 'documents': 92, 'prosandcons': 92, 'financial_ratios': 1276, 'peer_groups': 56}

        for tbl in fin_tables:
            if tbl not in SOURCE_FILES:
                continue
            if not (DATA_DIR / SOURCE_FILES[tbl]).exists():
                audit.append(dict(table_name=tbl, source_file=SOURCE_FILES[tbl], expected_rows=exp_counts.get(tbl, 0),
                                  loaded_rows=0, rejected_rows=0, load_timestamp=datetime.now().isoformat(), status='MISSING'))
                continue
            l, r = load_financial_table(conn, tbl, ticker_map, validator)
            audit.append(dict(table_name=tbl, source_file=SOURCE_FILES[tbl], expected_rows=exp_counts.get(tbl, 0),
                              loaded_rows=l, rejected_rows=r,
                              load_timestamp=datetime.now().isoformat(), status='SUCCESS' if r == 0 else 'PARTIAL'))

        fk_issues = check_fk(conn)
        if fk_issues:
            logger.warning(f"FK violations: {len(fk_issues)}")
            for v in fk_issues:
                logger.warning(f"  FK: {v}")
        else:
            logger.info("FK check passed: 0 violations")

        validator.dump_failures()
        write_audit(audit)
        logger.info("ETL pipeline completed successfully")
        return audit, fk_issues
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise
    finally:
        conn.close()


def expected_row_count(table_name):
    return {
        'companies': 92, 'profitandloss': 1276, 'balancesheet': 1312,
        'cashflow': 1187, 'stock_prices': 5520, 'sectors': 10,
        'analysis': 92, 'documents': 92, 'prosandcons': 92,
        'financial_ratios': 1276, 'peer_groups': 56,
    }.get(table_name, 0)


def compute_ratios():
    conn = get_connection()
    try:
        c = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        logger.info(f"Computing ratios for {c} companies")
        conn.execute("""
            INSERT OR REPLACE INTO financial_ratios (company_id, year, operating_profit_margin, net_profit_margin, return_on_equity)
            SELECT pl.company_id, pl.year,
                CASE WHEN pl.revenue>0 THEN pl.operating_profit/pl.revenue*100 END,
                CASE WHEN pl.revenue>0 THEN pl.net_profit/pl.revenue*100 END,
                CASE WHEN bs.shareholders_equity>0 THEN pl.net_profit/bs.shareholders_equity*100 END
            FROM profitandloss pl LEFT JOIN balancesheet bs ON pl.company_id=bs.company_id AND pl.year=bs.year
        """)
        conn.commit()
        logger.info("Ratios computed")
    finally:
        conn.close()


def launch_dashboard():
    try:
        import plotly.express as px
    except ImportError:
        logger.error("plotly required")
        return
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM companies", conn)
        if not df.empty:
            px.bar(df, x='company_name', title='Companies').show()
    finally:
        conn.close()


if __name__ == '__main__':
    load_all()
