# Indian IPO Platform Data Schema Specification

**Schema Version:** `1.0`  
**Status:** Approved Phase 1 Schema Design  
**Target Systems:** Phase 2 (Google Sheets IPO Database), Phase 3 (Python Data Analysis Engine), Phase 4 (Historical Backtesting Engine), Phase 5 (40% Target Performance Measurement), Phase 6 (Automated Daily Briefing), Later (MySQL / Kafka / Elasticsearch).

---

## 1. Schema Design Principles

The structured IPO data schema adheres to 15 core design principles:

1. **Preserve Raw Research Data:** Raw filing extracts and exchange bidding counts are stored alongside derived ratios.
2. **Explicit Data-Type Tagging:** Every quantitative metric is tagged as `Reported`, `Calculated`, `Estimate`, or `Not available`.
3. **Traceable Source Provenance:** Every factual entry records source name, URL, publication date, and retrieval timestamp.
4. **Strict Temporal Association:** Every financial metric is bound to its specific accounting period (`FY`, `Q1`, `Q2`, `Stub Period`, etc.).
5. **No Data Hallucination:** Unavailable fields are explicitly marked `"Not available"`; estimates are tagged `"Estimate"`.
6. **Temporal Separation (Pre-IPO vs. Post-Listing):** Pre-offering expectations are strictly separated from post-listing outcomes to eliminate look-ahead bias during backtesting.
7. **Strict Segment Segregation:** `segment` accepts only `"Mainboard"` or `"SME"` (never hybrid tags).
8. **Comprehensive Status Lifecycle:** Explicit state machine: `Upcoming`, `Opening Today`, `Currently Open`, `Closing Today`, `Closed`, `Listed`, `Withdrawn`, `Not Available`.
9. **Backtesting Readiness:** Field structure natively supports longitudinal tracking across 7d, 30d, 90d, 180d, and 1-year windows.
10. **Mathematical 40% Target Standardization:** `target_price = reference_price × 1.40` is calculated without probability or guarantee claims.
11. **Strict Prohibition of Recommendations:** No fields for `"buy"`, `"sell"`, `"apply"`, `"rating"`, or `"target score"`.
12. **Prohibition of IPO Ordinal Ranking:** No fields for `"rank"`, `"score"`, or `"best_ipo"`.
13. **Unofficial Nature of GMP:** Grey Market Premium is stored strictly as `Unofficial GMP` and cannot trigger or validate a scenario independently.
14. **No Qualitative Anchor Bias:** Anchor fields capture factual share allocations, lock-ins, and institutional categories without subjective "quality" scoring.
15. **Extensible & Backward Compatible:** Additional metadata fields can be appended without mutating primary key structures or schema contracts.

---

## 2. Core Data Structures & Entity Definitions

### 2.1 Primary IPO Entity (`ipo_entity`)

The central master record identifying the offering.

| Field Name | Type | Allowed Values / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `ipo_id` | String | Unique slug (e.g., `IND-MB-2026-MONEYVIEW`) | Primary system key |
| `company_name` | String | Text | Commercial / brand name |
| `company_legal_name`| String | Text | Statutory name in RoC / SEBI filings |
| `ticker_symbol` | String | Text or `"Not available"` | NSE/BSE proposed trading symbol |
| `isin` | String | 12-character alphanumeric or `"Not available"` | International Securities Identification Number |
| `segment` | Enum | `Mainboard`, `SME` | Primary exchange board |
| `sector` | String | Standardized industry sector | Macro sector classification |
| `industry` | String | Granular sub-industry | Sub-industry classification |

#### IPO Status & Timestamps (`ipo_status`)

| Field Name | Type | Allowed Values / Constraints | Description |
| :--- | :--- | :--- | :--- |
| `status` | Enum | `Upcoming`, `Opening Today`, `Currently Open`, `Closing Today`, `Closed`, `Listed`, `Withdrawn`, `Not Available` | Current operational state as of `data_cutoff` |
| `research_date` | Date | `YYYY-MM-DD` | Date of analyst evaluation |
| `research_time` | Time | `HH:MM:SS` (IST) | Time of analyst evaluation |
| `data_cutoff` | Timestamp | `YYYY-MM-DD HH:MM:SS` | Latest data reconciliation timestamp |
| `open_date` | Date | `YYYY-MM-DD` | Public bidding opening date |
| `close_date` | Date | `YYYY-MM-DD` | Public bidding closing date |
| `listing_date` | Date | `YYYY-MM-DD` or `"Not available"` | Actual or tentative stock exchange listing date |
| `listing_status` | Enum | `Pre-Listing`, `Listed`, `Deferred` | Lifecycle stage relative to secondary trading |

---

### 2.2 Issue Capital Structure (`issue_structure`)

Captures the offering mechanics and share breakdown.

