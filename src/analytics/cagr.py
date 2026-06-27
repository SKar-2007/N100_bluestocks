import logging

logger = logging.getLogger(__name__)

CAGR_DECLINE_TO_LOSS = 'DECLINE_TO_LOSS'
CAGR_TURNAROUND = 'TURNAROUND'
CAGR_BOTH_NEGATIVE = 'BOTH_NEGATIVE'
CAGR_ZERO_BASE = 'ZERO_BASE'
CAGR_INSUFFICIENT = 'INSUFFICIENT'


def compute_cagr(start_value, end_value, num_years):
    if num_years is None or num_years <= 0:
        return None, CAGR_INSUFFICIENT

    if start_value is None or end_value is None:
        return None, CAGR_INSUFFICIENT

    if start_value > 0 and end_value > 0:
        ratio = end_value / start_value
        cagr = (ratio ** (1.0 / num_years) - 1) * 100
        return cagr, None

    if start_value == 0:
        return None, CAGR_ZERO_BASE

    if start_value > 0 and end_value <= 0:
        return None, CAGR_DECLINE_TO_LOSS

    if start_value <= 0 and end_value > 0:
        return None, CAGR_TURNAROUND

    if start_value <= 0 and end_value <= 0:
        return None, CAGR_BOTH_NEGATIVE

    return None, CAGR_INSUFFICIENT


def get_sorted_values(records, key):
    sorted_recs = sorted(records, key=lambda r: r.get('year', 0))
    return [(r.get('year'), r.get(key)) for r in sorted_recs if r.get(key) is not None]


def window_cagr(values_by_year, end_year, window_years, key='value'):
    if len(values_by_year) < 2:
        return None, CAGR_INSUFFICIENT

    sorted_years = sorted(values_by_year.keys())
    if end_year not in values_by_year:
        return None, CAGR_INSUFFICIENT

    start_year = end_year - window_years
    available = [y for y in sorted_years if y <= end_year]

    if len(available) < 2:
        return None, CAGR_INSUFFICIENT

    end_val = values_by_year[end_year]

    if start_year in values_by_year:
        start_val = values_by_year[start_year]
    else:
        earlier = [y for y in available if y <= end_year - window_years + 1]
        if not earlier:
            return None, CAGR_INSUFFICIENT
        start_val = values_by_year[earlier[0]]
        actual_years = end_year - earlier[0]
        if actual_years < 1:
            return None, CAGR_INSUFFICIENT
        return compute_cagr(start_val, end_val, actual_years)

    return compute_cagr(start_val, end_val, window_years)


def compute_all_cagrs(records, revenue_key='revenue', pat_key='net_profit', eps_key='eps'):
    rev_by_year = {r.get('year'): r.get(revenue_key) for r in records if r.get(revenue_key) is not None}
    pat_by_year = {r.get('year'): r.get(pat_key) for r in records if r.get(pat_key) is not None}
    eps_by_year = {r.get('year'): r.get(eps_key) for r in records if r.get(eps_key) is not None}

    years = sorted(set(list(rev_by_year.keys()) + list(pat_by_year.keys()) + list(eps_by_year.keys())))

    result = {}
    for window in [3, 5, 10]:
        for year in years:
            prefix = f'revenue_cagr_{window}yr'
            val, flag = window_cagr(rev_by_year, year, window)
            result[f'{prefix}_{year}'] = (val, flag)

            prefix = f'pat_cagr_{window}yr'
            val, flag = window_cagr(pat_by_year, year, window)
            result[f'{prefix}_{year}'] = (val, flag)

            prefix = f'eps_cagr_{window}yr'
            val, flag = window_cagr(eps_by_year, year, window)
            result[f'{prefix}_{year}'] = (val, flag)

    return result


def get_cagr_for_year(cagr_results, metric, window, year):
    key = f'{metric}_cagr_{window}yr_{year}'
    return cagr_results.get(key, (None, CAGR_INSUFFICIENT))
