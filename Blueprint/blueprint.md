# Blueprint: Sprint 2 — Financial Ratio Engine

## Project Overview & Metadata
* **Epic:** Epic 02 · Financial Ratio Engine
* **Duration:** Day 08 — Day 14
* **Estimation / Velocity:** 42 Story Points (SP)
* **Target Environment:** Python, SQLite Database (`nifty100.db`)

---

## Sprint Goal
By end of Sprint 2, the Ratio Engine must compute 50+ KPIs for all 92 companies across all available years. The `financial_ratios` table in SQLite must be fully populated. All formula edge cases (negative equity, debt-free companies, CAGR turnarounds, bank carve-out) must be handled correctly and logged. All KPI formula unit tests must pass.

---

## Technical Artifacts & Deliverables

| Artifact Path | Description |
| :--- | :--- |
| **`src/analytics/ratios.py`** | Profitability, leverage, efficiency ratio functions (Net Profit Margin, OPM, ROE, ROCE, ROA, D/E, ICR, Net Debt, Asset Turnover). |
| **`src/analytics/cagr.py`** | CAGR engine with 6 edge case handlers (DECLINE_TO_LOSS, TURNAROUND, BOTH_NEGATIVE, ZERO_BASE, INSUFFICIENT). Computes Revenue, PAT, EPS CAGR for 3/5/10yr windows. |
| **`src/analytics/cashflow_kpis.py`** | CFO Quality Score, CapEx Intensity, FCF Conversion Rate, capital allocation 8-pattern classifier. |
| **`src/analytics/engine.py`** | Main orchestrator that loads data from `profitandloss`, `balancesheet`, `cashflow`, computes all KPIs, populates `financial_ratios` table, writes `capital_allocation.csv` and `ratio_edge_cases.log`. |
| **`output/capital_allocation.csv`** | 8-pattern label for every company-year based on (CFO, CFI, CFF) sign. |
| **`output/ratio_edge_cases.log`** | All anomalous ROCE/ROE cross-checks documented with category (formula discrepancy, data source issue). |
| **`tests/kpi/`** | 76 unit tests covering ratios, CAGR edge cases, and cash flow KPIs. |

---

## Day-by-Day Workflow Breakdown

### Day 08: Profitability Ratios
* **Objective:** Implement core profitability metrics with edge case handling.
* **Tasks:**
  * Write `src/analytics/ratios.py` — Net Profit Margin: `net_profit / sales * 100`, return None if sales = 0.
  * Operating Profit Margin — compute and cross-check against `operating_profit_margin` field, log if diff > 1%.
  * Return on Equity (ROE): `net_profit / (equity_capital + reserves) * 100`, return None if equity+reserves <= 0.
  * Return on Capital Employed (ROCE): EBIT / (equity + reserves + borrowings) * 100.
  * For companies in Financials broad_sector — D/E warning flag suppressed.
  * Return on Assets (ROA): `net_profit / total_assets * 100`, return None if total_assets = 0.
  * Write 8 unit tests covering normal, zero denominator (None), negative equity (None), OPM cross-check mismatch.

### Day 09: Leverage & Efficiency Ratios
* **Objective:** Implement debt, coverage, and efficiency metrics.
* **Tasks:**
  * Debt-to-Equity: `borrowings / (equity_capital + reserves)` — return 0 if borrowings = 0.
  * D/E flag: if D/E > 5 and company is NOT in Financials — `high_leverage_flag = True`.
  * Interest Coverage Ratio: `(operating_profit + other_income) / interest` — return None if interest = 0.
  * For ICR = None (debt-free) — store `icr_label = 'Debt Free'`.
  * ICR warning flag: if ICR < 1.5 — company at risk.
  * Net Debt: `borrowings - investments`.
  * Asset Turnover: `sales / total_assets`, return None if total_assets = 0.
  * Write 8 unit tests: D/E debt-free returns 0, ICR interest=0 returns None, ICR label = Debt Free, high D/E flag.

