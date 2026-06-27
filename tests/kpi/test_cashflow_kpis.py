import pytest
from src.analytics.cashflow_kpis import (
    free_cash_flow,
    cfo_quality_score,
    capex_intensity,
    fcf_conversion_rate,
    capital_allocation_pattern,
)


class TestFreeCashFlow:
    def test_normal(self):
        assert free_cash_flow(100, -30) == 70

    def test_negative_allowed(self):
        assert free_cash_flow(50, -100) == -50

    def test_none_operations(self):
        assert free_cash_flow(None, -30) == -30

    def test_both_none(self):
        assert free_cash_flow(None, None) is None


class TestCfoQualityScore:
    def test_high_quality(self):
        records = [
            {'net_profit': 100, 'cash_from_operations': 120},
            {'net_profit': 100, 'cash_from_operations': 130},
            {'net_profit': 100, 'cash_from_operations': 110},
        ]
        score, label = cfo_quality_score(records)
        assert score is not None
        assert score > 1.0
        assert label == 'High Quality'

    def test_moderate(self):
        records = [
            {'net_profit': 100, 'cash_from_operations': 70},
            {'net_profit': 100, 'cash_from_operations': 80},
            {'net_profit': 100, 'cash_from_operations': 60},
        ]
        score, label = cfo_quality_score(records)
        assert score is not None
        assert 0.5 <= score <= 1.0
        assert label == 'Moderate'

    def test_accrual_risk(self):
        records = [
            {'net_profit': 100, 'cash_from_operations': 20},
            {'net_profit': 100, 'cash_from_operations': 30},
            {'net_profit': 100, 'cash_from_operations': 10},
        ]
        score, label = cfo_quality_score(records)
        assert score is not None
        assert score < 0.5
        assert label == 'Accrual Risk'

    def test_insufficient_data(self):
        score, label = cfo_quality_score([
            {'net_profit': 100, 'cash_from_operations': 120},
        ])
        assert score is None
        assert label is None

    def test_zero_pat(self):
        records = [
            {'net_profit': 0, 'cash_from_operations': 120},
            {'net_profit': 0, 'cash_from_operations': 130},
            {'net_profit': 100, 'cash_from_operations': 110},
        ]
        score, label = cfo_quality_score(records)
        assert score is not None


class TestCapexIntensity:
    def test_asset_light(self):
        pct, label = capex_intensity(-20, 1000)
        assert pct == pytest.approx(2.0)
        assert label == 'Asset Light'

    def test_moderate(self):
        pct, label = capex_intensity(-50, 1000)
        assert pct == pytest.approx(5.0)
        assert label == 'Moderate'

    def test_capital_intensive(self):
        pct, label = capex_intensity(-100, 1000)
        assert pct == pytest.approx(10.0)
        assert label == 'Capital Intensive'

    def test_zero_sales(self):
        pct, label = capex_intensity(-50, 0)
        assert pct is None
        assert label is None


class TestFcfConversionRate:
    def test_normal(self):
        result = fcf_conversion_rate(70, 100)
        assert result == pytest.approx(70.0)

    def test_zero_op(self):
        assert fcf_conversion_rate(70, 0) is None

    def test_none_op(self):
        assert fcf_conversion_rate(70, None) is None


class TestCapitalAllocationPattern:
    def test_reinvestor(self):
        assert capital_allocation_pattern(100, -50, -30) == 'Reinvestor'

    def test_liquidating_assets(self):
        assert capital_allocation_pattern(100, 50, -30) == 'Liquidating Assets'

    def test_distress_signal(self):
        assert capital_allocation_pattern(-100, 50, 30) == 'Distress Signal'

    def test_growth_funded_by_debt(self):
        assert capital_allocation_pattern(-100, -50, 30) == 'Growth Funded by Debt'

    def test_cash_accumulator(self):
        assert capital_allocation_pattern(100, 50, 30) == 'Cash Accumulator'

    def test_pre_revenue(self):
        assert capital_allocation_pattern(-100, -50, -30) == 'Pre-Revenue'

    def test_mixed(self):
        assert capital_allocation_pattern(100, -50, 30) == 'Mixed'

    def test_other(self):
        assert capital_allocation_pattern(0, 0, 0) == 'Other'
