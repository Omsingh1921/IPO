-- =============================================================================
-- DATABASE DDL: ipo_recommendation
-- SYSTEM: Indian IPO Research & Data Analysis Platform
-- COMPLIANCE: MySQL 8.0+ / InnoDB / utf8mb4
-- PHYSICAL ARCHITECTURE: 14 Normalized Tables, 14 PKs, 25 FKs, 61 Indexes
-- =============================================================================

CREATE DATABASE IF NOT EXISTS ipo_recommendation
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ipo_recommendation;

-- 1. Centralized Provenance Sources Registry
CREATE TABLE IF NOT EXISTS sources (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_id VARCHAR(64) NOT NULL UNIQUE,
    source_name VARCHAR(255) NOT NULL,
    source_url TEXT NULL,
    source_type ENUM(
        'NSE', 'BSE', 'SEBI', 'Official Offer Document', 'Company Filing',
        'Registrar', 'Financial Publication', 'GMP Source', 'Calculated', 'Other'
    ) NOT NULL,
    publication_date DATE NULL,
    retrieval_timestamp DATETIME NOT NULL,
    page_or_section VARCHAR(255) NULL,
    data_type ENUM('Reported', 'Calculated', 'Estimate', 'Not available') NOT NULL DEFAULT 'Reported',
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_source_type_date (source_type, publication_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Master IPO Entity
CREATE TABLE IF NOT EXISTS ipo_master (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    company_legal_name VARCHAR(255) NOT NULL,
    ticker_symbol VARCHAR(32) NULL,
    isin VARCHAR(12) NULL UNIQUE,
    segment ENUM('Mainboard', 'SME') NOT NULL,
    sector VARCHAR(128) NOT NULL,
    industry VARCHAR(128) NOT NULL,
    status ENUM(
        'Upcoming', 'Opening Today', 'Currently Open', 'Closing Today',
        'Closed', 'Listed', 'Withdrawn', 'Not Available'
    ) NOT NULL,
    research_date DATE NOT NULL,
    research_time TIME NOT NULL,
    data_cutoff DATETIME NOT NULL,
    open_date DATE NOT NULL,
    close_date DATE NOT NULL,
    listing_date DATE NULL,
    listing_status ENUM('Pre-Listing', 'Listed', 'Deferred') NOT NULL DEFAULT 'Pre-Listing',
    issue_size DECIMAL(14,2) NOT NULL,
    fresh_issue_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    ofs_amount DECIMAL(14,2) NOT NULL DEFAULT 0.00,
    fresh_issue_percentage DECIMAL(5,2) NULL,
    ofs_percentage DECIMAL(5,2) NULL,
    face_value DECIMAL(8,2) NOT NULL,
    price_band_low DECIMAL(10,2) NULL,
    price_band_high DECIMAL(10,2) NOT NULL,
    issue_price DECIMAL(10,2) NULL,
    lot_size INT UNSIGNED NOT NULL,
    minimum_investment DECIMAL(12,2) NOT NULL,
    employee_reservation DECIMAL(12,2) NULL,
    shareholder_reservation DECIMAL(12,2) NULL,
    other_reservation DECIMAL(12,2) NULL,
    source_id VARCHAR(64) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ipo_master_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_ipo_status_dates (status, open_date, close_date),
    INDEX idx_ipo_segment_sector (segment, sector),
    INDEX idx_ipo_listing_date (listing_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Objects of the Issue (Fresh Issue Proceeds Utilization)
CREATE TABLE IF NOT EXISTS ipo_objects_of_issue (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    purpose_type ENUM(
        'debt_repayment', 'capital_expenditure', 'working_capital',
        'acquisitions_or_MA', 'general_corporate_purposes', 'issue_expenses', 'other_use'
    ) NOT NULL,
    purpose_description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    percentage_of_fresh_issue DECIMAL(5,2) NULL,
    disclosure_status ENUM('Disclosed', 'Estimated', 'Not available') NOT NULL DEFAULT 'Disclosed',
    source_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_obj_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_obj_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_obj_ipo_purpose (ipo_id, purpose_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Financial Statements (Multi-Period Restated Statements)
CREATE TABLE IF NOT EXISTS financials (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    financial_period VARCHAR(32) NOT NULL,
    period_type ENUM('FY', 'Q1', 'Q2', 'Q3', 'Q4', 'LTM', 'Stub Period', 'Not available') NOT NULL,
    revenue DECIMAL(14,2) NULL,
    revenue_growth DECIMAL(8,2) NULL,
    EBITDA DECIMAL(14,2) NULL,
    EBITDA_margin DECIMAL(6,2) NULL,
    PAT DECIMAL(14,2) NULL,
    PAT_growth DECIMAL(8,2) NULL,
    EPS DECIMAL(10,2) NULL,
    book_value_per_share DECIMAL(10,2) NULL,
    ROE DECIMAL(6,2) NULL,
    ROCE DECIMAL(6,2) NULL,
    total_debt DECIMAL(14,2) NULL,
    net_debt DECIMAL(14,2) NULL,
    debt_equity DECIMAL(6,2) NULL,
    operating_cash_flow DECIMAL(14,2) NULL,
    investing_cash_flow DECIMAL(14,2) NULL,
    financing_cash_flow DECIMAL(14,2) NULL,
    free_cash_flow DECIMAL(14,2) NULL,
    data_type ENUM('Reported', 'Calculated', 'Estimate', 'Not available') NOT NULL DEFAULT 'Reported',
    source_id VARCHAR(64) NULL,
    source_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_fin_ipo_period (ipo_id, financial_period),
    CONSTRAINT fk_fin_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_fin_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_fin_period_type (ipo_id, period_type, financial_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Valuation Benchmarks
CREATE TABLE IF NOT EXISTS valuation (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    issue_price DECIMAL(10,2) NOT NULL,
    reference_eps DECIMAL(10,2) NULL,
    reference_book_value_per_share DECIMAL(10,2) NULL,
    issue_pe DECIMAL(8,2) NULL,
    issue_pb DECIMAL(8,2) NULL,
    industry_pe DECIMAL(8,2) NULL,
    industry_pb DECIMAL(8,2) NULL,
    peer_average_pe DECIMAL(8,2) NULL,
    peer_average_pb DECIMAL(8,2) NULL,
    valuation_method VARCHAR(255) NULL,
    valuation_source VARCHAR(255) NULL,
    valuation_date DATE NULL,
    data_type ENUM('Reported', 'Calculated', 'Estimate', 'Not available') NOT NULL DEFAULT 'Calculated',
    source_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_val_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_val_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_val_ipo (ipo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Subscription Order Book Snapshots
CREATE TABLE IF NOT EXISTS subscription (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    subscription_date DATE NOT NULL,
    subscription_day VARCHAR(16) NOT NULL,
    QIB_shares_offered BIGINT UNSIGNED NULL,
    QIB_shares_bid BIGINT UNSIGNED NULL,
    QIB_subscription_multiple DECIMAL(8,2) NULL,
    NII_total_shares_offered BIGINT UNSIGNED NULL,
    NII_total_shares_bid BIGINT UNSIGNED NULL,
    NII_total_subscription_multiple DECIMAL(8,2) NULL,
    sHNI_shares_offered BIGINT UNSIGNED NULL,
    sHNI_shares_bid BIGINT UNSIGNED NULL,
    sHNI_subscription_multiple DECIMAL(8,2) NULL,
    bHNI_shares_offered BIGINT UNSIGNED NULL,
    bHNI_shares_bid BIGINT UNSIGNED NULL,
    bHNI_subscription_multiple DECIMAL(8,2) NULL,
    retail_shares_offered BIGINT UNSIGNED NULL,
    retail_shares_bid BIGINT UNSIGNED NULL,
    retail_subscription_multiple DECIMAL(8,2) NULL,
    employee_subscription DECIMAL(8,2) NULL,
    shareholder_subscription DECIMAL(8,2) NULL,
    other_subscription DECIMAL(8,2) NULL,
    total_subscription DECIMAL(8,2) NOT NULL,
    source_id VARCHAR(64) NULL,
    source_date DATE NULL,
    retrieval_timestamp DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_sub_ipo_date_day (ipo_id, subscription_date, subscription_day),
    CONSTRAINT fk_sub_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_sub_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_sub_lookup (ipo_id, subscription_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Anchor Book Header
CREATE TABLE IF NOT EXISTS anchors (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    anchor_id VARCHAR(64) NOT NULL UNIQUE,
    ipo_id VARCHAR(64) NOT NULL,
    anchor_allocation DECIMAL(12,2) NOT NULL,
    anchor_price DECIMAL(10,2) NOT NULL,
    anchor_investor_count INT UNSIGNED NOT NULL,
    anchor_allocation_percentage DECIMAL(5,2) NULL,
    lock_in_30_day DATE NOT NULL,
    lock_in_90_day DATE NOT NULL,
    source_id VARCHAR(64) NULL,
    source_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_anc_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_anc_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_anc_ipo (ipo_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Anchor Investors Detailed Roster
CREATE TABLE IF NOT EXISTS anchor_investors (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    anchor_id VARCHAR(64) NOT NULL,
    investor_name VARCHAR(255) NOT NULL,
    investor_type ENUM('DII', 'FPI', 'Mutual Fund', 'Insurance', 'Other', 'Not available') NOT NULL DEFAULT 'Other',
    allocation_amount DECIMAL(12,2) NOT NULL,
    allocation_shares BIGINT UNSIGNED NOT NULL,
    allocation_percentage DECIMAL(5,2) NULL,
    anchor_price DECIMAL(10,2) NOT NULL,
    source_id VARCHAR(64) NULL,
    source_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_anc_inv_header FOREIGN KEY (anchor_id) REFERENCES anchors(anchor_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_anc_inv_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_anc_inv_name (investor_name),
    INDEX idx_anc_inv_type (investor_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Indicative Grey Market Premium (GMP) Logs
CREATE TABLE IF NOT EXISTS gmp (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    gmp_date DATE NOT NULL,
    gmp_time TIME NOT NULL,
    gmp_value DECIMAL(10,2) NOT NULL,
    gmp_percentage DECIMAL(6,2) NULL,
    reference_price DECIMAL(10,2) NOT NULL,
    implied_price DECIMAL(10,2) NOT NULL,
    source_id VARCHAR(64) NULL,
    source_type ENUM('Unofficial GMP') NOT NULL DEFAULT 'Unofficial GMP',
    retrieval_timestamp DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_gmp_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_gmp_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE KEY uq_gmp_timeline (ipo_id, gmp_date, gmp_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Listed Competitor Peers
CREATE TABLE IF NOT EXISTS peers (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    peer_company_name VARCHAR(255) NOT NULL,
    ticker VARCHAR(32) NOT NULL,
    market_cap DECIMAL(14,2) NULL,
    revenue DECIMAL(14,2) NULL,
    PAT DECIMAL(14,2) NULL,
    EPS DECIMAL(10,2) NULL,
    PE DECIMAL(8,2) NULL,
    PB DECIMAL(8,2) NULL,
    ROE DECIMAL(6,2) NULL,
    ROCE DECIMAL(6,2) NULL,
    debt_equity DECIMAL(6,2) NULL,
    source_id VARCHAR(64) NULL,
    source_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_peer_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_peer_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_peer_lookup (ipo_id, ticker)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Disclosed Risk Disclosures
CREATE TABLE IF NOT EXISTS risks (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    risk_type ENUM(
        'business', 'financial', 'debt', 'sector', 'regulatory',
        'valuation', 'customer_concentration', 'promoter', 'execution', 'market', 'other'
    ) NOT NULL,
    risk_description TEXT NOT NULL,
    severity ENUM('High', 'Medium', 'Low', 'Not available') NOT NULL DEFAULT 'Not available',
    source_id VARCHAR(64) NULL,
    source_date DATE NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_risk_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_risk_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_risk_lookup (ipo_id, risk_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Standardized 40% Upside Scenario Model
CREATE TABLE IF NOT EXISTS scenarios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL UNIQUE,
    reference_price DECIMAL(10,2) NOT NULL,
    target_price DECIMAL(10,2) NOT NULL,
    required_price_movement DECIMAL(5,2) NOT NULL DEFAULT 40.00,
    target_pe DECIMAL(8,2) NULL,
    target_pb DECIMAL(8,2) NULL,
    supporting_factors JSON NULL,
    contradictory_factors JSON NULL,
    scenario_status ENUM('Supported', 'Not supported', 'Insufficient evidence') NOT NULL,
    scenario_methodology TEXT NOT NULL,
    scenario_data_timestamp DATETIME NOT NULL,
    source_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_scen_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_scen_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_scen_status (ipo_id, scenario_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Historical Post-Listing Aggregates (Strictly Segregated Post-Listing Stream)
CREATE TABLE IF NOT EXISTS historical_performance (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    ipo_year SMALLINT UNSIGNED NOT NULL,
    listing_price DECIMAL(10,2) NOT NULL,
    listing_day_close DECIMAL(10,2) NOT NULL,
    listing_day_high DECIMAL(10,2) NULL,
    listing_day_low DECIMAL(10,2) NULL,
    listing_day_return DECIMAL(8,2) NOT NULL,
    post_listing_7d_return DECIMAL(8,2) NULL,
    post_listing_30d_return DECIMAL(8,2) NULL,
    post_listing_90d_return DECIMAL(8,2) NULL,
    post_listing_180d_return DECIMAL(8,2) NULL,
    post_listing_1y_return DECIMAL(8,2) NULL,
    max_upside_from_issue_price DECIMAL(8,2) NULL,
    max_drawdown_from_issue_price DECIMAL(8,2) NULL,
    source_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_hist_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_hist_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_hist_year_return (ipo_year, listing_day_return)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 14. Longitudinal Event Stream for Backtesting (Strictly Segregated Post-Listing Stream)
CREATE TABLE IF NOT EXISTS performance_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    ipo_id VARCHAR(64) NOT NULL,
    event_date DATE NOT NULL,
    event_type ENUM(
        'Listing', 'Day 1', 'Day 7', 'Day 30', 'Day 90', 'Day 180',
        '1 Year', 'Target Reached', 'Drawdown', 'Other'
    ) NOT NULL,
    reference_price DECIMAL(10,2) NOT NULL,
    market_price DECIMAL(10,2) NOT NULL,
    return_percentage DECIMAL(8,2) NOT NULL,
    days_from_listing INT UNSIGNED NOT NULL,
    reached_40_percent_target BOOLEAN NOT NULL DEFAULT FALSE,
    source_id VARCHAR(64) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_pevent_ipo FOREIGN KEY (ipo_id) REFERENCES ipo_master(ipo_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_pevent_source FOREIGN KEY (source_id) REFERENCES sources(source_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_pevent_lookup (ipo_id, event_type, days_from_listing),
    INDEX idx_pevent_date (event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
