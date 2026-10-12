# Indian IPO Research & Data Analysis Platform

An institutional-grade, data-driven research, analysis, and decision-support platform designed specifically for the Indian Initial Public Offering (IPO) ecosystem (Mainboard & SME).

> **CRITICAL DISCLAIMER & MANDATORY OPERATING PRINCIPLE**  
> **No Guaranteed Returns:** This platform is strictly a research, historical backtesting, and decision-support system. Any reference to a **"40% return" or target scenario represents a conditional analytical hypothesis/target scenario**, NOT a guaranteed return, prediction, or financial advice. The platform does not execute automated trading, make definitive profit claims, or fabricate unverified financial metrics. All investments in public equity and IPOs carry substantial market risk, including potential loss of principal.

---

## 1. Project Purpose

The primary objective of this platform is to eliminate emotional bias and speculative hype around Indian IPOs by combining structured financial fundamental analysis, rigorous valuation benchmarking, real-time demand metrics, and indicative market sentiment into a reproducible, data-driven decision-support framework.

Key focus areas include:
- **Comprehensive Due Diligence:** Analyzing Red Herring Prospectuses (RHP), audited financial statements, capital structures, and disclosed risk factors.
- **Valuation Benchmarking:** Comparing IPO issue prices against industry peers and sector price-to-earnings (P/E) and price-to-book (P/B) multiples.
- **Demand & Sentiment Synthesis:** Integrating verified exchange subscription data (QIB, NII, Retail) with indicative Grey Market Premium (GMP) data.
- **Scenario & Upside Analysis:** Evaluating multi-scenario listing performance (Conservative, Base, Optimistic) and stress-testing conditions under which high-alpha scenarios (e.g., 40%+ listing gains) may materialize.
- **Historical Backtesting:** Tracking long-term listing day and post-listing performance against original research theses to iteratively refine selection criteria.

---

## 2. Current Phase: Phase 1 (Foundation & Research Prompt Engineering)

We are currently in **Phase 1** of the platform buildout.

### Phase 1 Deliverables:
- Repository architecture and baseline directory structure.
- Comprehensive technical documentation ([architecture.md](file:///c:/Users/omsin/OneDrive/Desktop/IPO-Recomendation-platform/docs/architecture.md), [roadmap.md](file:///c:/Users/omsin/OneDrive/Desktop/IPO-Recomendation-platform/docs/roadmap.md), and [data-sources.md](file:///c:/Users/omsin/OneDrive/Desktop/IPO-Recomendation-platform/docs/data-sources.md)).
- Standardized Gemini Master Prompt schema for structured IPO research reports ([prompts/phase1_ipo_research_prompt.md](file:///c:/Users/omsin/OneDrive/Desktop/IPO-Recomendation-platform/prompts/phase1_ipo_research_prompt.md)).
- Governance and compliance guardrails mandating verified source attribution and strict disclaimer enforcement.

*Note: In Phase 1, no databases, streaming pipelines, or complex application code are deployed.*

---

## 3. Overall Multi-Phase Roadmap

The platform is designed to scale progressively from structured AI-augmented research to an enterprise data streaming and analytics platform:

| Phase | Milestone | Core Technology / Objective |
| :--- | :--- | :--- |
| **Phase 1** | **Foundation & Research Schema** *(Current)* | Standardized directory structure, prompt engineering, source verification standards. |
| **Phase 2** | **Google Sheets IPO Database** | Centralized structured storage for quantitative metrics and IPO tracking. |
| **Phase 3** | **Python Data Analysis** | Python ETL and automated computation of financial ratios, valuation spreads, and subscription metrics. |
| **Phase 4** | **Historical Backtesting Engine** | Systematic backtesting framework to measure recommendation efficacy against actual listing day outcomes. |
| **Phase 5** | **40% Target Performance Measurement** | Precision evaluation of high-upside (40%+) scenario flags versus actual outcomes. |
| **Phase 6** | **Automated 9:00 AM Daily Dispatch** | Scheduled morning executive digest aggregating open IPOs, bid status, and updated GMP. |
| **Phase 7** | **Relational Storage (MySQL)** | Transition from spreadsheet storage to a relational schema for high data integrity and complex querying. |
| **Phase 8** | **Streaming & Search (Kafka + Elasticsearch + Kibana)** | Distributed streaming ingestion, full-text prospectus search, and visual analytics dashboards. |

For exhaustive milestone details and completion criteria, consult [docs/roadmap.md](file:///c:/Users/omsin/OneDrive/Desktop/IPO-Recomendation-platform/docs/roadmap.md).

---

## 4. Directory Layout

```
IPO-Recomendation-platform/
│
├── README.md                                # Platform overview, principles, and roadmap
│
├── docs/
│   ├── architecture.md                      # Multi-phase system architecture and evolution
│   ├── roadmap.md                           # Phase-by-phase objectives and completion criteria
│   └── data-sources.md                      # Catalog of primary and secondary data sources
│
├── prompts/
│   └── phase1_ipo_research_prompt.md        # Master Gemini research prompt template
│
├── data/
│   ├── raw/                                 # Raw prospectuses, RHP excerpts, and exchange feeds
│   └── processed/                           # Normalized metrics, structured JSONs, and CSVs
│
├── reports/                                 # Generated Markdown and PDF research reports
│
└── config/
    └── .gitkeep                             # Configuration files and environment settings
```

---

## 5. Governance & Data Principles

1. **Source Attribution:** Every quantitative datapoint must be accompanied by its primary or secondary source and timestamp.
2. **Missing Data Transparency:** Never synthesize or hallucinate financial figures. If a metric is not published or disclosed, label it as `"Not available"`.
3. **Primary vs. Unofficial:** Exchange bid books (NSE/BSE) and statutory filings (SEBI/RHP) take precedence over indicative metrics like Grey Market Premium (GMP).
4. **Research Only:** The platform does not provide buy/sell/apply advisory services or portfolio management services.
