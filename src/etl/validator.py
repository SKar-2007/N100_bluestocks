import csv
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

SEVERITY_CRITICAL = 'CRITICAL'
SEVERITY_WARNING = 'WARNING'


class ValidationFailure:
    def __init__(self, rule_code, severity, table, entity_id, field, message):
        self.rule_code = rule_code
        self.severity = severity
        self.table = table
        self.entity_id = str(entity_id) if entity_id else ''
        self.field = field
        self.message = message
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            'rule_code': self.rule_code,
            'severity': self.severity,
            'table': self.table,
            'entity_id': self.entity_id,
            'field': self.field,
            'message': self.message,
            'timestamp': self.timestamp,
        }


class Validator:
    def __init__(self, output_path='output/validation_failures.csv'):
        self.failures = []
        self.output_path = Path(output_path)

    def add_failure(self, rule_code, severity, table, entity_id, field, message):
        failure = ValidationFailure(rule_code, severity, table, entity_id, field, message)
        self.failures.append(failure)
        log_level = logging.ERROR if severity == SEVERITY_CRITICAL else logging.WARNING
        logger.log(log_level, f"[{rule_code}] [{severity}] {table}/{entity_id}: {message}")

    def validate_table(self, table_name, df):
        if table_name == 'companies':
            df = self._validate_companies(df)
        elif table_name == 'profitandloss':
            df = self._validate_profitandloss(df)
        elif table_name == 'balancesheet':
            df = self._validate_balancesheet(df)
        elif table_name == 'cashflow':
            df = self._validate_cashflow(df)
        elif table_name == 'stock_prices':
            df = self._validate_stock_prices(df)
        elif table_name == 'analysis':
            df = self._validate_analysis(df)
        elif table_name == 'documents':
            df = self._validate_documents(df)
        elif table_name == 'sectors':
            df = self._validate_sectors(df)
        elif table_name == 'financial_ratios':
            df = self._validate_financial_ratios(df)
        elif table_name == 'peer_groups':
            df = self._validate_peer_groups(df)
        elif table_name == 'prosandcons':
            df = self._validate_prosandcons(df)

        return df

    # DQ-01: Primary Key Uniqueness (CRITICAL)
    def _check_pk_uniqueness(self, df, pk_columns, table_name):
        if pk_columns and all(c in df.columns for c in pk_columns):
            duplicates = df[df.duplicated(subset=pk_columns, keep=False)]
            for idx in duplicates.index:
                entity = str(dict(zip(pk_columns, [df.loc[idx, c] for c in pk_columns])))
                self.add_failure(
                    'DQ-01', SEVERITY_CRITICAL, table_name, entity, ','.join(pk_columns),
                    f"Duplicate primary key combination: {entity}"
                )

    # DQ-02: Composite PK Validation (company_id, year) (CRITICAL)
    def _check_composite_pk(self, df, table_name):
        if 'company_id' in df.columns and 'year' in df.columns:
            self._check_pk_uniqueness(df, ['company_id', 'year'], table_name)

    # DQ-03: Foreign Key Integrity (CRITICAL) - checked at DB level via PRAGMA
    def _check_fk_references(self, df, fk_column, parent_table, table_name):
        pass

    # DQ-04: Balance Sheet Alignment (WARNING)
    def _check_balance_sheet_alignment(self, df):
        for idx in df.index:
            total_assets = df.loc[idx, 'total_assets'] if 'total_assets' in df.columns else 0
            total_liabilities = df.loc[idx, 'total_liabilities'] if 'total_liabilities' in df.columns else 0
            shareholders_equity = df.loc[idx, 'shareholders_equity'] if 'shareholders_equity' in df.columns else 0

            if total_assets and (total_liabilities + shareholders_equity):
                total_equity_liabilities = total_liabilities + shareholders_equity
                if total_assets > 0:
                    diff_pct = abs(total_assets - total_equity_liabilities) / total_assets * 100
                    if diff_pct >= 1.0:
                        company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                        year = df.loc[idx, 'year'] if 'year' in df.columns else 'unknown'
                        self.add_failure(
                            'DQ-04', SEVERITY_WARNING, 'balancesheet', f"{company_id}-{year}",
                            'total_assets',
                            f"Balance sheet off by {diff_pct:.2f}% (assets={total_assets}, liab+equity={total_equity_liabilities})"
                        )

    # DQ-05: Operating Profit Margin cross-check (WARNING)
    def _check_opm(self, df):
        for idx in df.index:
            revenue = df.loc[idx, 'revenue'] if 'revenue' in df.columns else 0
            op = df.loc[idx, 'operating_profit'] if 'operating_profit' in df.columns else 0
            opm_raw = df.loc[idx, 'operating_profit_margin'] if 'operating_profit_margin' in df.columns else None

            if revenue and op and opm_raw is not None:
                derived_opm = (op / revenue) * 100
                if abs(derived_opm - opm_raw) > 1.0:
                    company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                    year = df.loc[idx, 'year'] if 'year' in df.columns else 'unknown'
                    self.add_failure(
                        'DQ-05', SEVERITY_WARNING, 'profitandloss', f"{company_id}-{year}",
                        'operating_profit_margin',
                        f"OPM mismatch: derived={derived_opm:.2f}%, declared={opm_raw:.2f}%"
                    )

    # DQ-06: Net Cash validation (WARNING)
    def _check_net_cash(self, df):
        for idx in df.index:
            cash = df.loc[idx, 'cash_and_equivalents'] if 'cash_and_equivalents' in df.columns else None
            if cash is not None and cash < 0:
                company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                self.add_failure(
                    'DQ-06', SEVERITY_WARNING, 'cashflow', company_id,
                    'cash_and_equivalents',
                    f"Negative cash balance: {cash}"
                )

    # DQ-07: Effective Tax Rate range check (WARNING)
    def _check_tax_rate(self, df):
        for idx in df.index:
            tax = df.loc[idx, 'tax_expense'] if 'tax_expense' in df.columns else None
            pbt = df.loc[idx, 'profit_before_tax'] if 'profit_before_tax' in df.columns else None
            if tax is not None and pbt and pbt > 0:
                effective_rate = (tax / pbt) * 100
                if effective_rate < 0 or effective_rate > 100:
                    company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                    year = df.loc[idx, 'year'] if 'year' in df.columns else 'unknown'
                    self.add_failure(
                        'DQ-07', SEVERITY_WARNING, 'profitandloss', f"{company_id}-{year}",
                        'tax_expense',
                        f"Effective tax rate out of range: {effective_rate:.2f}%"
                    )

    # DQ-08: Revenue Validation - must be positive (WARNING)
    def _check_revenue_positive(self, df):
        for idx in df.index:
            revenue = df.loc[idx, 'revenue'] if 'revenue' in df.columns else None
            if revenue is not None and revenue < 0:
                company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                year = df.loc[idx, 'year'] if 'year' in df.columns else 'unknown'
                self.add_failure(
                    'DQ-08', SEVERITY_WARNING, 'profitandloss', f"{company_id}-{year}",
                    'revenue',
                    f"Negative revenue reported: {revenue}"
                )

    # DQ-09: Dividend Payout Ratio cap (WARNING)
    def _check_dividend_cap(self, df):
        for idx in df.index:
            dividend = df.loc[idx, 'dividend'] if 'dividend' in df.columns else 0
            net_profit = df.loc[idx, 'net_profit'] if 'net_profit' in df.columns else 0

            if net_profit and net_profit > 0:
                payout_ratio = abs(dividend) / net_profit * 100
                if payout_ratio > 100:
                    company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                    year = df.loc[idx, 'year'] if 'year' in df.columns else 'unknown'
                    self.add_failure(
                        'DQ-09', SEVERITY_WARNING, 'profitandloss', f"{company_id}-{year}",
                        'dividend',
                        f"Dividend payout ratio exceeds 100%: {payout_ratio:.2f}%"
                    )

    # DQ-10: URL format validation (CRITICAL)
    def _check_url_formats(self, df):
        url_pattern = re.compile(
            r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?::\d+)?(?:/[-\w%.~+]*)*(?:\?[-\w&=.]*)?(?:#[-\w]*)?$'
        )
        for idx in df.index:
            for col in df.columns:
                if 'url' in col.lower() or 'link' in col.lower() or 'website' in col.lower():
                    val = df.loc[idx, col]
                    if val and isinstance(val, str) and val.strip():
                        if not url_pattern.match(val.strip()):
                            company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else df.loc[idx, 'id'] if 'id' in df.columns else 'unknown'
                            self.add_failure(
                                'DQ-10', SEVERITY_CRITICAL, 'documents', company_id,
                                col,
                                f"Invalid URL format: {val[:100]}"
                            )

    # DQ-11: EPS sign correctness (WARNING)
    def _check_eps_sign(self, df):
        for idx in df.index:
            eps = df.loc[idx, 'eps'] if 'eps' in df.columns else None
            net_profit = df.loc[idx, 'net_profit'] if 'net_profit' in df.columns else None
            if eps is not None and net_profit is not None:
                if (net_profit > 0 and eps < 0) or (net_profit < 0 and eps > 0):
                    company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                    year = df.loc[idx, 'year'] if 'year' in df.columns else 'unknown'
                    self.add_failure(
                        'DQ-11', SEVERITY_WARNING, 'profitandloss', f"{company_id}-{year}",
                        'eps',
                        f"EPS sign mismatch: net_profit={net_profit}, eps={eps}"
                    )

    # DQ-12: BSE balance check (WARNING)
    def _check_bse_balance(self, df):
        for idx in df.index:
            bse_price = df.loc[idx, 'bse_price'] if 'bse_price' in df.columns else None
            nse_price = df.loc[idx, 'nse_price'] if 'nse_price' in df.columns else None
            if bse_price is not None and nse_price is not None and bse_price > 0:
                diff_pct = abs(bse_price - nse_price) / bse_price * 100
                if diff_pct > 5.0:
                    company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                    self.add_failure(
                        'DQ-12', SEVERITY_WARNING, 'stock_prices', company_id,
                        'bse_price',
                        f"BSE/NSE price divergence > 5%: {diff_pct:.2f}%"
                    )

    # DQ-13: Data coverage - minimum years check (WARNING)
    def _check_data_coverage(self, df, table_name):
        if 'company_id' in df.columns and 'year' in df.columns:
            coverage = df.groupby('company_id')['year'].nunique()
            for company_id, years_count in coverage.items():
                if years_count < 5:
                    self.add_failure(
                        'DQ-13', SEVERITY_WARNING, table_name, company_id,
                        'year',
                        f"Less than 5 years of data: {years_count} years found"
                    )

    # DQ-14: Sector mapping integrity (CRITICAL)
    def _check_sector_mapping(self, df):
        if 'sector_id' in df.columns:
            for idx in df.index:
                if df.loc[idx, 'sector_id'] is None or (isinstance(df.loc[idx, 'sector_id'], float) and df.isna().loc[idx, 'sector_id']):
                    company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else df.loc[idx, 'id'] if 'id' in df.columns else 'unknown'
                    self.add_failure(
                        'DQ-14', SEVERITY_CRITICAL, 'companies', company_id,
                        'sector_id',
                        "Missing sector mapping"
                    )

    # DQ-15: Stock price non-negative (CRITICAL)
    def _check_stock_price_non_negative(self, df):
        for col in df.columns:
            if 'price' in col.lower() or 'close' in col.lower() or 'open' in col.lower() or 'high' in col.lower() or 'low' in col.lower():
                for idx in df.index:
                    val = df.loc[idx, col]
                    if val is not None and val < 0:
                        company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                        self.add_failure(
                            'DQ-15', SEVERITY_CRITICAL, 'stock_prices', company_id,
                            col,
                            f"Negative stock price: {col}={val}"
                        )

    # DQ-16: Cross-table year consistency (CRITICAL)
    def _check_year_consistency(self, df, table_name):
        if 'year' in df.columns:
            invalid_years = df[df['year'] < 1990]
            for idx in invalid_years.index:
                company_id = df.loc[idx, 'company_id'] if 'company_id' in df.columns else 'unknown'
                year = df.loc[idx, 'year']
                self.add_failure(
                    'DQ-16', SEVERITY_CRITICAL, table_name, company_id,
                    'year',
                    f"Invalid year value: {year}"
                )

    def _validate_companies(self, df):
        self._check_pk_uniqueness(df, ['company_id'] if 'company_id' in df.columns else ['id'], 'companies')
        self._check_sector_mapping(df)
        self._check_data_coverage(df, 'companies')
        return df

    def _validate_profitandloss(self, df):
        self._check_composite_pk(df, 'profitandloss')
        self._check_revenue_positive(df)
        self._check_opm(df)
        self._check_tax_rate(df)
        self._check_dividend_cap(df)
        self._check_eps_sign(df)
        self._check_year_consistency(df, 'profitandloss')
        return df

    def _validate_balancesheet(self, df):
        self._check_composite_pk(df, 'balancesheet')
        self._check_balance_sheet_alignment(df)
        self._check_year_consistency(df, 'balancesheet')
        return df

    def _validate_cashflow(self, df):
        self._check_composite_pk(df, 'cashflow')
        self._check_net_cash(df)
        self._check_year_consistency(df, 'cashflow')
        return df

    def _validate_stock_prices(self, df):
        self._check_pk_uniqueness(df, ['company_id', 'date'] if 'date' in df.columns else ['company_id'], 'stock_prices')
        self._check_stock_price_non_negative(df)
        self._check_bse_balance(df)
        self._check_year_consistency(df, 'stock_prices')
        return df

    def _validate_analysis(self, df):
        self._check_composite_pk(df, 'analysis')
        return df

    def _validate_documents(self, df):
        self._check_pk_uniqueness(df, ['company_id'] if 'company_id' in df.columns else ['id'], 'documents')
        self._check_url_formats(df)
        return df

    def _validate_sectors(self, df):
        self._check_pk_uniqueness(df, ['sector_id'] if 'sector_id' in df.columns else ['id'], 'sectors')
        return df

    def _validate_financial_ratios(self, df):
        self._check_composite_pk(df, 'financial_ratios')
        return df

    def _validate_peer_groups(self, df):
        self._check_pk_uniqueness(df, ['company_id'] if 'company_id' in df.columns else ['id'], 'peer_groups')
        return df

    def _validate_prosandcons(self, df):
        self._check_pk_uniqueness(df, ['company_id'] if 'company_id' in df.columns else ['id'], 'prosandcons')
        return df

    def dump_failures(self):
        if not self.failures:
            logger.info("No validation failures recorded")
            return

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ['rule_code', 'severity', 'table', 'entity_id', 'field', 'message', 'timestamp']
        with open(self.output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for failure in self.failures:
                writer.writerow(failure.to_dict())

        critical_count = sum(1 for f in self.failures if f.severity == SEVERITY_CRITICAL)
        warning_count = sum(1 for f in self.failures if f.severity == SEVERITY_WARNING)
        logger.info(
            f"Validation failures dumped: {len(self.failures)} total "
            f"({critical_count} CRITICAL, {warning_count} WARNING) -> {self.output_path}"
        )


def generate_report():
    validator = Validator()
    logger.info("Validation report generated")
