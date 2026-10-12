# Phase 4: Historical Backtesting Engine Specification

**Specification Version:** `1.0`  
**Target Architecture:** Phase 4 (Historical Backtesting Engine)  
**System Role:** Programmatically evaluate historical IPO recommendations and scenario classifications against actual market listing and post-listing returns.

---

## 1. Architectural & Scientific Principles

1. **Strict Temporal Partitioning:** Pre-listing research evaluations (`ipo_master`, `financials`, `valuation`, `subscription`, `scenarios`) are strictly frozen at the pre-listing boundary (`listing_status = 'Pre-Listing'`). Post-listing outcome data (`historical_performance`, `performance_events`) is temporally partitioned to eliminate look-ahead bias.
2. **Empirical Evaluation Metrics:**
   - **Win Rate (%):** Percentage of historical offerings generating positive listing day returns.
   - **Average Listing Return (%):** Mean percentage gain/loss from issue price on listing close.
   - **Precision & Recall (%):** Precision measures what percentage of IPOs tagged as `Supported` reached +40% target; Recall measures what percentage of all +40% market winners were correctly tagged.
3. **No Financial Return Guarantees:** Backtest reports quantify historical accuracy across past market cycles (bull, bear, volatile) without claiming guaranteed future returns.
