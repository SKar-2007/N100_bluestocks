import logging

logger = logging.getLogger(__name__)


def net_profit_margin(net_profit, sales):
    if net_profit is None:
        return None
    if sales is None or sales == 0:
        return None
    return (net_profit / sales) * 100


def operating_profit_margin(operating_profit, sales, declared_opm=None):
    if sales is None or sales == 0:
        return None
    if operating_profit is None:
        return None
    result = (operating_profit / sales) * 100
    if declared_opm is not None and result is not None:
        diff = abs(result - declared_opm)
        if diff > 1.0:
            logger.warning(
                f"OPM cross-check mismatch: computed={result:.2f}%, "
                f"declared={declared_opm:.2f}%, diff={diff:.2f}%"
            )
    return result


def return_on_equity(net_profit, equity_capital, reserves):
    if net_profit is None:
        return None
    equity = (equity_capital or 0) + (reserves or 0)
    if equity <= 0:
        return None
    return (net_profit / equity) * 100


def return_on_capital_employed(ebit, equity_capital, reserves, borrowings):
    if ebit is None:
        return None
    capital = (equity_capital or 0) + (reserves or 0) + (borrowings or 0)
    if capital == 0:
        return None
    return (ebit / capital) * 100


def return_on_assets(net_profit, total_assets):
    if net_profit is None:
        return None
    if total_assets is None or total_assets == 0:
        return None
    return (net_profit / total_assets) * 100


def debt_to_equity(borrowings, equity_capital, reserves):
    if borrowings is None or borrowings == 0:
        return 0.0
    equity = (equity_capital or 0) + (reserves or 0)
    if equity == 0:
        return None
    return borrowings / equity


def high_leverage_flag(de_ratio, broad_sector):
    if de_ratio is None:
        return False
    if de_ratio > 5 and broad_sector != 'Financials':
        return True
    return False


def interest_coverage_ratio(operating_profit, other_income, interest):
    if interest is None or interest == 0:
        return None
    return ((operating_profit or 0) + (other_income or 0)) / interest


def icr_label(icr):
    if icr is None:
        return 'Debt Free'
    return None


def icr_warning_flag(icr):
    if icr is None:
        return False
    return icr < 1.5


def net_debt(borrowings, investments):
    return (borrowings or 0) - (investments or 0)


def asset_turnover(sales, total_assets):
    if total_assets is None or total_assets == 0:
        return None
    return sales / total_assets
