import pandas as pd
import pytest
from src.etl.validator import Validator, ValidationFailure, SEVERITY_CRITICAL, SEVERITY_WARNING


@pytest.fixture
def validator():
    return Validator(output_path='/tmp/test_validation_failures.csv')


class TestDQ01PrimaryKeyUniqueness:
    def test_no_duplicates(self, validator):
        df = pd.DataFrame({'id': [1, 2, 3]})
        validator._check_pk_uniqueness(df, ['id'], 'test')
        assert len(validator.failures) == 0

    def test_duplicates_detected(self, validator):
        df = pd.DataFrame({'id': [1, 2, 1]})
        validator._check_pk_uniqueness(df, ['id'], 'test')
        assert len(validator.failures) > 0

    def test_duplicates_severity(self, validator):
        df = pd.DataFrame({'id': [1, 1]})
        validator._check_pk_uniqueness(df, ['id'], 'test')
        assert validator.failures[0].severity == SEVERITY_CRITICAL

    def test_empty_df(self, validator):
        df = pd.DataFrame({'id': []})
        validator._check_pk_uniqueness(df, ['id'], 'test')
        assert len(validator.failures) == 0

    def test_missing_pk_column(self, validator):
        df = pd.DataFrame({'other': [1, 2]})
        validator._check_pk_uniqueness(df, ['id'], 'test')
        assert len(validator.failures) == 0


class TestDQ02CompositePK:
    def test_composite_unique(self, validator):
        df = pd.DataFrame({'company_id': [1, 1, 2], 'year': [2020, 2021, 2020]})
        validator._check_composite_pk(df, 'test')
        assert len(validator.failures) == 0

    def test_composite_duplicate(self, validator):
        df = pd.DataFrame({'company_id': [1, 1], 'year': [2020, 2020]})
        validator._check_composite_pk(df, 'test')
        assert len(validator.failures) > 0


class TestDQ04BalanceSheetAlignment:
    def test_balanced(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'total_assets': [100], 'total_liabilities': [60],
            'shareholders_equity': [40]
        })
        validator._check_balance_sheet_alignment(df)
        assert len(validator.failures) == 0

    def test_unbalanced(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'total_assets': [200], 'total_liabilities': [60],
            'shareholders_equity': [40]
        })
        validator._check_balance_sheet_alignment(df)
        assert len(validator.failures) > 0

    def test_unbalanced_severity(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'total_assets': [200], 'total_liabilities': [60],
            'shareholders_equity': [40]
        })
        validator._check_balance_sheet_alignment(df)
        assert validator.failures[0].severity == SEVERITY_WARNING

    def test_missing_columns(self, validator):
        df = pd.DataFrame({'company_id': [1]})
        validator._check_balance_sheet_alignment(df)
        assert len(validator.failures) == 0


class TestDQ05OPM:
    def test_opm_matches(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'revenue': [100], 'operating_profit': [20],
            'operating_profit_margin': [20.0]
        })
        validator._check_opm(df)
        assert len(validator.failures) == 0

    def test_opm_mismatch(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'revenue': [100], 'operating_profit': [20],
            'operating_profit_margin': [50.0]
        })
        validator._check_opm(df)
        assert len(validator.failures) > 0

    def test_opm_near_boundary(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'revenue': [100], 'operating_profit': [20],
            'operating_profit_margin': [19.0]
        })
        validator._check_opm(df)
        assert len(validator.failures) == 0


class TestDQ08RevenuePositive:
    def test_positive_revenue(self, validator):
        df = pd.DataFrame({'company_id': [1], 'year': [2020], 'revenue': [100]})
        validator._check_revenue_positive(df)
        assert len(validator.failures) == 0

    def test_negative_revenue(self, validator):
        df = pd.DataFrame({'company_id': [1], 'year': [2020], 'revenue': [-50]})
        validator._check_revenue_positive(df)
        assert len(validator.failures) > 0

    def test_null_revenue(self, validator):
        df = pd.DataFrame({'company_id': [1], 'year': [2020], 'revenue': [None]})
        validator._check_revenue_positive(df)
        assert len(validator.failures) == 0


class TestDQ10URLFormat:
    def test_valid_url(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'website_url': ['https://www.example.com']
        })
        validator._check_url_formats(df)
        assert len(validator.failures) == 0

    def test_invalid_url(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'website_url': ['not-a-url']
        })
        validator._check_url_formats(df)
        assert len(validator.failures) > 0

    def test_none_url(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'website_url': [None]
        })
        validator._check_url_formats(df)
        assert len(validator.failures) == 0