| Field Name | Type | Value Constraint / Formula | Description |
| :--- | :--- | :--- | :--- |
| `issue_size` | Decimal | `fresh_issue_amount + ofs_amount` | Total gross offering amount (₹ Cr) |
| `fresh_issue_amount` | Decimal | ₹ in Crores | Capital raised by issuer company |
| `ofs_amount` | Decimal | ₹ in Crores | Secondary shares sold by existing holders |
| `fresh_issue_percentage` | Decimal | `(fresh_issue_amount / issue_size) * 100` | Fresh issue share of total (%) |
| `ofs_percentage` | Decimal | `(ofs_amount / issue_size) * 100` | OFS share of total (%) |
| `face_value` | Decimal | ₹ per share | Nominal statutory share face value |
| `price_band_low` | Decimal | ₹ per share | Minimum bidding floor price |
| `price_band_high` | Decimal | ₹ per share | Maximum bidding cap price |
| `issue_price` | Decimal | ₹ per share or `"Not available"` | Discovered final allotment price |
| `lot_size` | Integer | Minimum bid multiplier | Equity shares per bidding lot |
| `minimum_investment` | Decimal | `lot_size * price_band_high` | Minimum retail application capital (₹) |
| `employee_reservation`| Decimal | ₹ in Crores or `"Not available"` | Quota reserved for eligible employees |
| `shareholder_reservation`| Decimal | ₹ in Crores or `"Not available"` | Quota reserved for parent firm shareholders |
| `other_reservation` | Decimal | ₹ in Crores or `"Not available"` | Specialized policy reservations |

*Value Provenance Envelope:* Every numerical field in `issue_structure` is backed by sub-attributes: `value`, `unit`, `currency`, `source`, `source_date`, `retrieval_timestamp`, and `data_type` (`Reported`, `Calculated`, `Estimate`, `Not available`).

---

### 2.3 Objects of the Issue (`objects_of_issue`)

Tracks the deployment of fresh issue proceeds.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `debt_repayment` | Object | Prepayment or repayment of outstanding borrowings |
| `capital_expenditure`| Object | Land, machinery, plant modernization, or software |
| `working_capital` | Object | Funding incremental working capital requirements |
| `acquisitions_or_MA` | Object | Inorganic strategic acquisitions or investments |
| `general_corporate_purposes` | Object | GCP allocation (subject to regulatory caps) |
| `issue_expenses` | Object | Merchant banker, legal, registrar, advertising fees |
| `other_use` | Object | Any other disclosed object |

*Each Object Record Schema:*
```json
{
  "purpose": "Debt Repayment / Prepayment",
  "amount": 220.00,
  "percentage_of_fresh_issue": 61.97,
  "source": "RHP Section III, Page 82",
  "source_date": "2026-09-21",
  "disclosure_status": "Disclosed" 
}
```
*`disclosure_status` constraints:* `Disclosed`, `Estimated`, `Not available`. Invented allocations are strictly prohibited.

---

### 2.4 Longitudinal Financial Records (`financial_data`)

A multi-period collection storing historical audited financials.

| Field Name | Type | Period Support | Calculation / Rule |
| :--- | :--- | :--- | :--- |
| `financial_period` | String | `FY2024`, `FY2025`, `FY2026`, `Q1_FY2027` | Specific accounting period name |
| `period_type` | Enum | `FY`, `Q1`, `Q2`, `Q3`, `Q4`, `LTM`, `Stub Period`, `Not available` | Standardized period interval |
| `revenue` | Decimal | ₹ in Crores | Revenue from Operations |
| `revenue_growth` | Decimal | Percentage (%) | `((revenue_t - revenue_t-1) / revenue_t-1) * 100` |
| `EBITDA` | Decimal | ₹ in Crores | Operating profit before interest, tax, dep/amort |
| `EBITDA_margin` | Decimal | Percentage (%) | `(EBITDA / revenue) * 100` |
| `PAT` | Decimal | ₹ in Crores | Net profit after tax and minority interests |
| `PAT_growth` | Decimal | Percentage (%) | `((PAT_t - PAT_t-1) / PAT_t-1) * 100` |
| `EPS` | Decimal | ₹ per share | Diluted earnings per share (restated post-split) |
| `book_value_per_share`| Decimal | ₹ per share | Net Worth / Diluted Equity Shares |
| `ROE` | Decimal | Percentage (%) | `(PAT / Net Worth) * 100` |
| `ROCE` | Decimal | Percentage (%) | `(EBIT / Capital Employed) * 100` |
| `total_debt` | Decimal | ₹ in Crores | Short-term + long-term borrowings |
| `net_debt` | Decimal | ₹ in Crores | `total_debt - (cash + cash equivalents)` |
| `debt_equity` | Decimal | Multiple (x) | `total_debt / Net Worth` |
| `operating_cash_flow` | Decimal | ₹ in Crores | Cash flow from operating activities (CFO) |
| `investing_cash_flow` | Decimal | ₹ in Crores | Cash flow from investing activities (CFI) |
| `financing_cash_flow` | Decimal | ₹ in Crores | Cash flow from financing activities (CFF) |
| `free_cash_flow` | Decimal | ₹ in Crores | `operating_cash_flow - capital_expenditures` |

---

### 2.5 Valuation Benchmarks (`valuation_data`)

| Field Name | Type | Constraints / Rules | Description |
| :--- | :--- | :--- | :--- |
| `issue_pe` | Decimal | Calculated: `issue_price / reference_eps` | Price-to-Earnings at issue price |
| `issue_pb` | Decimal | Calculated: `issue_price / reference_book_value_per_share` | Price-to-Book at issue price |
| `industry_pe` | Decimal | Sourced from exchange/sector benchmark | Sector average P/E multiple |
| `industry_pb` | Decimal | Sourced from exchange/sector benchmark | Sector average P/B multiple |
| `peer_average_pe` | Decimal | Calculated across verified listed peers | Peer group median/mean P/E |
| `peer_average_pb` | Decimal | Calculated across verified listed peers | Peer group median/mean P/B |
| `reference_eps` | Decimal | Trailing 12-month or latest full FY EPS | EPS base used for valuation |
| `reference_book_value_per_share` | Decimal | Latest restated NAV per share | Book value base used for valuation |
| `valuation_method` | String | Descriptive (e.g., Diluted Trailing FY26 P/E) | Methodological note |
| `valuation_source` | String | Prospectus / Exchange circular reference | Authoritative source |
| `valuation_date` | Date | `YYYY-MM-DD` | Date of multiple computation |