### Day 10: CAGR Engine — All Growth Metrics
* **Objective:** Build CAGR computation with comprehensive edge case handling.
* **Tasks:**
  * Write `src/analytics/cagr.py` — CAGR formula: `((end/start)^(1/n) - 1) * 100`.
  * Revenue CAGR for 3yr, 5yr, 10yr windows.
  * PAT CAGR for 3yr, 5yr, 10yr windows.
  * EPS CAGR for 3yr, 5yr, 10yr windows.
  * Handle 6 edge cases:
    * Positive+Positive — compute normally
    * Positive+Negative — return None with flag DECLINE_TO_LOSS
    * Negative+Positive — return None with flag TURNAROUND
    * Negative+Negative — return None with flag BOTH_NEGATIVE
    * Zero base — return None with flag ZERO_BASE
    * Less than n years — return None with flag INSUFFICIENT
  * Store CAGR flag alongside value (e.g. `revenue_cagr_5yr_flag`).
  * Write 10 unit tests: normal CAGR, all 6 edge case flags.

### Day 11: Cash Flow KPIs & Capital Allocation
* **Objective:** Derive cash flow health metrics and capital allocation patterns.
* **Tasks:**
  * Free Cash Flow: `operating_activity + investing_activity`.
  * CFO Quality Score: CFO/PAT ratio averaged over 5 years — >1.0 = High Quality, 0.5-1.0 = Moderate, <0.5 = Accrual Risk.
  * CapEx Intensity: `abs(investing_activity) / sales * 100` — <3% = Asset Light, 3-8% = Moderate, >8% = Capital Intensive.
  * FCF Conversion Rate: `FCF / operating_profit * 100`.
  * Capital allocation 8-pattern classifier based on sign of (CFO, CFI, CFF):
    * (+,-,-) = Reinvestor
    * (+,-,-) with high CFO/PAT = Shareholder Returns
    * (+,+,-) = Liquidating Assets
    * (-,+,+) = Distress Signal
    * (-,-,+) = Growth Funded by Debt
    * (+,+,+) = Cash Accumulator
    * (-,-,-) = Pre-Revenue
    * (+,-,+) = Mixed
  * Generate `output/capital_allocation.csv`.

### Day 12: Populate financial_ratios Table
* **Objective:** Run full ratio engine for all companies, populate SQLite.
* **Tasks:**
  * Run `src/analytics/engine.py` for all 92 companies across all available years.
  * KPI columns: `net_profit_margin_pct`, `operating_profit_margin_pct`, `return_on_equity_pct`, `debt_to_equity`, `interest_coverage`, `asset_turnover`, `free_cash_flow_cr`, `capex_cr`, `earnings_per_share`, `book_value_per_share`, `dividend_payout_ratio_pct`, `total_debt_cr`, `cash_from_operations_cr`, `revenue_cagr_5yr`, `pat_cagr_5yr`, `eps_cagr_5yr`, `composite_quality_score`.
  * Verify row count >= 1,100.
  * Manual spot-check: 3 companies, recompute ROE and 5yr Revenue CAGR — difference < 0.1%.

### Day 13: Bank ROCE Carve-Out & Edge Case Log
* **Objective:** Handle Financials sector exceptions and document anomalies.
* **Tasks:**
  * For 19 companies in Financials sector — standard D/E warning flag suppressed (high leverage structurally normal).
  * Cross-check ROCE against `roce_percentage` column in companies.xlsx — log anomalies > 5% diff to `output/ratio_edge_cases.log`.
  * Cross-check ROE against `roe_percentage` column — note source anomalies (e.g. TCS shows 0.52).
  * Categorise each anomaly: data source issue, version difference, or formula discrepancy.

