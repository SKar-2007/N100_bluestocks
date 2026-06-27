import pytest
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


class TestNetProfitMargin:
    def test_normal(self):
        result = net_profit_margin(100, 1000)
        assert result == pytest.approx(10.0)

    def test_zero_sales(self):
        assert net_profit_margin(100, 0) is None

    def test_none_sales(self):
        assert net_profit_margin(100, None) is None

    def test_negative_profit(self):
        result = net_profit_margin(-50, 1000)
        assert result == pytest.approx(-5.0)


class TestOperatingProfitMargin:
    def test_normal(self):
        result = operating_profit_margin(200, 1000)
        assert result == pytest.approx(20.0)

    def test_zero_sales(self):
        assert operating_profit_margin(100, 0) is None

    def test_opm_mismatch_logged(self, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        result = operating_profit_margin(200, 1000, declared_opm=15.0)
        assert result == pytest.approx(20.0)
        assert "OPM cross-check mismatch" in caplog.text

    def test_opm_match_no_log(self, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        result = operating_profit_margin(200, 1000, declared_opm=20.0)
        assert result == pytest.approx(20.0)
        assert "OPM cross-check mismatch" not in caplog.text


class TestReturnOnEquity:
    def test_normal(self):
        result = return_on_equity(100, 200, 800)
        assert result == pytest.approx(10.0)

    def test_negative_equity(self):
        assert return_on_equity(100, -100, 50) is None

    def test_zero_equity(self):
        assert return_on_equity(100, 0, 0) is None

    def test_none_values(self):
        assert return_on_equity(100, None, None) is None


class TestReturnOnCapitalEmployed:
    def test_normal(self):
        result = return_on_capital_employed(150, 200, 800, 500)
        assert result == pytest.approx(10.0)

    def test_zero_capital(self):
        assert return_on_capital_employed(100, 0, 0, 0) is None


class TestReturnOnAssets:
    def test_normal(self):
        result = return_on_assets(50, 1000)
        assert result == pytest.approx(5.0)

    def test_zero_assets(self):
        assert return_on_assets(100, 0) is None

    def test_none_assets(self):
        assert return_on_assets(100, None) is None


class TestDebtToEquity:
    def test_normal(self):
        result = debt_to_equity(500, 200, 800)
        assert result == pytest.approx(0.5)

    def test_zero_borrowings_returns_0(self):
        assert debt_to_equity(0, 200, 800) == 0.0

    def test_none_borrowings_returns_0(self):
        assert debt_to_equity(None, 200, 800) == 0.0

    def test_negative_equity(self):
        result = debt_to_equity(500, -100, 50)
        assert result == pytest.approx(-10.0)


class TestHighLeverageFlag:
    def test_high_de_non_financials(self):
        assert high_leverage_flag(6.0, 'Industrials') is True

    def test_high_de_financials_suppressed(self):
        assert high_leverage_flag(6.0, 'Financials') is False

    def test_low_de_no_flag(self):
        assert high_leverage_flag(2.0, 'Industrials') is False

    def test_none_de(self):
        assert high_leverage_flag(None, 'Industrials') is False


class TestInterestCoverageRatio:
    def test_normal(self):
        result = interest_coverage_ratio(100, 20, 40)
        assert result == pytest.approx(3.0)

    def test_zero_interest_returns_none(self):
        assert interest_coverage_ratio(100, 20, 0) is None

    def test_none_interest_returns_none(self):
        assert interest_coverage_ratio(100, 20, None) is None

    def test_no_other_income(self):
        result = interest_coverage_ratio(100, None, 50)
        assert result == pytest.approx(2.0)


class TestIcrLabel:
    def test_debt_free(self):
        assert icr_label(None) == 'Debt Free'

    def test_normal_icr_no_label(self):
        assert icr_label(3.0) is None


class TestIcrWarningFlag:
    def test_icr_below_1_5(self):
        assert icr_warning_flag(1.0) is True

    def test_icr_above_1_5(self):
        assert icr_warning_flag(3.0) is False

    def test_icr_none(self):
        assert icr_warning_flag(None) is False


class TestNetDebt:
    def test_normal(self):
        assert net_debt(1000, 300) == 700

    def test_no_debt(self):
        assert net_debt(0, 300) == -300

    def test_none_values(self):
        assert net_debt(None, None) == 0


class TestAssetTurnover:
    def test_normal(self):
        result = asset_turnover(2000, 1000)
        assert result == pytest.approx(2.0)

    def test_zero_assets(self):
        assert asset_turnover(100, 0) is None

    def test_none_assets(self):
        assert asset_turnover(100, None) is None