class TestDQ15StockPrice:
    def test_positive_prices(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'close_price': [100.0],
            'open_price': [101.0]
        })
        validator._check_stock_price_non_negative(df)
        assert len(validator.failures) == 0

    def test_negative_price(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'close_price': [-10.0]
        })
        validator._check_stock_price_non_negative(df)
        assert len(validator.failures) > 0

    def test_negative_price_severity(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'close_price': [-10.0]
        })
        validator._check_stock_price_non_negative(df)
        assert validator.failures[0].severity == SEVERITY_CRITICAL


class TestDQ16YearConsistency:
    def test_valid_years(self, validator):
        df = pd.DataFrame({
            'company_id': [1, 2],
            'year': [2000, 2024]
        })
        validator._check_year_consistency(df, 'test')
        assert len(validator.failures) == 0

    def test_invalid_years(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'year': [1800]
        })
        validator._check_year_consistency(df, 'test')
        assert len(validator.failures) > 0

    def test_invalid_year_severity(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'year': [1800]
        })
        validator._check_year_consistency(df, 'test')
        assert validator.failures[0].severity == SEVERITY_CRITICAL


class TestValidatorTableSpecific:
    def test_validate_companies(self, validator):
        df = pd.DataFrame({
            'id': [1, 2],
            'company_name': ['A', 'B'],
            'sector_id': [1, 2]
        })
        result = validator._validate_companies(df)
        assert list(result.columns) == list(df.columns)

    def test_validate_profitandloss(self, validator):
        df = pd.DataFrame({
            'company_id': [1, 2], 'year': [2020, 2021],
            'revenue': [100, 200], 'operating_profit': [20, 40],
            'operating_profit_margin': [20.0, 20.0],
            'tax_expense': [10, 20], 'profit_before_tax': [50, 100],
            'net_profit': [40, 80], 'eps': [10, 20], 'dividend': [5, 10]
        })
        result = validator._validate_profitandloss(df)
        assert list(result.columns) == list(df.columns)

    def test_validate_balancesheet(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'year': [2020],
            'total_assets': [100], 'total_liabilities': [60],
            'shareholders_equity': [40]
        })
        result = validator._validate_balancesheet(df)
        assert list(result.columns) == list(df.columns)

    def test_validate_stock_prices(self, validator):
        df = pd.DataFrame({
            'company_id': [1], 'date': ['2020-01-01'],
            'close_price': [100.0], 'open_price': [101.0],
            'high_price': [102.0], 'low_price': [99.0]
        })
        result = validator._validate_stock_prices(df)
        assert list(result.columns) == list(df.columns)

    def test_validate_documents(self, validator):
        df = pd.DataFrame({
            'company_id': [1],
            'website_url': ['https://example.com']
        })
        result = validator._validate_documents(df)
        assert list(result.columns) == list(df.columns)


class TestValidationFailure:
    def test_failure_creation(self):
        f = ValidationFailure('DQ-01', SEVERITY_CRITICAL, 'companies', '1', 'id', 'Duplicate')
        assert f.rule_code == 'DQ-01'
        assert f.severity == SEVERITY_CRITICAL
        assert f.table == 'companies'

    def test_to_dict(self):
        f = ValidationFailure('DQ-01', SEVERITY_CRITICAL, 'companies', '1', 'id', 'Duplicate')
        d = f.to_dict()
        assert d['rule_code'] == 'DQ-01'
        assert d['severity'] == SEVERITY_CRITICAL
        assert 'timestamp' in d

    def test_empty_entity_id(self):
        f = ValidationFailure('DQ-01', SEVERITY_CRITICAL, 'companies', None, 'id', 'Duplicate')
        assert f.entity_id == ''


class TestValidatorDump:
    def test_dump_failures(self, tmp_path):
        v = Validator(output_path=str(tmp_path / 'test_failures.csv'))
        v.add_failure('DQ-01', SEVERITY_CRITICAL, 'test', '1', 'id', 'Test')
        v.dump_failures()
        import csv
        with open(tmp_path / 'test_failures.csv') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]['rule_code'] == 'DQ-01'

    def test_no_failures_dump(self, tmp_path, caplog):
        import logging
        caplog.set_level(logging.INFO)
        v = Validator(output_path=str(tmp_path / 'empty.csv'))
        v.dump_failures()
        assert 'No validation failures' in caplog.text