### Day 14: Tests & Sprint Review
* **Objective:** Final validation and documentation.
* **Tasks:**
  * Run all KPI formula unit tests — 0 failures.
  * Review `ratio_edge_cases.log` — all anomalies documented.
  * Screener: ROE > 15% and D/E < 1 — verify 15-50 companies.
  * Sprint retrospective — document formula decisions and edge case resolutions.

---

## Datasets Used

The ratio engine draws from these source files loaded into `nifty100.db`:

| Source File | Table | Key Columns Used |
| :--- | :--- | :--- |
| `profitandloss.xlsx` | `profitandloss` | `revenue`, `operating_profit`, `operating_profit_margin`, `other_income`, `interest_expense`, `net_profit`, `eps`, `dividend_payout_ratio` |
| `balancesheet.xlsx` | `balancesheet` | `share_capital`, `reserves_and_surplus`, `total_debt`, `total_assets`, `investments` |
| `cashflow.xlsx` | `cashflow` | `cash_from_operations`, `cash_from_investing`, `cash_from_financing` |
| `companies.xlsx` | `companies` | `ticker`, `face_value`, `roce_percentage`, `roe_percentage` |
| `sectors.xlsx` | `sectors` | `broad_sector` (for Financials carve-out) |

---

## Target Expected Load Volume Telemetry

| Table | Expected Rows | Actual Rows |
| :--- | :--- | :--- |
| `companies` | 92 | 101 |
| `profitandloss` | ~1,276 | 1,165 |
| `balancesheet` | ~1,312 | 1,137 |
| `cashflow` | ~1,187 | 1,152 |
| `financial_ratios` | >= 1,100 | 1,166 |

---

## Exit Criteria & Definition of Done (DoD)

- [x] `SELECT COUNT(*) FROM financial_ratios` returns >= 1,100 rows (**1,166 rows**).
- [x] All 17 KPI columns populated — zero null-only columns.
- [x] All 176 unit tests pass with 0 failures (35 ETL + 76 KPI + validator tests).
- [x] Manual spot-check: TCS, RELIANCE, HDFCBANK ROE and 5yr Revenue CAGR verified within 0.1%.
- [x] `output/ratio_edge_cases.log` exists with documented explanations.
- [x] `output/capital_allocation.csv` written with 8-pattern labels.
- [x] Screener (ROE > 15%, D/E < 1) returns 40 companies (within 15-50 range).
- [x] Sprint 2 review meeting completed and signed off by team lead.

---

## Formula Decisions & Edge Case Resolutions

| Metric | Edge Case | Resolution |
| :--- | :--- | :--- |
| Net Profit Margin | Sales = 0 | Return None (not zero) |
| Operating Profit Margin | OPM mismatch > 1% | Log warning only, use computed value |
| ROE | Equity + Reserves <= 0 | Return None |
| ROCE | Zero capital employed | Return None |
| ROA | Total assets = 0 | Return None |
| Debt-to-Equity | Borrowings = 0 | Return 0.0 (not None) |
| High Leverage Flag | Financials sector, D/E > 5 | Flag suppressed (bank carve-out) |
| Interest Coverage Ratio | Interest = 0 | Return None, label 'Debt Free' |
| ICR Warning | ICR < 1.5 | Flag True |
| Net Debt | Null borrowings/investments | Treat as 0 |
| Asset Turnover | Total assets = 0 | Return None |
| CAGR | Positive->Negative | DECLINE_TO_LOSS flag |
| CAGR | Negative->Positive | TURNAROUND flag |
| CAGR | Negative->Negative | BOTH_NEGATIVE flag |
| CAGR | Start = 0 | ZERO_BASE flag |
| CAGR | Insufficient data | INSUFFICIENT flag |
| CFO Quality Score | < 3 years of data | Return None |
| CapEx Intensity | Sales = 0 | Return None |
| FCF Conversion Rate | Operating profit = 0 | Return None |
| ROCE/ROE source cross-check | Diff > 5% | Log to `ratio_edge_cases.log` as formula discrepancy |
