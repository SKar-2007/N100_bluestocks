# Blueprint: Sprint 1 — Data Foundation

## Project Overview & Metadata
* **Epic:** Epic 01 · Data Ingestion & ETL
* **Duration:** Day 01 - Day 07
* **Estimation / Velocity:** 34 Story Points (SP)
* **Target Environment:** Python, SQLite Database (`nifty100.db`)

---

## Sprint Goal
By the end of Sprint 1, the team must have a fully loaded and validated SQLite database (`nifty100.db`) containing all core and supplementary tables derived from 12 source files. All 16 data quality rules must be fully implemented, executed, and any **CRITICAL** failures completely resolved. This sprint establishes the data foundation required for all subsequent modules.

---

## Technical Artifacts & Deliverables

The sprint will deliver the following verified artifacts:

| Artifact Path | Description |
| :--- | :--- |
| **`nifty100.db`** | SQLite database with all tables fully populated. |
| **`db/schema.sql`** | Database schema script defining tables, Primary Keys (PK), and Foreign Keys (FK). |
| **`src/etl/loader.py`** | Main ETL execution script responsible for reading, staging, and inserting data. |
| **`src/etl/normaliser.py`** | Utility containing text/ticker and data structure normalization logic. |
| **`src/etl/validator.py`** | Component containing the implementation of the 16 Data Quality rules. |
| **`output/load_audit.csv`** | Audit ledger documenting per-table row counts, successful loads, and rejections. |
| **`output/validation_failures.csv`** | Log of all data quality violations detailed by rule, entity, and severity level. |
| **`tests/etl/`** | Test suite containing **35+ unit tests** validating parser/loader behavior. |
| **`notebooks/exploratory_queries.sql`** | Validation script containing exactly **10 exploratory queries** for data verification. |

---

## Day-by-Day Workflow Breakdown

### 📅 Day 01: Environment Setup & Tooling Foundation
* **Objective:** Establish the development environment, package management, and common workflows.
* **Tasks:**
  * Create core project directory structures (`src/etl/`, `db/`, `output/`, `tests/etl/`, `notebooks/`).
  * Initialize the python virtual environment (`venv`).
  * Install **20 required core libraries** for ETL, parsing, and data validation.
  * Configure project settings and secrets inside a secure `.env` file.
  * Define and test automated project workflows via **Makefile targets**:
    * `load` — Triggers full data parsing and insertion.
    * `ratios` — Executes financial ratio computations.
    * `test` — Runs the unit testing suite.
    * `report` — Generates automated quality and processing logs.
    * `dashboard` — Launches data overview telemetry interfaces.
    * `api` — Sets up downstream service entry points.
    * `clean` — Resets temporary build, environment, and database outputs.

### 📅 Day 02: Excel Loader & Normaliser Development
* **Objective:** Build robust file parsers capable of cleaning structural irregularities from source records.
* **Tasks:**
  * Author `src/etl/normaliser.py` and initialize `src/etl/loader.py`.
  * Implement `normalize_year()` to standardize varying fiscal and chronological year representations across files.
  * Implement `normalize_ticker()` to clean ticker symbols, prefixes, or format inconsistencies.
  * Author and execute a comprehensive unit testing suite within `tests/etl/` containing **35+ unit tests** to prevent regression:
    * **20+ unit tests** dedicated exclusively to `normalize_year`.
    * **15+ unit tests** dedicated exclusively to `normalize_ticker`.

### 📅 Day 03: Schema Validator & 16 Data Quality (DQ) Rules
* **Objective:** Establish strict data guardrails to protect against corrupted or incomplete upstream information.
* **Tasks:**
  * Develop the data verification matrix inside `src/etl/validator.py` covering **DQ-01 to DQ-16**.
  * Classify validation failures into strict severity tiers to manage loading exceptions:
    * **CRITICAL Tier:** Structural errors that block database integrity (e.g., Primary Key violations, Missing Foreign Keys).
    * **WARNING Tier:** Data anomalies requiring auditing but permitting row stage passage (e.g., Operating Profit Margin cross-checks, Negative sales).
  * Automatically dump exceptions to `output/validation_failures.csv` containing failure locations and severity metadata.

### 📅 Day 04: SQLite Database Schema Design
* **Objective:** Author the structural blueprints for the storage layer ensuring referential integrity rules are locked down.
* **Tasks:**
  * Write `db/schema.sql` to map the target relational models.
  * Explicitly define Primary Keys (PK), Composite Keys, and Foreign Keys (FK) matching the financial domain objects.
  * Integrate structural validation rules inside `loader.py` to match the target tables.
  * Enforce strict referential constraints at connection startup by configuring the database engine command:
    ```sql
    PRAGMA foreign_keys = ON;
    ```