---

### 2.6 The 40% Target Scenario Model (`scenario_40_percent`)

A standardized analytical container evaluating the conditional +40% scenario hypothesis.

| Field Name | Type | Constraints / Formula | Description |
| :--- | :--- | :--- | :--- |
| `reference_price` | Decimal | Upper price band (open) or Issue price (closed) | Baseline calculation price (₹) |
| `target_price` | Decimal | `reference_price * 1.40` | +40.0% scenario price target (₹) |
| `required_price_movement` | Decimal | Exactly `40.00` | Percentage move required |
| `target_pe` | Decimal | `target_price / reference_eps` (or `"Not available"`) | Valuation multiple implied at target |
| `target_pb` | Decimal | `target_price / reference_book_value_per_share` | Implied P/B multiple at target |
| `supporting_factors` | Array | Text bullet points | Empirical evidence supporting scenario |
| `contradictory_factors` | Array | Text bullet points | Empirical evidence opposing scenario |
| `scenario_status` | Enum | `Supported`, `Not supported`, `Insufficient evidence` | Analytical classification |
| `scenario_methodology` | String | Fixed standard text | Analytical hypothesis disclaimer |
| `scenario_data_timestamp` | Timestamp | `YYYY-MM-DD HH:MM:SS` | Timestamp when scenario was evaluated |

*Prohibited Fields:* `probability_of_40_percent`, `guaranteed_return`, `expected_return`, `recommendation`, `buy_signal`, `sell_signal` are strictly forbidden.

---

### 2.7 Bidding & Subscription Dynamics (`subscription_data`)

Segregated tracking of the exchange order book across investor tiers.

| Category Slug | Category Description | Application Size Limits |
| :--- | :--- | :--- |
| `QIB` | Qualified Institutional Buyers | Institutional allocation (ex-Anchor) |
| `NII_total` | Non-Institutional Investors (Total) | Applications > ₹2,00,000 |
| `sHNI` | Small HNI (Sub-tier of NII) | Applications > ₹2,00,000 and $\le$ ₹10,00,000 |
| `bHNI` | Big HNI (Sub-tier of NII) | Applications > ₹10,00,000 |
| `retail` | Retail Individual Investors (RII) | Applications up to ₹2,00,000 |
| `employee` | Employee Reservation Quota | Specific reservation pool |
| `shareholder` | Parent Shareholder Reservation | Specific reservation pool |
| `other` | Specialized Quota | Custom reservation |
| `total_subscription` | Cumulative Issue Subscription Multiple | Total bids across all categories |

*Per-Category Data Schema:*
```json
{
  "shares_offered": 81481481,
  "shares_bid": 297407405,
  "subscription_multiple": 3.65,
  "source": "NSE Cumulative Bid Log",
  "source_date": "2026-09-24",
  "retrieval_timestamp": "2026-09-24 10:30:00"
}
```

---

### 2.8 Anchor Book & Investor Allocations (`anchor_data`)

Factual reporting of institutional anchor allocations without subjective bias.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `anchor_allocation` | Decimal | Total anchor placement amount (₹ Cr) |
| `anchor_price` | Decimal | Fixed anchor issue price (₹ per share) |
| `anchor_investor_count` | Integer | Total institutional entities participating |
| `anchor_allocation_percentage`| Decimal | Percentage of overall offering allocated to anchors |
| `lock_in_30_day` | Date | Expiry date of 50% anchor shares (30 days from allotment) |
| `lock_in_90_day` | Date | Expiry date of remaining 50% shares (90 days from allotment) |

#### Child Record: `anchor_investors`
- `investor_name`: Statutory institutional name.
- `investor_type`: Strictly `DII`, `FPI`, `Mutual Fund`, `Insurance`, `Other`, or `Not available`.
- `allocation_amount`: ₹ in Crores.
- `allocation_shares`: Number of shares allotted.
- `allocation_percentage`: Share of total anchor book (%).
- `anchor_price`: Issue price.
- `source` & `source_date`: Exchange filing citation.

*Prohibited Fields:* `anchor_quality_score`, `anchor_strength`, `anchor_rating`, `anchor_quality` are forbidden.

---

### 2.9 Indicative Grey Market Data (`gmp_data`)

| Field Name | Type | Constraints / Disclaimers | Description |
| :--- | :--- | :--- | :--- |
| `gmp_value` | Decimal | Currency in ₹ | Premium over upper price band |
| `gmp_percentage` | Decimal | `(gmp_value / reference_price) * 100` | Percentage indicative premium |
| `gmp_date` | Date | `YYYY-MM-DD` | Date of dealer quote |
| `gmp_time` | Time | `HH:MM:SS` (IST) | Time of dealer quote |
| `reference_price` | Decimal | ₹ per share | Base offering price |
| `implied_price` | Decimal | `reference_price + gmp_value` | Indicative implied listing level |
| `source` | String | News portal / OTC aggregator name | Originating publication |
| `source_type` | Enum | `Unofficial GMP` | Fixed source classification |

