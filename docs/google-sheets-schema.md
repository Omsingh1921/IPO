# Phase 2: Google Sheets IPO Database Specification & Operational SOP

**Specification Version:** `1.0`  
**Target Architecture:** Phase 2 (Google Sheets Tabular IPO Database)  
**System Role:** Lightweight, collaborative tabular datastore mapping to Schema Version 1.0 specifications (`docs/ipo-data-schema.md`).

---

## 1. Executive Summary & Design Principles

The Google Sheets IPO Database serves as the tabular data entry and research tracking layer for the **Indian IPO Research & Data Analysis Platform**. It implements an 11-tab normalized structure adhering strictly to 5 core design principles:

1. **Preserve Raw Data & Provenance:** Ground truth disclosures (RHP, exchange bid books) are stored alongside computed formulas.
2. **Explicit Data-Type Tagging:** Values carry explicit attributes or default classifications (`Reported`, `Calculated`, `Estimate`, `Not available`).
3. **No Data Hallucination:** Unavailable figures are written verbatim as `"Not available"`.
4. **Strict Mathematical Formulas:**
   $$\text{Target Price (+40\%)} = \text{Reference Price} \times 1.40$$
   $$\text{Required Price Movement} = 40.00\%$$
5. **Strict Governance & Prohibited Fields:** Ratings, buy/sell recommendations, ordinal ranks, and qualitative anchor quality scores are strictly barred across all 11 tabs.

---

## 2. 11-Tab Tabular Schema Specification

### Tab 1: `IPO_Master`
Master entity parameters and issue mechanics.
- **Columns:** `ipo_id`, `company_name`, `segment`, `status`, `open_date`, `close_date`, `listing_date`, `price_band_low`, `price_band_high`, `issue_price`, `lot_size`, `minimum_investment`, `issue_size`, `fresh_issue_amount`, `ofs_amount`, `fresh_percentage`, `lead_managers`, `registrar`, `data_cutoff`

### Tab 2: `Financials`
Longitudinal 3-year restated balance sheet and P&L entries.
- **Columns:** `ipo_id`, `period_name`, `period_type`, `revenue`, `revenue_growth`, `EBITDA`, `EBITDA_margin`, `PAT`, `PAT_growth`, `EPS`, `ROE`, `total_debt`, `debt_equity`, `operating_cash_flow`, `source_ref`

### Tab 3: `Subscription`
Segmented subscription multiples captured from exchange bid books (NSE/BSE).
- **Columns:** `ipo_id`, `category`, `shares_offered`, `shares_bid`, `subscription_multiple`, `timestamp`

### Tab 4: `Anchors`
Factual institutional anchor investor placement details.
- **Columns:** `ipo_id`, `investor_name`, `investor_type`, `amount_cr`, `shares_allotted`, `lock_in_30d`, `lock_in_90d`

### Tab 5: `GMP`
Time-series OTC Grey Market Premium quotes.
- **Columns:** `ipo_id`, `gmp_value`, `reference_price`, `gmp_percentage`, `quote_timestamp`, `source_type` (`Must strictly equal 'Unofficial GMP'`)

### Tab 6: `Valuation`
Issue valuation multiples and sector benchmarks.
- **Columns:** `ipo_id`, `reference_price`, `reference_eps`, `issue_pe`, `issue_pb`, `industry_pe`

### Tab 7: `Peers`
Direct listed domestic competitors.
- **Columns:** `ipo_id`, `peer_name`, `ticker`, `peer_pe`, `peer_roe`

### Tab 8: `Risks`
Statutory risk factors extracted from RHP Section II.
- **Columns:** `ipo_id`, `risk_category`, `risk_summary`, `severity`

### Tab 9: `Scenarios`
Conditional +40% upside scenario evaluation hypothesis.
- **Columns:** `ipo_id`, `reference_price`, `target_price_40`, `required_move`, `target_pe`, `scenario_status`, `evaluation_date`

### Tab 10: `Sources`
Centralized provenance registry mapping every record to its authoritative filing or circular.
- **Columns:** `source_id`, `ipo_id`, `source_name`, `source_url`, `source_type`

### Tab 11: `Historical_Performance`
Post-listing returns and secondary market price trajectories (Strictly segregated from Pre-IPO data).
- **Columns:** `ipo_id`, `issue_price`, `listing_open`, `listing_close`, `listing_return`, `post_30d_return`, `reached_40_target`

---

## 3. Standard Operating Procedure (SOP) for Updating Datastore

1. **Extraction:** Analyst or prompt engine extracts quantitative tables from RHP filings or exchange circulars.
2. **Tabular Ingestion:** Data is parsed using `SheetsDataMapper.record_to_tabular()`.
3. **Validation:** Ingested rows are audited using `SheetsTabularValidator` to enforce header correctness, math formula integrity (`target_price_40 == reference_price * 1.40`), and prohibition of recommendation signals.
4. **Source Linkage:** Every observation is populated with a valid `source_ref` or `source_id` matching an entry in the `Sources` tab.