### 📅 Day 05: Full Data Load Execution (All 12 Files)
* **Objective:** Execute the automated pipeline to ingest data in order across all source formats.
* **Tasks:**
  * Sequence processing over **12 source files** partitioned into:
    * **7 Core Excel Files**
    * **5 Supplementary Files**
  * Execute ingestion according to a logical, dependency-aware load order to prevent referential key exceptions.
  * Populate all **10 target tables** (specified across structural contexts as: `companies`, `profitandloss`, `balancesheet`, `cashflow`, `analysis`, `documents`, `prosandcons`, `sectors`, `stock_prices`, `financial_ratios`, and `peer_groups`).
  * Verify audit metrics against targets in `output/load_audit.csv` ensuring an explicit **Foreign Key check result of 0 (zero errors)**. All **CRITICAL** structural failures must be completely resolved before the end of Day 05.

### 📅 Day 06: Data Quality Manual Review & Edge Case Patching
* **Objective:** Perform qualitative visual inspections to locate silent bugs or data gaps that automation missed.
* **Tasks:**
  * Select **5 random companies** at random and perform full end-to-end trace auditing from source files to database cells.
  * Conduct an evaluation of historical multi-year coverage.
  * Scan for and flag data gaps, specifically highlighting companies with **less than 5 years** of historical financial footprints.
  * Diagnose code flaws, resolve edge-case parsing errors, patch the loader scripts, and execute a complete pipeline re-run to maintain clean state.

### 📅 Day 07: Sprint Wrap-Up, Analytical Validation & Review
* **Objective:** Sign off on the technical foundations and update sprint tracking telemetry.
* **Tasks:**
  * Finalize a suit of analysis scripts inside `notebooks/exploratory_queries.sql` comprising **exactly 10 structural validation queries**.
  * Validate that the unit test suite registers **0 failures**.
  * Conduct a live system demonstration of the working `nifty100.db` instance to stakeholders.
  * Host the Sprint Retrospective session to gather team feedback on pipeline bottlenecks.
  * Formally close out sprint issues and update the project management board.

---

## Data Quality (DQ) Matrix Rules Summary

The ingestion engine enforces a battery of 16 rules, including but not limited to the following:

| Rule Code | Focus Area | Target Condition / Severity |
| :--- | :--- | :--- |
| **DQ-01** | Primary Key Uniqueness | Rejects duplicate identifiers entirely (**CRITICAL**) |
| **DQ-02** | Composite PK Validation | Validates unique combinations of `(company_id, year)` (**CRITICAL**) |
| **DQ-03** | Foreign Key Integrity | Validates parent records exist prior to child row writing (**CRITICAL**) |
| **DQ-04** | Balance Sheet Alignment | Validates Balance Sheet equity and liabilities balance to within `< 1%` (**WARNING**) |
| **DQ-05** | Operating Profit Margin (OPM) | Cross-checks derived percentages against raw line items (**WARNING**) |
| **DQ-08** | Revenue Validation | Confirms sales/revenue figures register as positive values (**WARNING**) |
| **DQ-09 - 16**| Scope Safeguards | Covers constraints on net cash, tax rate, dividend caps, URL valid formats, EPS sign correctness, BSE balance, and general data coverage metrics. |

---

## Target Expected Load Volume Telemetry
The pipeline execution expects the following target metrics during a clean run verification:

* **Source File Count:** 12 Files (7 Core + 5 Supplementary)
* **Target Table Entities:** 10 Tables
* **Expected Successful Database Records:**
  * `companies` = **92 rows**
  * `profitandloss` (P&L) ~ **1,276 rows**
  * `balancesheet` (BS) ~ **1,312 rows**
  * `cashflow` (CF) ~ **1,187 rows**
  * `stock_prices` = **5,520 rows**

---

## Exit Criteria & Definition of Done (DoD)

To move out of Sprint 1 and authorize subsequent analytics phases, the following checklist must evaluate to 100% compliance:

- [ ] **Row Count Match:** `SELECT COUNT(*) FROM companies;` returns exactly **92**.
- [ ] **Referential Integrity:** `PRAGMA foreign_key_check;` execution yields exactly **0 rows** of errors.
- [ ] **Rejection Enforcement:** `load_audit.csv` verifies **zero CRITICAL rejections** remaining in the processing engine.
- [ ] **Test Coverage:** All **35+ ETL unit tests** execute with a status of 100% pass (0 failures).
- [ ] **Manual Trace Verification:** Review of the 5 selected companies proves perfect accuracy with no truncated data.
- [ ] **Sprint Sign-Off:** Stakeholder demonstration completed and sprint closure approved.
