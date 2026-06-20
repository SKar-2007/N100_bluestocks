import os
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.etl.normaliser import normalize_ticker, normalize_year
from src.etl.validator import Validator


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / 'test.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn, db_path
    conn.close()


class TestTickerResolution:
    def test_normalize_ticker_basic(self):
        assert normalize_ticker('TCS') == 'TCS'
        assert normalize_ticker('tcs') == 'TCS'
        assert normalize_ticker('TCS.NS') == 'TCS'

    def test_normalize_ticker_suffixes(self):
        assert normalize_ticker('TCS.BSE') == 'TCS'
        assert normalize_ticker('TCS.NSE') == 'TCS'
        assert normalize_ticker('TCS.BO') == 'TCS'

    def test_normalize_ticker_prefixes(self):
        assert normalize_ticker('NSE:TCS') == 'TCS'
        assert normalize_ticker('BSE:INFY') == 'INFY'

    def test_normalize_ticker_ampersand(self):
        assert normalize_ticker('M&M') == 'MANDM'

    def test_normalize_ticker_edge_cases(self):
        assert normalize_ticker(None) is None
        assert normalize_ticker('') is None
        assert normalize_ticker('   ') is None


class TestYearResolution:
    def test_normalize_year_basic(self):
        assert normalize_year('FY2023') == 2023
        assert normalize_year('2023') == 2023
        assert normalize_year(2023) == 2023

    def test_normalize_year_ranges(self):
        assert normalize_year('2022-23') == 2022
        assert normalize_year('2022-2023') == 2022

    def test_normalize_year_fiscal(self):
        assert normalize_year('Mar 2023') == 2023
        assert normalize_year('Dec 2023') == 2023

    def test_normalize_year_edge_cases(self):
        assert normalize_year(None) is None
        assert normalize_year('') is None
        assert normalize_year('invalid') is None


class TestColumnMapping:
    def test_apply_col_map_profitandloss(self):
        from src.etl.loader import apply_col_map
        df = pd.DataFrame({
            'company_id': ['ABB'], 'year': ['Dec 2012'],
            'sales': [1653], 'operating_profit': [202],
            'opm_percentage': [12.0], 'other_income': [33],
            'interest': [0], 'depreciation': [19],
            'profit_before_tax': [215], 'tax_percentage': [33],
            'net_profit': [145], 'eps': [68],
            'dividend_payout': [25]
        })
        result = apply_col_map(df, 'profitandloss')
        assert 'revenue' in result.columns
        assert 'sales' not in result.columns
        assert 'operating_profit' in result.columns
        assert 'operating_profit_margin' in result.columns
        assert 'interest_expense' in result.columns
        assert 'tax_expense' in result.columns
        assert 'dividend_payout_ratio' in result.columns
        assert 'company_id' in result.columns
        assert 'year' in result.columns

    def test_apply_col_map_balancesheet(self):
        from src.etl.loader import apply_col_map
        df = pd.DataFrame({
            'company_id': ['ABB'], 'year': ['Dec 2012'],
            'equity_capital': [21], 'reserves': [626],
            'borrowings': [0], 'other_liabilities': [260],
            'total_liabilities': [907], 'fixed_assets': [109],
            'investments': [0], 'total_assets': [907]
        })
        result = apply_col_map(df, 'balancesheet')
        assert 'share_capital' in result.columns
        assert 'reserves_and_surplus' in result.columns
        assert 'total_debt' in result.columns
        assert 'current_liabilities' in result.columns
        assert 'company_id' in result.columns

    def test_apply_col_map_cashflow(self):
        from src.etl.loader import apply_col_map
        df = pd.DataFrame({
            'company_id': ['TCS'], 'year': ['Mar-13'],
            'operating_activity': [11615],
            'investing_activity': [-6038],
            'financing_activity': [-5729],
            'net_cash_flow': [-152]
        })
        result = apply_col_map(df, 'cashflow')
        assert 'cash_from_operations' in result.columns
        assert 'cash_from_investing' in result.columns
        assert 'cash_from_financing' in result.columns
        assert 'company_id' in result.columns

    def test_apply_col_map_documents_excludes_year(self):
        from src.etl.loader import apply_col_map
        df = pd.DataFrame({
            'company_id': ['ABB'], 'Year': [2024],
            'Annual_Report': ['https://example.com']
        })
        result = apply_col_map(df, 'documents')
        assert 'annual_report_url' in result.columns
        assert 'year' not in result.columns
        assert 'company_id' in result.columns


@pytest.mark.slow
class TestSchemaCreation:
    def test_init_database_creates_tables(self, tmp_path):
        from src.etl.loader import init_database, get_connection
        db_path = tmp_path / 'test_nifty.db'
        import os
        os.environ['DB_PATH'] = str(db_path)
        os.environ['DB_SCHEMA'] = 'db/schema.sql'

        conn = get_connection()
        init_database(conn)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [t[0] for t in tables]
        expected = ['analysis', 'balancesheet', 'cashflow', 'companies',
                    'documents', 'financial_ratios', 'peer_groups',
                    'profitandloss', 'prosandcons', 'sectors', 'stock_prices']
        for e in expected:
            assert e in table_names
        conn.close()


class TestNormalizerEdgeCases:
    def test_year_with_month_suffix(self):
        assert normalize_year('Dec 2012') == 2012
        assert normalize_year('March 2024') == 2024
        assert normalize_year('Mar-2023') == 2023

    def test_year_with_special_chars(self):
        assert normalize_year('2022\u201323') == 2022

    def test_ticker_special_chars_removed(self):
        result = normalize_ticker('HCL@TECH')
        assert '@' not in result
        assert result == 'HCLTECH'

    def test_ticker_multiple_suffixes(self):
        result = normalize_ticker('TCS.NS.NS')
        assert result == 'TCS'

    def test_ticker_whitespace_inside(self):
        result = normalize_ticker('HCL TECH')
        assert result == 'HCLTECH'

    def test_ticker_lowercase_mixed(self):
        assert normalize_ticker('hdfcBank') == 'HDFCBANK'
        assert normalize_ticker('IcIcI BAnk') == 'ICICIBANK'
