import csv
import logging
import sqlite3
import os
from pathlib import Path

from src.analytics.ratios import (
    net_profit_margin,
    operating_profit_margin,
    return_on_equity,
    return_on_capital_employed,
    return_on_assets,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    icr_label,
    icr_warning_flag,
    net_debt,
    asset_turnover,
)
from src.analytics.cagr import compute_all_cagrs, get_cagr_for_year
from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
    write_capital_allocation_csv,
)

logger = logging.getLogger(__name__)

DB_PATH = os.getenv('DB_PATH', 'nifty100.db')
OUTPUT_DIR = Path(os.getenv('OUTPUT_DIR', 'output/'))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(financial_ratios)").fetchall()}
    needed = [
        ('return_on_capital_employed', 'REAL'),
        ('return_on_assets', 'REAL'),
        ('interest_coverage', 'REAL'),
        ('icr_label', 'TEXT'),
        ('icr_warning_flag', 'INTEGER'),
        ('high_leverage_flag', 'INTEGER'),
        ('net_debt', 'REAL'),
        ('asset_turnover', 'REAL'),
        ('free_cash_flow', 'REAL'),
        ('cfo_quality_score', 'REAL'),
        ('cfo_quality_label', 'TEXT'),
        ('capex_intensity', 'REAL'),
        ('capex_intensity_label', 'TEXT'),
        ('fcf_conversion_rate', 'REAL'),
        ('capital_allocation_pattern', 'TEXT'),
        ('revenue_cagr_3yr', 'REAL'),
        ('revenue_cagr_3yr_flag', 'TEXT'),
        ('revenue_cagr_5yr', 'REAL'),
        ('revenue_cagr_5yr_flag', 'TEXT'),
        ('revenue_cagr_10yr', 'REAL'),
        ('revenue_cagr_10yr_flag', 'TEXT'),
        ('pat_cagr_3yr', 'REAL'),
        ('pat_cagr_3yr_flag', 'TEXT'),
        ('pat_cagr_5yr', 'REAL'),
        ('pat_cagr_5yr_flag', 'TEXT'),
        ('pat_cagr_10yr', 'REAL'),
        ('pat_cagr_10yr_flag', 'TEXT'),
        ('eps_cagr_3yr', 'REAL'),
        ('eps_cagr_3yr_flag', 'TEXT'),
        ('eps_cagr_5yr', 'REAL'),
        ('eps_cagr_5yr_flag', 'TEXT'),
        ('eps_cagr_10yr', 'REAL'),
        ('eps_cagr_10yr_flag', 'TEXT'),
        ('composite_quality_score', 'REAL'),
        ('roce_percentage', 'REAL'),
        ('roe_percentage', 'REAL'),
        ('net_profit_margin_pct', 'REAL'),
        ('operating_profit_margin_pct', 'REAL'),
        ('return_on_equity_pct', 'REAL'),
        ('debt_to_equity_ratio', 'REAL'),
        ('free_cash_flow_cr', 'REAL'),
        ('capex_cr', 'REAL'),
        ('earnings_per_share', 'REAL'),
        ('book_value_per_share', 'REAL'),
        ('dividend_payout_ratio_pct', 'REAL'),
        ('total_debt_cr', 'REAL'),
        ('cash_from_operations_cr', 'REAL'),
        ('revenue_cagr_5yr', 'REAL'),
        ('pat_cagr_5yr', 'REAL'),
        ('eps_cagr_5yr', 'REAL'),
    ]
    for col_name, col_type in needed:
        if col_name.lower() not in {c.lower() for c in existing}:
            try:
                conn.execute(f"ALTER TABLE financial_ratios ADD COLUMN {col_name} {col_type}")
                logger.info(f"Added column {col_name} to financial_ratios")
            except Exception as e:
                logger.debug(f"Could not add column {col_name}: {e}")


def get_sector_map(conn):
    rows = conn.execute("""
        SELECT c.company_id, s.sector_name
        FROM companies c
        JOIN sectors s ON c.sector_id = s.sector_id
    """).fetchall()
    return {r['company_id']: r['sector_name'] for r in rows}


def get_company_ticker_map(conn):
    rows = conn.execute("SELECT company_id, ticker FROM companies").fetchall()
    return {r['company_id']: r['ticker'] for r in rows}


