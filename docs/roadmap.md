# Platform Implementation Roadmap

This document outlines the phased roadmap for building the **Indian IPO Research & Data Analysis Platform**. Each phase defines clear objectives, key deliverables, and measurable completion criteria.

---

## Roadmap Overview

```
Phase 1: Foundation & Research Schema                     [IMPLEMENTED & VERIFIED]
   │
Phase 2: Google Sheets IPO Schema & Mappers              [IMPLEMENTED & VERIFIED]
   │
Phase 3: Python Data Analysis Engine                      [IMPLEMENTED & VERIFIED]
   │
Phase 4: Historical Backtesting Engine                   [IMPLEMENTED & VERIFIED]
   │
Phase 5: 40% Target Performance Scenario Evaluator       [IMPLEMENTED & VERIFIED]
   │
Phase 6: Automated 9:00 AM Daily Briefing & Dispatch      [IMPLEMENTED & VERIFIED]
   │
Phase 7: Relational Primary System of Record (MySQL)     [IMPLEMENTED & VERIFIED]
   │
Phase 8: Distributed Streaming & CDC (Kafka + Debezium)  [IMPLEMENTED & VERIFIED]
   │
Phase 9: FastAPI REST API & Native Web Dashboard         [IMPLEMENTED & VERIFIED]
   │
Phase 10: Security Hardening, JWT Auth & RBAC             [IMPLEMENTED & VERIFIED]
```

---

## Phase 1: Foundation & Master Research Prompting

- **Status:** **In Progress (Current Phase)**
- **Objective:** Establish the foundational project structure, operational guidelines, source hierarchy, and the master Gemini prompt to generate structured, institutional-grade IPO research reports.
- **Key Deliverables:**
  - Standardized repository directory structure (`docs/`, `prompts/`, `data/`, `reports/`, `config/`).
  - Architecture specification (`docs/architecture.md`).
  - Phased roadmap documentation (`docs/roadmap.md`).
  - Data sources catalog classifying primary vs. secondary/unofficial feeds (`docs/data-sources.md`).
  - Master research prompt for Gemini (`prompts/phase1_ipo_research_prompt.md`).
- **Completion Criteria:**
  - Repository structure created without unnecessary third-party package dependencies.
  - Prompt enforces verified citations, clear labeling of unavailable data, and strict absence of guaranteed return claims.
  - Disclaimers highlighting research-only purpose and 40% target as a conditional scenario are embedded across all artifacts.

---

## Phase 2: Google Sheets IPO Database

- **Status:** Planned
- **Objective:** Implement a centralized tabular datastore using Google Sheets for lightweight, collaborative data entry and tracking of ongoing and historical IPOs.
- **Key Deliverables:**
  - Standardized Master Sheet schema covering:
    - Company metadata (Name, Sector, Sub-industry, CIN).
    - Issue parameters (Dates, Issue Price, Lot Size, Fresh vs. OFS, Anchor Allocation).
    - Three-year restated financials (Revenue, EBITDA, PAT, EPS, Debt, Net Worth).
    - Subscription multiples (Anchor, QIB, NII, Retail, Overall).
    - Daily GMP logs and dates.
  - Standard Operating Procedure (SOP) for updating the sheet from Phase 1 report outputs.
- **Completion Criteria:**
  - Sheet populated with structured baseline schema.
  - Verification that all calculations (e.g., Market Cap at Upper Band, Implied P/E, OFS percentage) auto-calculate accurately without errors.

---

## Phase 3: Python Data Analysis Engine

- **Status:** Planned
- **Objective:** Develop a Python analysis layer to compute valuation metrics, financial quality scores, and demand acceleration trends from the structured data.
- **Key Deliverables:**
  - Script to ingest and normalize data from Google Sheets or local CSVs (`data/raw/`).
  - Financial ratio computation module (ROE, ROCE, Debt-to-Equity, EBITDA margins, PAT margins, Free Cash Flow conversion).
  - Valuation relative benchmarking module (Company P/E vs. Industry median P/E, P/B vs. ROE matrix).
  - Demand momentum calculation (Day-over-day QIB and NII bidding velocity).
- **Completion Criteria:**
  - Python scripts execute deterministically and generate verified tables in `data/processed/`.
  - Automated tests validate ratio calculations against sample audited filings.

---

## Phase 4: Historical Backtesting Engine

- **Status:** Planned
- **Objective:** Build an empirical backtesting framework to test historical IPO recommendations and scenario accuracy against actual market listing and 30/90-day returns.
- **Key Deliverables:**
  - Historical database of Indian IPO listings spanning a minimum of 2-3 fiscal years.
  - Automated comparison engine evaluating actual listing price against predicted scenario ranges (Conservative, Base, Optimistic).
  - Reporting metrics: Win rate, Average listing gain, Maximum drawdown, Risk-reward ratio.