*Governance Mandate:* The schema explicitly codifies that GMP is unofficial, unregulated, fluctuates rapidly, does not guarantee listing price, and cannot independently determine scenario classifications. Prohibited: `gmp_signal`, `gmp_buy_score`, `gmp_confidence`.

---

### 2.10 Listed Competitor Benchmarks (`peer_companies`)

Array of direct domestic listed competitors:
- `company_name`: Peer corporate name.
- `ticker`: NSE/BSE ticker symbol.
- `market_cap`: ₹ in Crores.
- `revenue`: FY revenue from operations (₹ Cr).
- `PAT`: FY net profit (₹ Cr).
- `EPS`: Diluted EPS (₹).
- `PE`: Trailing P/E multiple.
- `PB`: Price-to-Book multiple.
- `ROE`: Return on Equity (%).
- `ROCE`: Return on Capital Employed (%).
- `debt_equity`: Debt-to-Equity ratio.
- `source` & `source_date`: Regulatory filing / exchange feed citation.

---

### 2.11 Disclosed Risk Matrix (`risk_data`)

Captures material risks cited in statutory offer documents (RHP Section II):
- Categories: `business_risk`, `financial_risk`, `debt_risk`, `sector_risk`, `regulatory_risk`, `valuation_risk`, `customer_concentration_risk`, `promoter_risk`, `execution_risk`, `market_risk`, `other_risk`.
- Structure per risk: `risk_description`, `source`, `source_date`, `severity` (`High`, `Medium`, `Low`, `Not available`).
- *Prohibition:* Risk severity must never be converted into an algorithmic recommendation score.

---

### 2.12 Source Provenance Envelope (`source`)

Standardized provenance object attached to all primary research data:
```json
{
  "source_name": "SEBI Red Herring Prospectus",
  "source_url": "https://www.sebi.gov.in/filings/public-issues/sep-2026/moneyview-rhp.pdf",
  "source_type": "Official Offer Document",
  "publication_date": "2026-09-21",
  "retrieval_timestamp": "2026-09-24 10:45:00",
  "page_or_section": "Section III, Page 78",
  "data_type": "Reported",
  "notes": "Verified against RoC filing"
}
```
*`source_type` supported values:* `NSE`, `BSE`, `SEBI`, `Official Offer Document`, `Company Filing`, `Registrar`, `Financial Publication`, `GMP Source`, `Calculated`, `Other`.

---

### 2.13 Data Quality Assessment (`data_quality`)

- `completeness_status`: `Complete`, `Partial`, `Insufficient evidence`.
- `source_verification_status`: `Verified`, `Partially verified`, `Not verified`.
- `last_verified`: Timestamp.
- `missing_fields`: Array of strings identifying null/missing datapoints.
- `conflicting_data`: Array of documented reporting discrepancies.
- `notes`: Analyst audit log.

---

### 2.14 Historical Performance & Backtesting Schema (`historical_ipo` & `performance_events`)

Dedicated structures reserved for future Phase 4 & Phase 5 backtesting.

#### Record Structure: `historical_ipo` (Post-Listing Only)
- `historical_ipo`: Boolean flag (`true` only after listing has occurred).
- `ipo_year`: Calendar year of listing.
- `listing_price`: Official discovery price at opening of trading (₹).
- `listing_day_close`: Official closing price on listing day (₹).
- `listing_day_high`: Peak intraday price on listing day (₹).
- `listing_day_low`: Minimum intraday price on listing day (₹).
- `listing_day_return`: Percentage listing gain/loss from issue price (`((listing_day_close - issue_price) / issue_price) * 100`).
- `post_listing_7d_return`: Closing return after 7 calendar days.
- `post_listing_30d_return`: Closing return after 30 calendar days.
- `post_listing_90d_return`: Closing return after 90 calendar days.
- `post_listing_180d_return`: Closing return after 180 calendar days.
- `post_listing_1y_return`: Closing return after 1 year.
- `max_upside_from_issue_price`: Highest recorded market price vs. issue price (%).
- `max_drawdown_from_issue_price`: Maximum decline recorded relative to issue price (%).

#### Longitudinal Event Stream: `performance_events`
- `event_date`: `YYYY-MM-DD`.
- `event_type`: `Listing`, `Day 1`, `Day 7`, `Day 30`, `Day 90`, `Day 180`, `1 Year`, `Target Reached`, `Drawdown`, `Other`.
- `reference_price`: Initial benchmark price (₹).
- `market_price`: Closing price on event date (₹).
- `return_percentage`: Gain/loss from reference price.
- `days_from_listing`: Integer days elapsed.
- `reached_40_percent_target`: Boolean (`true` / `false`).
- `source`: Official exchange historical price feed.

---

## 3. Data Lifecycle & Transition Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    1. RAW RESEARCH DATA                     │
│    • Prospectuses (RHP/DRHP) • Exchange Bids • OTC Feeds    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  2. VALIDATED SOURCE DATA                   │
│   • Source URLs • Period Tags • Provenance Attribution      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 3. CALCULATED METRICS ENGINE                │
│   • Normalized Multiples • YoY Growth • 40% Target Price    │
│   Rule: Raw source values are NEVER overwritten by computed │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 4. MASTER TABULAR DATABASE                  │
│       • Phase 2: Google Sheets  • Phase 7: MySQL Tables     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│           5. POST-LISTING & BACKTESTING ENGINE              │
│       • Phase 4: Event Stream  • Phase 5: Hit-Rate Audit    │
│       Rule: Strict Pre-IPO vs Post-Listing separation       │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Google Sheets Mapping (Phase 2 Architecture)