def get_face_value_map():
    import pandas as pd
    df = pd.read_excel('data/companies.xlsx', header=None)
    fv_map = {}
    for i in range(2, len(df)):
        ticker = str(df.iloc[i, 0]).strip()
        face_val = df.iloc[i, 8]
        if pd.notna(face_val):
            try:
                fv_map[ticker] = float(face_val)
            except (ValueError, TypeError):
                pass
    return fv_map


def load_all_data(conn):
    pl_rows = conn.execute("""
        SELECT company_id, year, revenue, operating_profit, operating_profit_margin,
               other_income, interest_expense, net_profit, eps, dividend_payout_ratio
        FROM profitandloss
        ORDER BY company_id, year
    """).fetchall()

    bs_rows = conn.execute("""
        SELECT company_id, year, share_capital, reserves_and_surplus, total_debt,
               total_assets, investments, book_value_per_share
        FROM balancesheet
        ORDER BY company_id, year
    """).fetchall()

    cf_rows = conn.execute("""
        SELECT company_id, year, cash_from_operations, cash_from_investing, cash_from_financing
        FROM cashflow
        ORDER BY company_id, year
    """).fetchall()

    data_by_company = {}
    for r in pl_rows:
        cid = r['company_id']
        if cid not in data_by_company:
            data_by_company[cid] = {}
        data_by_company[cid][r['year']] = {
            'pl': dict(r),
            'bs': {},
            'cf': {},
        }

    for r in bs_rows:
        cid = r['company_id']
        if cid in data_by_company and r['year'] in data_by_company[cid]:
            data_by_company[cid][r['year']]['bs'] = dict(r)
        elif cid not in data_by_company:
            data_by_company[cid] = {r['year']: {'pl': {}, 'bs': dict(r), 'cf': {}}}

    for r in cf_rows:
        cid = r['company_id']
        if cid in data_by_company and r['year'] in data_by_company[cid]:
            data_by_company[cid][r['year']]['cf'] = dict(r)
        elif cid not in data_by_company:
            data_by_company[cid] = {r['year']: {'pl': {}, 'bs': {}, 'cf': dict(r)}}

    return data_by_company


def compute_ebit(operating_profit, other_income):
    return (operating_profit or 0) + (other_income or 0)