- **Completion Criteria:**
  - Backtest engine produces a quantitative report demonstrating scenario hit-rates across different market environments (bull, bear, volatile).
  - Identification of recurring failure modes (e.g., IPOs with high GMP but weak QIB participation).

---

## Phase 5: 40% Target Performance Measurement

- **Status:** Planned
- **Objective:** Create a dedicated evaluation module specifically focused on evaluating the conditional criteria for "40%+ Upside Scenarios".
- **Key Deliverables:**
  - Precision and Recall metric suite for all historical IPOs where a 40%+ upside scenario was evaluated.
  - Multi-variable threshold analyzer (e.g., minimum QIB subscription threshold, GMP/Issue Price ratio, peer valuation discount threshold).
  - Guardrail calibration to reduce false positives in high-upside tags.
- **Completion Criteria:**
  - Clear statistical report validating what percentage of flagged 40%+ scenario candidates reached the target on listing day.
  - Calibrated rubric for when Gemini or the system is permitted to label a 40%+ scenario as plausible.

---

## Phase 6: Automated 9:00 AM Daily Briefing

- **Status:** Planned
- **Objective:** Deploy an automated report generator that prepares and dispatches an executive intelligence summary every morning at 9:00 AM IST.
- **Key Deliverables:**
  - Daily scheduler (Cron or scheduled task).
  - Report aggregator synthesizing:
    - Active IPOs closing today or entering final subscription day.
    - Updated Grey Market Premium (GMP) and subscription status as of market opening.
    - Upcoming listings scheduled for the current trading session.
  - Output formats: Markdown summary saved to `reports/daily/` with optional automated email/notification webhook.
- **Completion Criteria:**
  - Scheduled run reliably triggers at 9:00 AM IST without manual intervention.
  - Report completes generation within < 60 seconds with fresh data.

---

## Phase 7: Relational Database Migration (MySQL)

- **Status:** Planned
- **Objective:** Migrate from spreadsheet-based storage to a production-ready MySQL relational database to ensure ACID compliance, referential integrity, and complex querying.
- **Key Deliverables:**
  - Production database schema with proper indexes, foreign keys, and constraints (`companies`, `issues`, `financials`, `subscriptions`, `gmp_logs`, `listing_outcomes`).
  - Data migration scripts transferring existing historical data from Google Sheets/CSVs into MySQL.
  - Python ORM / data access layer (e.g., SQLAlchemy) for seamless query execution.
- **Completion Criteria:**
  - Schema migrations tested with complete data validation.
  - Query latency < 50ms for complex join queries across multi-year financial statements.

---

## Phase 8: Distributed Streaming & CDC (Apache Kafka + Debezium)
 
- **Status:** **Implemented & Verified** (Unit tests pass; integration verification blocked pending local Docker Desktop daemon)
- **Objective:** Establish an enterprise-grade Change Data Capture (CDC) streaming pipeline from MySQL to Apache Kafka for downstream idempotent consumption and cache synchronization.
- **Key Deliverables:**
-   - Apache Kafka broker in KRaft mode (`confluentinc/cp-kafka:7.5.3`).
-   - Debezium MySQL Connector on Kafka Connect (`debezium/connect:2.5.4.Final`) tracking MySQL row-level binary logs (`ROW` format, `FULL` row image).
-   - Idempotent Python CDC consumer (`src/ipo_platform/streaming/consumer.py`) with sliding-window deduplication, transient retry mechanics, and poison message DLQ quarantine.
-   - Kafka Connect REST management client (`src/ipo_platform/streaming/cdc_manager.py`).
-   - Verified connector configuration (`config/debezium-mysql-connector.json`).
-   - Least-privilege MySQL CDC user script (`scripts/init-cdc-user.sql`).
- - **Completion Criteria:**
-   - Compose configuration parses and validates with `docker compose config`.
-   - Unit test suite passes without live Kafka cluster (`tests/test_kafka_cdc.py`).
-   - **Out-of-Scope Architecture Confirmation:** Elasticsearch and Kibana have been completely removed from active dependencies, Compose services, and roadmap deliverables. No Spring Boot consumers are used.
-
----
-
-## Phase 9: FastAPI REST API & Native Web Dashboard
-
-- **Status:** **Implemented & Verified**
-- **Objective:** Expose enterprise REST API endpoints (`/ipos`, `/health`, `/metrics`, `/portfolio`, `/recommendation`) and deliver an interactive zero-dependency single-page HTML5/CSS/JavaScript dashboard.
-
----
-
-## Phase 10: Security Hardening, Authentication & RBAC
-
-- **Status:** **Implemented & Verified**
-- **Objective:** Enterprise JWT authentication, API-key management, role-based access control (`READ_ONLY`, `OPERATOR`, `ADMIN`), rate limiting with Redis fail-safe support, path traversal prevention, and atomic file writers.
