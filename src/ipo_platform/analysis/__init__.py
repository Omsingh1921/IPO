"""
Phase 3 Python Data Analysis Engine.
Provides programmatic ingestion, growth analytics, valuation normalization, subscription momentum tracking, and normalized dataset generation.
"""

from .reader import IPODataReader
from .valuation_normalizer import ValuationNormalizer
from .growth_analytics import GrowthAnalytics
from .subscription_momentum import SubscriptionMomentumEngine
from .dataset_normalizer import DatasetNormalizer
from .rhp_parser import RHPProspectusParser

__all__ = [
    "IPODataReader",
    "ValuationNormalizer",
    "GrowthAnalytics",
    "SubscriptionMomentumEngine",
    "DatasetNormalizer",
    "RHPProspectusParser",
]