def run_engine():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()
    edge_cases = []

    try:
        ensure_columns(conn)
        sector_map = get_sector_map(conn)
        ticker_map = get_company_ticker_map(conn)
        face_value_map = get_face_value_map()
        data_by_company = load_all_data(conn)

        conn.execute("DELETE FROM financial_ratios")
        conn.commit()

        capital_allocation_records = []
        total_rows = 0

        for company_id in sorted(data_by_company.keys()):
            years = sorted(data_by_company[company_id].keys())
            sector_name = sector_map.get(company_id, 'Unknown')
            is_financials = (sector_name == 'Financials')
            ticker = ticker_map.get(company_id)

            pl_records = []
            for year in years:
                d = data_by_company[company_id][year]
                pl = d['pl']
                if pl:
                    pl_records.append(pl)

            cagr_results = compute_all_cagrs(pl_records)

            combined_records = []
            for year in years:
                d = data_by_company[company_id][year]
                rec = {}
                rec.update(d['pl'])
                rec.update(d['cf'])
                combined_records.append(rec)

            cfo_val, cfo_label = cfo_quality_score(combined_records)

            for year in years:
                d = data_by_company[company_id][year]
                pl = d['pl']
                bs = d['bs']
                cf = d['cf']

                if not pl and not bs and not cf:
                    continue

                revenue = pl.get('revenue') if pl else None
                operating_profit_val = pl.get('operating_profit') if pl else None
                opm_declared = pl.get('operating_profit_margin') if pl else None
                other_income_val = pl.get('other_income') if pl else None
                interest = pl.get('interest_expense') if pl else None
                net_profit_val = pl.get('net_profit') if pl else None
                eps_val = pl.get('eps') if pl else None
                dividend_payout = pl.get('dividend_payout_ratio') if pl else None

                equity_capital = bs.get('share_capital') if bs else None
                reserves = bs.get('reserves_and_surplus') if bs else None
                borrowings = bs.get('total_debt') if bs else None
                total_assets = bs.get('total_assets') if bs else None
                investments_val = bs.get('investments') if bs else None
                if bs and bs.get('share_capital') and bs.get('share_capital') > 0:
                    sc = bs['share_capital']
                    rs = bs.get('reserves_and_surplus') or 0
                    fv = face_value_map.get(ticker, 10)
                    bv_per_share = (sc + rs) * fv / sc
                else:
                    bv_per_share = bs.get('book_value_per_share') if bs else None

                cfo = cf.get('cash_from_operations') if cf else None
                cfi = cf.get('cash_from_investing') if cf else None
                cff = cf.get('cash_from_financing') if cf else None

                npm = net_profit_margin(net_profit_val, revenue)
                opm = operating_profit_margin(operating_profit_val, revenue, opm_declared)
                roe = return_on_equity(net_profit_val, equity_capital, reserves)
                ebit = compute_ebit(operating_profit_val, other_income_val)
                roce = return_on_capital_employed(ebit, equity_capital, reserves, borrowings)
                roa = return_on_assets(net_profit_val, total_assets)

                de = debt_to_equity(borrowings, equity_capital, reserves)
                hl_flag = high_leverage_flag(de, sector_name)
                icr = interest_coverage_ratio(operating_profit_val, other_income_val, interest)
                icr_lbl = icr_label(icr)
                icr_warn = icr_warning_flag(icr)
                nd = net_debt(borrowings, investments_val)
                at = asset_turnover(revenue, total_assets)

                fcf = free_cash_flow(cfo, cfi)
                cap_int, cap_label = capex_intensity(cfi, revenue)
                fcf_conv = fcf_conversion_rate(fcf, operating_profit_val)
                alloc_pattern = capital_allocation_pattern(cfo, cfi, cff)

                cap_rec = {
                    'company_id': company_id,
                    'year': year,
                    'cash_from_operations': cfo,
                    'cash_from_investing': cfi,
                    'cash_from_financing': cff,
                    'allocation_pattern': alloc_pattern,
                }
                capital_allocation_records.append(cap_rec)

                rev_cagr_3yr, rev_cagr_3yr_flag = get_cagr_for_year(cagr_results, 'revenue', 3, year)
                rev_cagr_5yr, rev_cagr_5yr_flag = get_cagr_for_year(cagr_results, 'revenue', 5, year)
                rev_cagr_10yr, rev_cagr_10yr_flag = get_cagr_for_year(cagr_results, 'revenue', 10, year)
                pat_cagr_3yr, pat_cagr_3yr_flag = get_cagr_for_year(cagr_results, 'pat', 3, year)
                pat_cagr_5yr, pat_cagr_5yr_flag = get_cagr_for_year(cagr_results, 'pat', 5, year)
                pat_cagr_10yr, pat_cagr_10yr_flag = get_cagr_for_year(cagr_results, 'pat', 10, year)
                eps_cagr_3yr, eps_cagr_3yr_flag = get_cagr_for_year(cagr_results, 'eps', 3, year)
                eps_cagr_5yr, eps_cagr_5yr_flag = get_cagr_for_year(cagr_results, 'eps', 5, year)
                eps_cagr_10yr, eps_cagr_10yr_flag = get_cagr_for_year(cagr_results, 'eps', 10, year)

                quality_scores = [v for v in [npm, roe, opm, fcf_conv] if v is not None]
                composite_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

                roce_src = None
                roe_src = None

                if ticker:
                    try:
                        import pandas as pd
                        companies_df = pd.read_excel('data/companies.xlsx', header=None)
                        for i in range(2, len(companies_df)):
                            if str(companies_df.iloc[i, 0]).strip() == ticker:
                                roce_src = companies_df.iloc[i, 10]
                                roe_src = companies_df.iloc[i, 11]
                                break
                    except Exception:
                        pass

                if roce is not None and roce_src is not None:
                    try:
                        roce_src_val = float(roce_src)
                        diff = abs(roce - roce_src_val)
                        if diff > 5.0:
                            msg = (f"Company {company_id} ({ticker}) year {year}: ROCE computed={roce:.2f}%, "
                                   f"source={roce_src_val:.2f}%, diff={diff:.2f}%")
                            edge_cases.append({
                                'company_id': company_id,
                                'ticker': ticker,
                                'year': year,
                                'metric': 'ROCE',
                                'computed': roce,
                                'source': roce_src_val,
                                'diff': diff,
                                'category': 'formula discrepancy',
                                'message': msg,
                            })
                            logger.warning(msg)
                    except (ValueError, TypeError):
                        pass

                if roe is not None and roe_src is not None:
                    try:
                        roe_src_val = float(roe_src)
                        diff = abs(roe - roe_src_val)
                        if diff > 5.0:
                            msg = (f"Company {company_id} ({ticker}) year {year}: ROE computed={roe:.2f}%, "
                                   f"source={roe_src_val:.2f}%, diff={diff:.2f}%")
                            edge_cases.append({
                                'company_id': company_id,
                                'ticker': ticker,
                                'year': year,
                                'metric': 'ROE',
                                'computed': roe,
                                'source': roe_src_val,
                                'diff': diff,
                                'category': 'formula discrepancy',
                                'message': msg,
                            })
                            logger.warning(msg)
                    except (ValueError, TypeError):
                        pass

                conn.execute("""
                    INSERT OR REPLACE INTO financial_ratios (
                        company_id, year,
                        net_profit_margin, operating_profit_margin,
                        return_on_equity, return_on_capital_employed, return_on_assets,
                        debt_to_equity_ratio, interest_coverage, icr_label,
                        icr_warning_flag, high_leverage_flag, net_debt,
                        asset_turnover, free_cash_flow,
                        cfo_quality_score, cfo_quality_label,
                        capex_intensity, capex_intensity_label,
                        fcf_conversion_rate, capital_allocation_pattern,
                        revenue_cagr_3yr, revenue_cagr_3yr_flag,
                        revenue_cagr_5yr, revenue_cagr_5yr_flag,
                        revenue_cagr_10yr, revenue_cagr_10yr_flag,
                        pat_cagr_3yr, pat_cagr_3yr_flag,
                        pat_cagr_5yr, pat_cagr_5yr_flag,
                        pat_cagr_10yr, pat_cagr_10yr_flag,
                        eps_cagr_3yr, eps_cagr_3yr_flag,
                        eps_cagr_5yr, eps_cagr_5yr_flag,
                        eps_cagr_10yr, eps_cagr_10yr_flag,
                        composite_quality_score,
                        roce_percentage, roe_percentage,
                        net_profit_margin_pct, operating_profit_margin_pct,
                        return_on_equity_pct,
                        free_cash_flow_cr, capex_cr,
                        earnings_per_share, book_value_per_share,
                        dividend_payout_ratio_pct, total_debt_cr, cash_from_operations_cr
                    ) VALUES (
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                    )
                """, (
                    company_id, year,
                    npm, opm,
                    roe, roce, roa,
                    de, icr, icr_lbl,
                    1 if icr_warn else 0, 1 if hl_flag else 0, nd,
                    at, fcf,
                    cfo_val, cfo_label,
                    cap_int, cap_label,
                    fcf_conv, alloc_pattern,
                    rev_cagr_3yr, rev_cagr_3yr_flag,
                    rev_cagr_5yr, rev_cagr_5yr_flag,
                    rev_cagr_10yr, rev_cagr_10yr_flag,
                    pat_cagr_3yr, pat_cagr_3yr_flag,
                    pat_cagr_5yr, pat_cagr_5yr_flag,
                    pat_cagr_10yr, pat_cagr_10yr_flag,
                    eps_cagr_3yr, eps_cagr_3yr_flag,
                    eps_cagr_5yr, eps_cagr_5yr_flag,
                    eps_cagr_10yr, eps_cagr_10yr_flag,
                    composite_quality,
                    roce, roe,
                    npm, opm,
                    roe,
                    fcf, cap_int,
                    eps_val, bv_per_share,
                    dividend_payout, borrowings, cfo,
                ))
                total_rows += 1

        conn.commit()

        write_capital_allocation_csv(capital_allocation_records, str(OUTPUT_DIR / 'capital_allocation.csv'))

        edge_path = OUTPUT_DIR / 'ratio_edge_cases.log'
        with open(edge_path, 'w') as f:
            f.write("Ratio Edge Cases Log\n")
            f.write("=" * 80 + "\n\n")
            for ec in edge_cases:
                f.write(f"Company: {ec['company_id']} ({ec.get('ticker')}) | Year: {ec['year']}\n")
                f.write(f"Metric: {ec['metric']}\n")
                f.write(f"Computed: {ec['computed']:.2f} | Source: {ec['source']:.2f} | Diff: {ec['diff']:.2f}\n")
                f.write(f"Category: {ec['category']}\n")
                f.write(f"Message: {ec['message']}\n")
                f.write("-" * 60 + "\n\n")

        if not edge_cases:
            with open(edge_path, 'a') as f:
                f.write("No edge case anomalies found.\n")

        logger.info(f"Total rows inserted into financial_ratios: {total_rows}")
        logger.info(f"Edge cases logged: {len(edge_cases)}")
        return total_rows, edge_cases

    finally:
        conn.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    run_engine()