The schema maps directly into an 11-tab collaborative Google Sheets datastore:

### Tab 1: `IPO_Master`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Reported | Unique entity key | `IND-MB-2026-MONEYVIEW` |
| `company_name` | String | Required | Reported | Commercial brand name | `Moneyview Limited` |
| `segment` | String | Required | Reported | Market segment (`Mainboard`/`SME`) | `Mainboard` |
| `status` | String | Required | Reported | Active operational status | `Opening Today` |
| `open_date` | Date | Required | Reported | Subscription start date | `2026-09-24` |
| `close_date` | Date | Required | Reported | Subscription end date | `2026-09-28` |
| `listing_date`| Date | Optional | Reported | Tentative or actual listing | `2026-10-01` |
| `price_band_low` | Decimal | Required | Reported | Lower price boundary | `32.00` |
| `price_band_high`| Decimal | Required | Reported | Upper price boundary | `34.00` |
| `issue_price` | Decimal | Optional | Reported | Final allotment price | `34.00` |
| `lot_size` | Integer | Required | Reported | Shares per bid lot | `441` |
| `minimum_investment` | Decimal | Required | Calculated | `lot_size * price_band_high` | `14994.00` |
| `issue_size` | Decimal | Required | Reported | Total offering size (₹ Cr) | `1091.68` |
| `fresh_issue_amount` | Decimal | Required | Reported | Fresh capital raised (₹ Cr)| `750.00` |
| `ofs_amount` | Decimal | Required | Reported | Shares sold by promoters (₹ Cr)| `341.68` |
| `fresh_percentage` | Decimal | Required | Calculated | Fresh share of total issue (%) | `68.70` |
| `lead_managers`| String | Optional | Reported | Syndicate banking names | `Axis Capital, BofA, Kotak` |
| `registrar` | String | Required | Reported | Share registrar entity | `KFin Technologies Ltd` |
| `data_cutoff` | Timestamp | Required | Reported | Data reconciliation time | `2026-09-24 10:45:00` |

### Tab 2: `Financials`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `period_name` | String | Required | Reported | Accounting period tag | `FY2026` |
| `period_type` | String | Required | Reported | `FY`, `Q1`, `Stub Period` | `FY` |
| `revenue` | Decimal | Required | Reported | Revenue from Operations (₹ Cr) | `3404.27` |
| `revenue_growth` | Decimal | Optional | Calculated | YoY revenue growth rate (%) | `43.12` |
| `EBITDA` | Decimal | Required | Reported | Operating EBITDA (₹ Cr) | `968.92` |
| `EBITDA_margin` | Decimal | Required | Calculated | `(EBITDA / revenue) * 100` | `28.46` |
| `PAT` | Decimal | Required | Reported | Net profit after tax (₹ Cr) | `242.71` |
| `PAT_growth` | Decimal | Optional | Calculated | YoY net profit growth rate (%) | `1.01` |
| `EPS` | Decimal | Required | Reported | Diluted restated EPS (₹) | `0.79` |
| `ROE` | Decimal | Optional | Reported | Return on Equity (%) | `16.80` |
| `total_debt` | Decimal | Required | Reported | Total borrowings (₹ Cr) | `1450.00` |
| `debt_equity` | Decimal | Required | Reported | Leverage ratio (x) | `1.45` |
| `operating_cash_flow` | Decimal | Optional | Reported | Cash flow from operations (₹ Cr) | `412.50` |
| `source_ref` | String | Required | Source Tag | Prospectus page reference | `RHP Section V, Page 198` |

### Tab 3: `Subscription`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `category` | String | Required | Reported | `QIB`, `NII_Total`, `sHNI`, `bHNI`, `Retail` | `sHNI` |
| `shares_offered`| Integer | Required | Reported | Shares reserved for tier | `12500000` |
| `shares_bid` | Integer | Required | Reported | Cumulative shares bid | `1520000` |
| `subscription_multiple` | Decimal | Required | Calculated | `shares_bid / shares_offered` | `0.12` |
| `timestamp` | Timestamp | Required | Reported | Bidding timestamp | `2026-09-24 10:30:00` |

### Tab 4: `Anchors`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `investor_name`| String | Required | Reported | Disclosed institution name | `SBI Mutual Fund` |
| `investor_type`| String | Required | Reported | `DII`, `FPI`, `Mutual Fund` | `DII` |
| `amount_cr` | Decimal | Required | Reported | Allocation amount (₹ Cr) | `50.00` |
| `shares_allotted`| Integer | Required | Reported | Number of equity shares | `14705882` |
| `lock_in_30d` | Date | Required | Reported | 50% lock-in expiry date | `2026-10-29` |
| `lock_in_90d` | Date | Required | Reported | Remaining 50% lock-in date | `2026-12-28` |

### Tab 5: `GMP`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `gmp_value` | Decimal | Required | Reported | Unofficial premium quote (₹) | `14.00` |
| `reference_price`| Decimal | Required | Reported | Base price (₹) | `34.00` |
| `gmp_percentage`| Decimal | Required | Calculated | `(gmp_value / ref_price) * 100` | `41.18` |
| `quote_timestamp`| Timestamp | Required | Reported | Dealer quote timestamp | `2026-09-24 09:30:00` |
| `source_type` | String | Required | Fixed Flag | Must be `Unofficial GMP` | `Unofficial GMP` |

