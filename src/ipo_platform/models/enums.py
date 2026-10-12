"""
Enum definitions for Indian IPO Research & Data Analysis Platform.
Preserves existing schema contracts and strict allowed values per docs/ipo-data-schema.md.
"""

from enum import Enum


class SegmentEnum(str, Enum):
    MAINBOARD = "Mainboard"
    SME = "SME"


class IPOStatusEnum(str, Enum):
    UPCOMING = "Upcoming"
    OPENING_TODAY = "Opening Today"
    CURRENTLY_OPEN = "Currently Open"
    CLOSING_TODAY = "Closing Today"
    CLOSED = "Closed"
    LISTED = "Listed"
    WITHDRAWN = "Withdrawn"
    NOT_AVAILABLE = "Not Available"


class ListingStatusEnum(str, Enum):
    PRE_LISTING = "Pre-Listing"
    LISTED = "Listed"
    DEFERRED = "Deferred"


class PeriodTypeEnum(str, Enum):
    FY = "FY"
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    LTM = "LTM"
    STUB_PERIOD = "Stub Period"
    NOT_AVAILABLE = "Not available"


class DataTypeEnum(str, Enum):
    REPORTED = "Reported"
    CALCULATED = "Calculated"
    ESTIMATE = "Estimate"
    NOT_AVAILABLE = "Not available"


class SourceTypeEnum(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    SEBI = "SEBI"
    OFFICIAL_OFFER_DOCUMENT = "Official Offer Document"
    COMPANY_FILING = "Company Filing"
    REGISTRAR = "Registrar"
    FINANCIAL_PUBLICATION = "Financial Publication"
    UNOFFICIAL_GMP = "Unofficial GMP"
    CALCULATED = "Calculated"
    OTHER = "Other"


class ScenarioStatusEnum(str, Enum):
    SUPPORTED = "Supported"
    NOT_SUPPORTED = "Not supported"
    INSUFFICIENT_EVIDENCE = "Insufficient evidence"


class InvestorTypeEnum(str, Enum):
    DII = "DII"
    FPI = "FPI"
    MUTUAL_FUND = "Mutual Fund"
    INSURANCE = "Insurance"
    OTHER = "Other"
    NOT_AVAILABLE = "Not available"


class RiskCategoryEnum(str, Enum):
    BUSINESS_RISK = "business_risk"
    FINANCIAL_RISK = "financial_risk"
    DEBT_RISK = "debt_risk"
    SECTOR_RISK = "sector_risk"
    REGULATORY_RISK = "regulatory_risk"
    VALUATION_RISK = "valuation_risk"
    CUSTOMER_CONCENTRATION_RISK = "customer_concentration_risk"
    PROMOTER_RISK = "promoter_risk"
    EXECUTION_RISK = "execution_risk"
    MARKET_RISK = "market_risk"
    OTHER_RISK = "other_risk"


class RiskSeverityEnum(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    NOT_AVAILABLE = "Not available"


class PerformanceEventTypeEnum(str, Enum):
    LISTING = "Listing"
    DAY_1 = "Day 1"
    DAY_7 = "Day 7"
    DAY_30 = "Day 30"
    DAY_90 = "Day 90"
    DAY_180 = "Day 180"
    ONE_YEAR = "1 Year"
    TARGET_REACHED = "Target Reached"
    DRAWDOWN = "Drawdown"
    OTHER = "Other"


class ObjectsDisclosureStatusEnum(str, Enum):
    DISCLOSED = "Disclosed"
    ESTIMATED = "Estimated"
    NOT_AVAILABLE = "Not available"


class DataCompletenessEnum(str, Enum):
    COMPLETE = "Complete"
    PARTIAL = "Partial"
    INSUFFICIENT_EVIDENCE = "Insufficient evidence"


class SourceVerificationEnum(str, Enum):
    VERIFIED = "Verified"
    PARTIALLY_VERIFIED = "Partially verified"
    NOT_VERIFIED = "Not verified"
