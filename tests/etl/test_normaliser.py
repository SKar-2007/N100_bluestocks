import re

import pytest
from src.etl.normaliser import normalize_year, normalize_ticker


class TestNormalizeYear:
    def test_fy_prefix_four_digit(self):
        assert normalize_year("FY2023") == 2023
        assert normalize_year("FY2024") == 2024
        assert normalize_year("FY2025") == 2025

    def test_fy_prefix_two_digit(self):
        assert normalize_year("FY23") == 2023
        assert normalize_year("FY24") == 2024
        assert normalize_year("FY25") == 2025

    def test_fy_prefix_two_digit_historical(self):
        assert normalize_year("FY99") == 1999
        assert normalize_year("FY00") == 2000
        assert normalize_year("FY01") == 2001

    def test_fy_prefix_lowercase(self):
        assert normalize_year("fy2023") == 2023
        assert normalize_year("fy23") == 2023

    def test_year_range_short(self):
        assert normalize_year("2022-23") == 2022
        assert normalize_year("2023-24") == 2023
        assert normalize_year("2024-25") == 2024

    def test_year_range_full(self):
        assert normalize_year("2022-2023") == 2022
        assert normalize_year("2023-2024") == 2023
        assert normalize_year("2024-2025") == 2024

    def test_year_range_with_dash_variants(self):
        assert normalize_year("2022\u201323") == 2022
        assert normalize_year("2022\u201323") == 2022

    def test_four_digit_year_only(self):
        assert normalize_year("2023") == 2023
        assert normalize_year("2024") == 2024
        assert normalize_year("2000") == 2000
        assert normalize_year("1999") == 1999

    def test_numeric_input_int(self):
        assert normalize_year(2023) == 2023
        assert normalize_year(1999) == 1999
        assert normalize_year(2001) == 2001

    def test_numeric_input_float(self):
        assert normalize_year(2023.0) == 2023
        assert normalize_year(2024.5) == 2024

    def test_month_year_formats(self):
        assert normalize_year("Mar 2023") == 2023
        assert normalize_year("March 2024") == 2024
        assert normalize_year("Dec 2023") == 2023
        assert normalize_year("December 2025") == 2025
        assert normalize_year("Jan 2023") == 2023
        assert normalize_year("Jun 2023") == 2023

    def test_date_format_dd_mon_yyyy(self):
        assert normalize_year("31-Mar-2023") == 2023
        assert normalize_year("01-Jan-2024") == 2024
        assert normalize_year("15-Jun-2023") == 2023

    def test_date_format_mon_dd_yyyy(self):
        assert normalize_year("Mar-31-2023") == 2023
        assert normalize_year("Jan-01-2024") == 2024

    def test_calendar_year_prefix(self):
        assert normalize_year("CY2023") == 2023
        assert normalize_year("CY2024") == 2024
        assert normalize_year("cy2023") == 2023

    def test_date_format_dd_mm_yyyy(self):
        assert normalize_year("31-12-2023") == 2023
        assert normalize_year("01-01-2024") == 2024

    def test_fiscal_context(self):
        assert normalize_year("FY2023", context='fiscal') == 2023
        assert normalize_year("2022-23", context='fiscal') == 2022

    def test_edge_case_empty_string(self):
        assert normalize_year("") is None

    def test_edge_case_none(self):
        assert normalize_year(None) is None

    def test_edge_case_whitespace(self):
        assert normalize_year("  FY2023  ") == 2023
        assert normalize_year("  2022-23  ") == 2022

    def test_edge_case_invalid_string(self):
        assert normalize_year("not-a-year") is None
        assert normalize_year("abc") is None

    def test_edge_case_special_chars_only(self):
        assert normalize_year("---") is None

    def test_negative_year(self):
        assert normalize_year("-2023") == -2023

    def test_leading_zeros(self):
        assert normalize_year("002023") == 2023

    def test_numeric_string_with_decimal(self):
        assert normalize_year("2023.0") == 2023
        assert normalize_year("2023.99") == 2023


class TestNormalizeTicker:
    def test_basic_ticker(self):
        assert normalize_ticker("TCS") == "TCS"
        assert normalize_ticker("INFY") == "INFY"
        assert normalize_ticker("RELIANCE") == "RELIANCE"

    def test_ticker_with_ns_suffix(self):
        assert normalize_ticker("TCS.NS") == "TCS"
        assert normalize_ticker("INFY.NS") == "INFY"
        assert normalize_ticker("RELIANCE.NS") == "RELIANCE"

    def test_ticker_with_bse_suffix(self):
        assert normalize_ticker("TCS.BSE") == "TCS"
        assert normalize_ticker("INFY.BSE") == "INFY"

    def test_ticker_with_nse_suffix(self):
        assert normalize_ticker("TCS.NSE") == "TCS"

    def test_ticker_with_bo_suffix(self):
        assert normalize_ticker("TCS.BO") == "TCS"

    def test_ticker_with_ns_prefix(self):
        assert normalize_ticker("NS:TCS") == "TCS"
        assert normalize_ticker("NSE:INFY") == "INFY"
        assert normalize_ticker("BSE:RELIANCE") == "RELIANCE"

    def test_ticker_with_whitespace(self):
        assert normalize_ticker("  TCS  ") == "TCS"
        assert normalize_ticker("  INFY  ") == "INFY"

    def test_ticker_lowercase(self):
        assert normalize_ticker("tcs") == "TCS"
        assert normalize_ticker("infy") == "INFY"
        assert normalize_ticker("reliance") == "RELIANCE"

    def test_ampersand_replacement(self):
        assert normalize_ticker("M&M") == "MANDM"
        assert normalize_ticker("A&B") == "AANDB"

    def test_special_characters_removed(self):
        result = normalize_ticker("HCL@TECH")
        assert result == "HCLTECH"
        assert not re.search(r'[^A-Z0-9\s-]', result)

    def test_ticker_with_extra_spaces_inside(self):
        assert normalize_ticker("HCL TECH") == "HCLTECH"
        assert normalize_ticker("BAJAJ AUTO") == "BAJAJAUTO"

    def test_edge_case_none(self):
        assert normalize_ticker(None) is None

    def test_edge_case_empty_string(self):
        assert normalize_ticker("") is None

    def test_edge_case_whitespace_only(self):
        assert normalize_ticker("   ") is None

    def test_capital_first_letter_only(self):
        result = normalize_ticker("tcs")
        assert result == "TCS"

    def test_mixed_case_ticker(self):
        assert normalize_ticker("HdfcBank") == "HDFCBANK"
        assert normalize_ticker("ICICI Bank") == "ICICIBANK"

    def test_ticker_known_mapping(self):
        assert normalize_ticker("M&M") == "MANDM"
        assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"

    def test_numeric_ticker(self):
        assert normalize_ticker("5PAISA") == "5PAISA"

    def test_ticker_with_dot_inside(self):
        result = normalize_ticker("HCL.TECH")
        assert "HCLTECH" in result

    def test_ticker_with_multiple_suffixes(self):
        assert normalize_ticker("TCS.NS.NS") == "TCS"
