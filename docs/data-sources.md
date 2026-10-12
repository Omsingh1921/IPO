# IPO Data Sources & Classification Hierarchy

To ensure high data integrity and institutional research standards, this platform enforces a strict distinction between **Primary (Official / Regulatory)** sources and **Secondary / Indicative (Unofficial)** sources.

Every datapoint captured, logged, or referenced within the platform must be attributed to its originating source and classified according to the trust hierarchy outlined below.

---

## 1. Source Classification Hierarchy

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRIMARY OFFICIAL SOURCES                        │
│   • SEBI Regulatory Filings (DRHP, RHP, Addendums, Orders)            │
│   • NSE & BSE Official Bidding Platforms & Notices                     │
│   • Statutory Company Disclosures & Audited Financial Statements       │
│   Status: Ground Truth / Authoritative                                 │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       SECONDARY FINANCIAL SOURCES                      │
│   • Verified Financial Portals (Moneycontrol, Livemint, Chittorgarh)   │
│   • Peer Group Financial Filings & Exchange Annual Reports             │
│   • Brokerage / Research House Institutional Due Diligence Notes       │
│   Status: Informational / Cross-Verification Required                  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     UNOFFICIAL / INDICATIVE DATA                       │
│   • Grey Market Premium (GMP) Dealer Trackers & Aggregators           │
│   • Kostak Rates & Subject-to-Sauda Quotes                             │
│   Status: Unofficial Market Sentiment Only (Never Treated as Fact)     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Primary Sources (Authoritative & Verified)

Primary sources form the baseline truth for all corporate actions, capital structures, financial metrics, and official subscription figures.

### A. SEBI (Securities and Exchange Board of India)
- **Role:** Capital markets regulator for India.
- **Data Retrieved:**
  - Draft Red Herring Prospectus (DRHP) review status and observations.
  - Final Red Herring Prospectus (RHP) approvals.
  - Formal regulatory orders, exemptions, or show-cause notices involving the issuer or promoters.
- **Reliability:** Maximum (Regulatory Baseline).

### B. Stock Exchanges (NSE & BSE)
- **Role:** Primary trading venues and official book-building platforms.
- **Data Retrieved:**
  - Official IPO Bidding / Subscription data across categories:
    - Qualified Institutional Buyers (QIB - Anchor, Domestic, FII)
    - Non-Institutional Investors (NII / HNI - Small HNI & Big HNI)
    - Retail Individual Investors (RII)
    - Employee and Shareholder reservations
  - Final Basis of Allotment documents and Listing Day circulars.
  - Pre-open discovered prices and official listing day trading statistics.
- **Reliability:** Maximum (Exchange Settlement Ground Truth).

### C. Official IPO Prospectus (DRHP, RHP, and Price Band Addendum)
- **Role:** Statutory disclosures submitted by the company and Lead Merchant Bankers.
- **Data Retrieved:**
  - Complete issue structure (Fresh Issue vs. Offer for Sale / OFS split).
  - Objects of the issue (Debt reduction, capex, general corporate purposes).
  - Capital structure (pre- and post-issue equity shares, promoter dilution).
  - Restated audited financial statements (3 full fiscal years + stub period).
  - Key risk factors, ongoing material litigations, and contingent liabilities.
  - Related party transactions and promoter compensation.
- **Reliability:** Maximum (Legally Binding Corporate Filings).

### D. Audited Company Financial Information
- **Role:** Independent statutory auditor reports, balance sheets, P&L, cash flow statements.
- **Data Retrieved:**
  - Restated Revenue from Operations, EBITDA, PAT, EPS.
  - Balance sheet leverage (Gross Debt, Net Debt, Debt-to-Equity).
  - Return ratios (ROE, ROCE, Net Worth).
- **Reliability:** Maximum.

---

## 3. Secondary Sources (Informational & Cross-Validation)

Secondary sources provide derived metrics, peer comparisons, and contextual sector intelligence.

### A. Reputable Financial News & Data Portals
- **Sources:** Moneycontrol, Livemint, The Economic Times, Business Standard, Chittorgarh, Trendlyne, Screener.in.
- **Data Retrieved:**
  - Listed peer group financial multiples (Industry P/E, Median P/B, Market Cap).
  - Consensus industry growth rates and macro sector tailwinds.
  - Analyst consensus summaries and institutional brokerage subscription notes.
- **Reliability:** High, but subject to cross-verification against exchange filings.

---

## 4. Unofficial / Indicative Sources (Sentiment Only)

### A. Grey Market Premium (GMP)
- **Description:** Grey Market Premium (GMP) represents the unofficial, unregulated over-the-counter forward price at which IPO shares trade among market intermediaries before official stock exchange listing.
- **Indicative Indicators:**
  - **GMP (₹):** Premium over the upper price band.
  - **Kostak (₹):** Fixed amount paid for an IPO application regardless of allotment status.
  - **Subject to Sauda (₹):** Guaranteed profit paid to the applicant only upon confirmed allotment.
- **Crucial Governance Rules:**
  - **Never Official:** GMP is strictly an indicative, unofficial sentiment gauge. It is volatile, unregulated by SEBI or exchanges, and susceptible to artificial manipulation.
  - **Never Used for Fundamental Valuation:** GMP must never be used to establish intrinsic corporate value.
  - **Labeling Requirement:** Every mention of GMP in reports must explicitly state: *"Indicative unofficial market sentiment only; subject to high volatility and manipulation."*

---

## 5. Data Handling & Integrity Standards

1. **Source Citation:** Every qualitative claim and numerical table must cite its exact source (e.g., `Source: RHP dated DD-MM-YYYY, Page 142` or `Source: NSE Bidding Platform as of 17:00 IST`).
2. **Missing Data Protocol:** If a metric is not disclosed in the RHP or exchange filings, it must be labeled **`"Not available"`**. Never fabricate, interpolate without notation, or approximate figures.
3. **Currency & Unit Consistency:** Standardize all financial metrics in Indian Rupees (INR), stating explicit units (e.g., `₹ in Crores` or `₹ per share`).
