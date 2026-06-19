import csv
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

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

CORE_FILES = {
    'companies': 'data/companies.xlsx',
    'profitandloss': 'data/profitandloss.xlsx',
    'balancesheet': 'data/balancesheet.xlsx',
    'cashflow': 'data/cashflow.xlsx',
    'analysis': 'data/analysis.xlsx',
    'documents': 'data/documents.xlsx',
    'prosandcons': 'data/prosandcons.xlsx',
}

SUPPLEMENTARY_FILES = {
    'sectors': 'data/sectors.xlsx',
    'stock_prices': 'data/stock_prices.xlsx',
    'financial_ratios': 'data/financial_ratios.xlsx',
    'peer_groups': 'data/peer_groups.xlsx',
}


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
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    logger.info("Database schema initialized successfully")


def load_table(conn, table_name, file_path, validator):
    logger.info(f"Loading table: {table_name} from {file_path}")

    if not Path(file_path).exists():
        logger.warning(f"File not found: {file_path}, skipping {table_name}")
        return 0, 0

    try:
        import pandas as pd
        df = pd.read_excel(file_path)
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return 0, 0

    if df.empty:
        logger.warning(f"Empty file: {file_path}")
        return 0, 0

    df = validator.validate_table(table_name, df)

    records = df.to_dict('records')
    successful = 0
    rejected = 0

    for record in records:
        try:
            columns = ', '.join(record.keys())
            placeholders = ', '.join(['?' for _ in record])
            sql = f"INSERT OR IGNORE INTO {table_name} ({columns}) VALUES ({placeholders})"
            conn.execute(sql, list(record.values()))
            successful += 1
        except sqlite3.IntegrityError as e:
            rejected += 1
            logger.debug(f"Integrity error on {table_name}: {e}")
        except Exception as e:
            rejected += 1
            logger.debug(f"Error inserting into {table_name}: {e}")

    conn.commit()
    logger.info(f"Loaded {successful} rows into {table_name} ({rejected} rejected)")
    return successful, rejected


def write_audit(audit_records):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        'table_name', 'source_file', 'expected_rows', 'loaded_rows',
        'rejected_rows', 'load_timestamp', 'status'
    ]
    with open(LOAD_AUDIT_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_records)
    logger.info(f"Audit written to {LOAD_AUDIT_PATH}")


def validate_foreign_keys(conn):
    cursor = conn.execute("PRAGMA foreign_key_check;")
    violations = cursor.fetchall()
    return violations


def load_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validator = Validator(VALIDATION_FAILURES_PATH)
    conn = get_connection()

    try:
        init_database(conn)

        audit_records = []
        all_files = {**CORE_FILES, **SUPPLEMENTARY_FILES}

        for table_name in LOAD_ORDER:
            if table_name in all_files:
                expected = expected_row_count(table_name)
                loaded, rejected = load_table(conn, table_name, all_files[table_name], validator)
                audit_records.append({
                    'table_name': table_name,
                    'source_file': all_files.get(table_name, ''),
                    'expected_rows': expected,
                    'loaded_rows': loaded,
                    'rejected_rows': rejected,
                    'load_timestamp': datetime.now().isoformat(),
                    'status': 'SUCCESS' if rejected == 0 else 'PARTIAL',
                })

        fk_violations = validate_foreign_keys(conn)
        if fk_violations:
            logger.warning(f"Foreign key violations found: {len(fk_violations)}")
            for violation in fk_violations:
                logger.warning(f"  FK violation: {violation}")
        else:
            logger.info("Foreign key check passed: 0 violations")

        validator.dump_failures()

        write_audit(audit_records)

        logger.info("ETL pipeline completed successfully")
        return audit_records, fk_violations

    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        raise
    finally:
        conn.close()


def expected_row_count(table_name):
    counts = {
        'companies': 92,
        'profitandloss': 1276,
        'balancesheet': 1312,
        'cashflow': 1187,
        'stock_prices': 5520,
        'sectors': 50,
        'analysis': 92,
        'documents': 92,
        'prosandcons': 92,
        'financial_ratios': 1276,
        'peer_groups': 50,
    }
    return counts.get(table_name, 0)


def compute_ratios():
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT COUNT(*) FROM companies")
        count = cursor.fetchone()[0]
        logger.info(f"Computing financial ratios for {count} companies")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financial_ratios AS
            SELECT
                pl.company_id,
                pl.year,
                CASE WHEN pl.revenue > 0 THEN (pl.profit_before_tax / pl.revenue * 100) ELSE NULL END AS operating_profit_margin,
                CASE WHEN pl.revenue > 0 THEN (pl.net_profit / pl.revenue * 100) ELSE NULL END AS net_profit_margin,
                CASE WHEN pl.revenue > 0 THEN (pl.ebitda / pl.revenue * 100) ELSE NULL END AS ebitda_margin,
                CASE WHEN bs.total_assets > 0 THEN (bs.shareholders_equity / bs.total_assets * 100) ELSE NULL END AS debt_to_equity,
                CASE WHEN bs.total_assets > 0 THEN (bs.current_assets / bs.total_assets * 100) ELSE NULL END AS current_ratio
            FROM profitandloss pl
            LEFT JOIN balancesheet bs ON pl.company_id = bs.company_id AND pl.year = bs.year
        """)
        conn.commit()
        logger.info("Financial ratios computed successfully")
    finally:
        conn.close()


def launch_dashboard():
    try:
        import plotly.express as px
        import pandas as pd
    except ImportError:
        logger.error("plotly and pandas required for dashboard")
        return

    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM companies", conn)
        if not df.empty:
            fig = px.bar(df, x='company_name', title='Companies Overview')
            fig.show()
    finally:
        conn.close()


if __name__ == '__main__':
    load_all()
