import pytest
from src.analytics.cagr import (
    compute_cagr,
    window_cagr,
    CAGR_DECLINE_TO_LOSS,
    CAGR_TURNAROUND,
    CAGR_BOTH_NEGATIVE,
    CAGR_ZERO_BASE,
    CAGR_INSUFFICIENT,
)


class TestComputeCagr:
    def test_normal_positive(self):
        val, flag = compute_cagr(100, 200, 5)
        assert val is not None
        assert val > 0
        assert flag is None

    def test_normal_negative_growth(self):
        val, flag = compute_cagr(200, 100, 5)
        assert val is not None
        assert val < 0
        assert flag is None

    def test_decline_to_loss(self):
        val, flag = compute_cagr(100, -50, 5)
        assert val is None
        assert flag == CAGR_DECLINE_TO_LOSS

    def test_turnaround(self):
        val, flag = compute_cagr(-100, 50, 5)
        assert val is None
        assert flag == CAGR_TURNAROUND

    def test_both_negative(self):
        val, flag = compute_cagr(-100, -50, 5)
        assert val is None
        assert flag == CAGR_BOTH_NEGATIVE

    def test_zero_base(self):
        val, flag = compute_cagr(0, 100, 5)
        assert val is None
        assert flag == CAGR_ZERO_BASE

    def test_insufficient_years(self):
        val, flag = compute_cagr(100, 200, 0)
        assert val is None
        assert flag == CAGR_INSUFFICIENT

    def test_none_values(self):
        val, flag = compute_cagr(None, 200, 5)
        assert val is None
        assert flag == CAGR_INSUFFICIENT

    def test_precise_cagr(self):
        val, flag = compute_cagr(100, 133.1, 3)
        assert val is not None
        assert val == pytest.approx(10.0, abs=0.01)
        assert flag is None

    def test_exact_values(self):
        val, flag = compute_cagr(1000, 1000, 5)
        assert val == pytest.approx(0.0)
        assert flag is None


class TestWindowCagr:
    def test_insufficient_data(self):
        val, flag = window_cagr({2020: 100}, 2020, 5)
        assert val is None
        assert flag == CAGR_INSUFFICIENT

    def test_normal_window(self):
        data = {2019: 100, 2020: 120, 2021: 144, 2022: 172.8, 2023: 207.36, 2024: 248.83}
        val, flag = window_cagr(data, 2024, 5)
        assert val is not None
        assert val == pytest.approx(20.0, abs=0.5)
        assert flag is None
