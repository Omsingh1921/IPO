# Platform Implementation Roadmap

This document outlines the phased roadmap for building the **Indian IPO Research & Data Analysis Platform**. Each phase defines clear objectives, key deliverables, and measurable completion criteria.

---

## Roadmap Overview

```
Phase 1: Foundation & Research Prompting [ACTIVE]
   │
Phase 2: Google Sheets IPO Database
   │
Phase 3: Python Data Analysis Engine
   │
Phase 4: Historical Backtesting Engine
   │
Phase 5: 40% Target Performance Measurement
   │
Phase 6: Automated 9:00 AM Daily Briefing
   │
Phase 7: Relational Database Migration (MySQL)
   │
Phase 8: Enterprise Streaming & Search (Kafka + Elasticsearch + Kibana)
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

## Phase 8: Enterprise Streaming & Search (Kafka -> Elasticsearch -> Kibana)

- **Status:** Planned
- **Objective:** Scale the system to an enterprise-grade real-time streaming and search architecture for live exchange feeds and full-text document search across RHP/DRHP filings.
- **Key Deliverables:**
  - Apache Kafka pipeline: Topics for real-time bid streams, exchange announcements, and sentiment feeds.
  - Elasticsearch cluster: Ingestion and indexing of full text from RHP/DRHP PDFs for instant keyword search (e.g., specific risk factors, litigations, customer concentrations).
  - Kibana visual dashboards: Real-time visualization of subscription curves, sector valuation distributions, and historical scenario accuracy.
- **Completion Criteria:**
  - Real-time bid events ingested and indexed with sub-second latency.
  - Full-text search across 500+ page prospectus documents returning relevant risk disclosures in < 200ms.
  - End-to-end interactive Kibana dashboards operational for institutional research review.