### Tab 6: `Valuation`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `reference_price`| Decimal | Required | Reported | Upper band or issue price (₹) | `34.00` |
| `reference_eps` | Decimal | Required | Reported | Trailing EPS used (₹) | `0.79` |
| `issue_pe` | Decimal | Required | Calculated | `reference_price / reference_eps` | `43.04` |
| `issue_pb` | Decimal | Optional | Calculated | `reference_price / NAV_per_share` | `5.80` |
| `industry_pe` | Decimal | Optional | Reported | Sector benchmark multiple | `28.50` |

### Tab 7: `Peers`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `peer_name` | String | Required | Reported | Direct listed competitor | `PB Fintech Limited` |
| `ticker` | String | Required | Reported | Exchange ticker | `POLICYBZR` |
| `peer_pe` | Decimal | Required | Reported | Competitor P/E multiple | `92.00` |
| `peer_roe` | Decimal | Optional | Reported | Competitor Return on Equity (%) | `12.40` |

### Tab 8: `Risks`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `risk_category`| String | Required | Reported | Risk category classification | `regulatory_risk` |
| `risk_summary` | String | Required | Reported | Statutory disclosure summary | `RBI FLDG cap of 5% on default loss` |
| `severity` | String | Required | Reported | `High`, `Medium`, `Low` | `High` |

### Tab 9: `Scenarios`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Target IPO key | `IND-MB-2026-MONEYVIEW` |
| `reference_price` | Decimal | Required | Reported | Starting baseline price (₹) | `34.00` |
| `target_price_40` | Decimal | Required | Calculated | `reference_price * 1.40` | `47.60` |
| `required_move` | Decimal | Required | Fixed | Exactly `40.00` | `40.00` |
| `target_pe` | Decimal | Optional | Calculated | `target_price_40 / reference_eps` | `60.25` |
| `scenario_status`| Enum | Required | Evaluated | `Supported`, `Not supported`, `Insufficient evidence` | `Insufficient evidence` |
| `evaluation_date`| Timestamp | Required | System Time | Timestamp of evaluation | `2026-09-24 11:00:00` |

### Tab 10: `Sources`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `source_id` | String | Required | Primary Key | Provenance record key | `SRC-MV-RHP-01` |
| `ipo_id` | String | Required | Foreign Key | Associated IPO key | `IND-MB-2026-MONEYVIEW` |
| `source_name` | String | Required | Reported | Document / platform name | `SEBI RHP Filing` |
| `source_url` | String | Required | Reported | Web link | `https://www.sebi.gov.in/...` |
| `source_type` | String | Required | Classification | Sourcing category | `Official Offer Document` |

