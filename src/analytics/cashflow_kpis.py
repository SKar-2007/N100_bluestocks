import csv
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def free_cash_flow(cash_from_operations, cash_from_investing):
    if cash_from_operations is None and cash_from_investing is None:
        return None
    return (cash_from_operations or 0) + (cash_from_investing or 0)


def cfo_quality_score(records, pat_key='net_profit', cfo_key='cash_from_operations'):
    cfo_values = []
    pat_values = []

    for r in records:
        cfo = r.get(cfo_key)
        pat = r.get(pat_key)
        if cfo is not None and pat is not None:
            cfo_values.append(cfo)
            pat_values.append(pat)

    if len(cfo_values) < 3:
        return None, None

    ratios = []
    for cfo, pat in zip(cfo_values, pat_values):
        if pat != 0:
            ratios.append(cfo / pat)

    if not ratios:
        return None, None

    avg = sum(ratios) / len(ratios)

    if avg > 1.0:
        label = 'High Quality'
    elif avg >= 0.5:
        label = 'Moderate'
    else:
        label = 'Accrual Risk'

    return avg, label


def capex_intensity(investing_activity, sales):
    if sales is None or sales == 0:
        return None, None
    intensity = abs(investing_activity or 0) / sales * 100

    if intensity < 3:
        label = 'Asset Light'
    elif intensity <= 8:
        label = 'Moderate'
    else:
        label = 'Capital Intensive'

    return intensity, label


def fcf_conversion_rate(fcf, operating_profit):
    if operating_profit is None or operating_profit == 0:
        return None
    if fcf is None:
        return None
    return (fcf / operating_profit) * 100


def capital_allocation_pattern(cfo, cfi, cff):
    cfo_s = 1 if cfo and cfo > 0 else (-1 if cfo and cfo < 0 else 0)
    cfi_s = 1 if cfi and cfi > 0 else (-1 if cfi and cfi < 0 else 0)
    cff_s = 1 if cff and cff > 0 else (-1 if cff and cff < 0 else 0)

    pattern = (cfo_s, cfi_s, cff_s)

    if pattern == (1, -1, -1):
        return 'Reinvestor'
    elif pattern == (1, 1, -1):
        return 'Liquidating Assets'
    elif pattern == (-1, 1, 1):
        return 'Distress Signal'
    elif pattern == (-1, -1, 1):
        return 'Growth Funded by Debt'
    elif pattern == (1, 1, 1):
        return 'Cash Accumulator'
    elif pattern == (-1, -1, -1):
        return 'Pre-Revenue'
    elif pattern == (1, -1, 1):
        return 'Mixed'
    else:
        return 'Other'


def write_capital_allocation_csv(records, output_path='output/capital_allocation.csv'):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ['company_id', 'year', 'cfo_sign', 'cfi_sign', 'cff_sign', 'pattern_label']
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({
                'company_id': r.get('company_id'),
                'year': r.get('year'),
                'cfo_sign': 1 if r.get('cash_from_operations', 0) and r['cash_from_operations'] > 0 else (-1 if r.get('cash_from_operations', 0) and r['cash_from_operations'] < 0 else 0),
                'cfi_sign': 1 if r.get('cash_from_investing', 0) and r['cash_from_investing'] > 0 else (-1 if r.get('cash_from_investing', 0) and r['cash_from_investing'] < 0 else 0),
                'cff_sign': 1 if r.get('cash_from_financing', 0) and r['cash_from_financing'] > 0 else (-1 if r.get('cash_from_financing', 0) and r['cash_from_financing'] < 0 else 0),
                'pattern_label': r.get('allocation_pattern', capital_allocation_pattern(
                    r.get('cash_from_operations'), r.get('cash_from_investing'), r.get('cash_from_financing')
                )),
            })

    logger.info(f"Capital allocation written to {output_path}")
    return output_path