### Tab 11: `Historical_Performance`
| Column Name | Data Type | Required/Optional | Reported / Calculated | Description | Example Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ipo_id` | String | Required | Foreign Key | Associated IPO key | `IND-MB-2026-MONEYVIEW` |
| `issue_price` | Decimal | Required | Reported | Final issue price (₹) | `34.00` |
| `listing_open` | Decimal | Optional | Reported | Open price on Day 1 (₹) | `Not available` (Pre-listing) |
| `listing_close`| Decimal | Optional | Reported | Close price on Day 1 (₹) | `Not available` (Pre-listing) |
| `listing_return`| Decimal | Optional | Calculated | Gain on listing day (%) | `Not available` (Pre-listing) |
| `post_30d_return`| Decimal | Optional | Calculated | Return after 30 days (%) | `Not available` (Pre-listing) |
| `reached_40_target`| Boolean | Optional | Evaluated | True if market price $\ge$ target | `Not available` (Pre-listing) |

---

## 5. Python Analysis Engine Mapping (Phase 3 Specification)

The Phase 3 Python engine will ingest these standardized schema structures using `pandas` and data classes.

### 5.1 Programmatic Input Fields
- **Financial Inputs:** Multi-period restated `revenue`, `EBITDA`, `PAT`, `EPS`, `debt`, `operating_cash_flow`.
- **Valuation Inputs:** `price_band_high`, `issue_price`, `reference_eps`, `reference_book_value_per_share`, `peer_pe`.
- **Subscription Inputs:** Category-wise `shares_offered`, `shares_bid`, `subscription_multiple`.
- **Anchor Inputs:** `anchor_allocation`, `anchor_investor_count`, `lock_in_30_day`, `lock_in_90_day`.
- **Market Sentiment:** `gmp_value`, `reference_price` (tagged strictly as unofficial sentiment).
- **Risk Metadata:** Array of categorized risk disclosures.

### 5.2 Algorithmic Computations
1. **Growth Analytics:** Computes 3-year compound annual growth rates (CAGR) and YoY velocity:
   $$\text{Growth Rate (\%)} = \left(\frac{\text{Metric}_{t} - \text{Metric}_{t-1}}{\text{Metric}_{t-1}}\right) \times 100$$
2. **Valuation Spreads:** Calculates discount/premium relative to peer median:
   $$\text{Valuation Spread (\%)} = \left(\frac{\text{Issue PE} - \text{Peer Median PE}}{\text{Peer Median PE}}\right) \times 100$$
3. **40% Scenario Modeling:**
   $$\text{Target Price} = \text{Reference Price} \times 1.40$$
   $$\text{Implied Target PE} = \frac{\text{Target Price}}{\text{Reference EPS}}$$
4. **Subscription Acceleration:** Measures Day-over-Day bidding acceleration between Day 1, Day 2, and Day 3 across QIB and NII tiers.

---

## 6. Historical Backtesting & Look-Ahead Governance (Phase 4 & 5)

To prevent look-ahead bias, the schema enforces a strict temporal partition between **Pre-IPO Research Data** and **Post-Listing Performance Data**.

### 6.1 Pre-IPO Dataset (Information Boundary: Before Trading Commences)
*Available prior to listing:*
- Statutory RHP financials, balance sheets, and objects of the issue.
- Anchor book allocations and disclosed participants.
- Final exchange subscription multiples (QIB, sHNI, bHNI, Retail).
- Pre-listing unofficial GMP trajectories and timestamps.
- Pre-computed 40% Target Price and implied target multiples.

### 6.2 Post-Listing Dataset (Information Boundary: After Trading Commences)
*Recorded strictly post-listing:*
- Opening discovered price, listing day high/low, and listing day closing price.
- 7-day, 30-day, 90-day, 180-day, and 1-year closing price streams.
- Days elapsed to reach +40% target (if achieved).
- Maximum upside and maximum drawdown observed.

### 6.3 Backtesting Inquiry Matrix
The backtesting engine will execute SQL / Python queries answering:
1. What was the exact baseline issue price and implied P/E?
2. Did the market price reach or exceed `target_price_40`?
3. How many calendar/trading days elapsed before the +40% target was reached?
4. What was the maximum drawdown before any +40% upward movement?
5. Did issues classified as `Supported` hit +40% at a statistically higher rate than those classified as `Not supported` or `Insufficient evidence`?
6. Which pre-IPO variable (e.g., QIB oversubscription vs. starting valuation spread) exhibited the highest predictive correlation with positive listing gains?

---

## 7. Concrete Sample Record: Moneyview Limited

Below is an instantiated sample record complying with schema version 1.0.  
*(Note: Example provided strictly for schema demonstration; does not constitute financial advice or an investment recommendation).*

```json
{
  "schema_version": "1.0",
  "ipo_entity": {
    "ipo_id": "IND-MB-2026-MONEYVIEW",
    "company_name": "Moneyview Limited",
    "company_legal_name": "Whizdm Innovations Private Limited",
    "ticker_symbol": "MONEYVIEW",
    "isin": "Not available",
    "segment": "Mainboard",
    "sector": "Fintech / Financial Services",
    "industry": "Digital Lending Platforms"
  },
  "ipo_status": {
    "status": "Opening Today",
    "research_date": "2026-09-24",
    "research_time": "11:15:00",
    "data_cutoff": "2026-09-24 10:45:00",
    "open_date": "2026-09-24",
    "close_date": "2026-09-28",
    "listing_date": "2026-10-01",
    "listing_status": "Pre-Listing"
  },
  "issue_structure": {
    "issue_size": { "value": 1091.68, "unit": "Crores", "currency": "INR", "data_type": "Reported", "source": "RHP Pg 68" },
    "fresh_issue_amount": { "value": 750.00, "unit": "Crores", "currency": "INR", "data_type": "Reported", "source": "RHP Pg 68" },
    "ofs_amount": { "value": 341.68, "unit": "Crores", "currency": "INR", "data_type": "Reported", "source": "RHP Pg 68" },
    "fresh_issue_percentage": { "value": 68.70, "unit": "Percent", "data_type": "Calculated", "source": "System Formula" },
    "ofs_percentage": { "value": 31.30, "unit": "Percent", "data_type": "Calculated", "source": "System Formula" },
    "face_value": { "value": 1.00, "unit": "INR", "data_type": "Reported", "source": "RHP Pg 68" },
    "price_band_low": { "value": 32.00, "unit": "INR", "data_type": "Reported", "source": "RHP Notice" },
    "price_band_high": { "value": 34.00, "unit": "INR", "data_type": "Reported", "source": "RHP Notice" },
    "issue_price": { "value": "Not available", "data_type": "Not available", "source": "Pending Allotment" },
    "lot_size": { "value": 441, "unit": "Shares", "data_type": "Reported", "source": "Bidding Circular" },
    "minimum_investment": { "value": 14994.00, "unit": "INR", "data_type": "Calculated", "source": "Lot * High Band" }
  },
  "objects_of_issue": [
    {
      "purpose": "Default Loss Guarantee (DLG) arrangements loan growth",
      "amount": 325.00,
      "percentage_of_fresh_issue": 43.33,
      "source": "RHP Section III, Pg 78",
      "source_date": "2026-09-21",
      "disclosure_status": "Disclosed"
    },
    {
      "purpose": "Capital base augmentation of Whizdm Finance Pvt Ltd",
      "amount": 250.00,
      "percentage_of_fresh_issue": 33.33,
      "source": "RHP Section III, Pg 79",
      "source_date": "2026-09-21",
      "disclosure_status": "Disclosed"
    },
    {
      "purpose": "General corporate purposes and issue expenses",
      "amount": 175.00,
      "percentage_of_fresh_issue": 23.34,
      "source": "RHP Section III, Pg 80",
      "source_date": "2026-09-21",
      "disclosure_status": "Disclosed"
    }
  ],
  "financial_data": [
    {
      "financial_period": "FY2025",
      "period_type": "FY",
      "revenue": { "value": 2378.53, "unit": "Crores", "data_type": "Reported" },
      "revenue_growth": { "value": "Not available", "data_type": "Not available" },
      "EBITDA": { "value": 697.98, "unit": "Crores", "data_type": "Reported" },
      "EBITDA_margin": { "value": 29.35, "unit": "Percent", "data_type": "Calculated" },
      "PAT": { "value": 240.28, "unit": "Crores", "data_type": "Reported" },
      "PAT_growth": { "value": "Not available", "data_type": "Not available" },
      "EPS": { "value": 0.78, "unit": "INR", "data_type": "Reported" }
    },
    {
      "financial_period": "FY2026",
      "period_type": "FY",
      "revenue": { "value": 3404.27, "unit": "Crores", "data_type": "Reported" },
      "revenue_growth": { "value": 43.12, "unit": "Percent", "data_type": "Calculated" },
      "EBITDA": { "value": 968.92, "unit": "Crores", "data_type": "Reported" },
      "EBITDA_margin": { "value": 28.46, "unit": "Percent", "data_type": "Calculated" },
      "PAT": { "value": 242.71, "unit": "Crores", "data_type": "Reported" },
      "PAT_growth": { "value": 1.01, "unit": "Percent", "data_type": "Calculated" },
      "EPS": { "value": 0.79, "unit": "INR", "data_type": "Reported" },
      "ROE": { "value": 16.80, "unit": "Percent", "data_type": "Reported" },
      "ROCE": { "value": 18.50, "unit": "Percent", "data_type": "Calculated" },
      "total_debt": { "value": 1450.00, "unit": "Crores", "data_type": "Reported" },
      "debt_equity": { "value": 1.45, "unit": "Multiple", "data_type": "Reported" },
      "operating_cash_flow": { "value": 412.50, "unit": "Crores", "data_type": "Reported" }
    },
    {
      "financial_period": "Q1_FY2027",
      "period_type": "Stub Period",
      "revenue": { "value": 1065.09, "unit": "Crores", "data_type": "Reported" },
      "PAT": { "value": 173.80, "unit": "Crores", "data_type": "Reported" }
    }
  ],
  "valuation_data": {
    "reference_price": 34.00,
    "reference_eps": 0.79,
    "issue_pe": { "value": 43.04, "data_type": "Calculated" },
    "issue_pb": { "value": 5.80, "data_type": "Calculated" },
    "industry_pe": { "value": 28.50, "data_type": "Reported" },
    "valuation_method": "Trailing Diluted P/E on FY26 Earnings",
    "valuation_source": "RHP Financial Statements",
    "valuation_date": "2026-09-24"
  },
  "scenario_40_percent": {
    "reference_price": 34.00,
    "target_price": 47.60,
    "required_price_movement": 40.00,
    "target_pe": 60.25,
    "target_pb": 8.12,
    "supporting_factors": [
      "Unofficial GMP quoted at ₹14.00 (+41.18%) on September 24 morning",
      "Q1 FY27 reported net profit reached ₹173.80 Cr",
      "20 institutional entities participated in anchor book"
    ],
    "contradictory_factors": [
      "Audited FY2026 annual PAT grew by only +1.01% YoY",
      "Target P/E of 60.25x represents substantial valuation stretch for unsecured consumer lending entity",
      "Unofficial GMP fluctuates rapidly and does not constitute exchange-regulated price discovery"
    ],
    "scenario_status": "Insufficient evidence",
    "scenario_methodology": "Standardized non-predictive scenario model evaluating plausibility of +40% move.",
    "scenario_data_timestamp": "2026-09-24 11:00:00"
  },
  "anchor_data": {
    "anchor_allocation": 327.50,
    "anchor_price": 34.00,
    "anchor_investor_count": 20,
    "anchor_allocation_percentage": 30.00,
    "lock_in_30_day": "2026-10-29",
    "lock_in_90_day": "2026-12-28",
    "anchor_investors": [
      {
        "investor_name": "SBI Mutual Fund Schemes",
        "investor_type": "DII",
        "allocation_amount": 50.00,
        "allocation_shares": 14705882,
        "allocation_percentage": 15.27,
        "source": "BSE Anchor Notice",
        "source_date": "2026-09-23"
      },
      {
        "investor_name": "Goldman Sachs India Equity Portfolio",
        "investor_type": "FPI",
        "allocation_amount": 30.00,
        "allocation_shares": 8823529,
        "allocation_percentage": 9.16,
        "source": "BSE Anchor Notice",
        "source_date": "2026-09-23"
      }
    ]
  },
  "gmp_data": {
    "gmp_value": 14.00,
    "gmp_percentage": 41.18,
    "gmp_date": "2026-09-24",
    "gmp_time": "09:30:00",
    "reference_price": 34.00,
    "implied_price": 48.00,
    "source": "NDTV Profit / InvestorGain Tracker",
    "source_type": "Unofficial GMP"
  },
  "historical_ipo": {
    "historical_ipo": false,
    "ipo_year": 2026,
    "listing_price": "Not available",
    "listing_day_close": "Not available",
    "listing_day_return": "Not available",
    "post_listing_30d_return": "Not available"
  },
  "data_quality": {
    "completeness_status": "Partial",
    "source_verification_status": "Verified",
    "last_verified": "2026-09-24 10:45:00",
    "missing_fields": [
      "isin",
      "issue_price",
      "final_subscription_multiples",
      "post_listing_outcomes"
    ],
    "conflicting_data": [],
    "notes": "Pre-listing Day 1 active issue. Final allotment and listing metrics pending."
  }
}
```
