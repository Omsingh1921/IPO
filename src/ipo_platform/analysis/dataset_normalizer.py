"""
Dataset Normalizer Module for Phase 3 Analysis Engine.
Aggregates valuation, growth, subscription momentum, and scenario metrics into normalized datasets.
Exports outputs to data/processed/.
"""

import os
import json
from typing import Any, Dict
from ..models.schema import MasterIPORecord
from .reader import IPODataReader
from .valuation_normalizer import ValuationNormalizer
from .growth_analytics import GrowthAnalytics
from .subscription_momentum import SubscriptionMomentumEngine


class DatasetNormalizer:
    """Combines raw IPO research records with computed analytics into normalized datasets."""

    @classmethod
    def generate_normalized_dataset(cls, record: MasterIPORecord) -> Dict[str, Any]:
        """Generates a complete normalized analytical dataset from a MasterIPORecord.

        Leaves original input record untouched and immutable.
        """
        # Ensure input immutability
        reader = IPODataReader(record)
        raw_rec = reader.raw_record

        # 1. Financial Growth Analytics
        growth_metrics = GrowthAnalytics.analyze_financials(raw_rec)

        # 2. Valuation Normalization & Benchmarking
        valuation_metrics = ValuationNormalizer.analyze_valuation(raw_rec)

        # 3. Subscription Momentum Analytics
        subscription_metrics = SubscriptionMomentumEngine.analyze_subscription(raw_rec)

        # 4. Construct Normalized Master Output
        normalized_dataset = {
            "schema_version": "1.0",
            "ipo_id": raw_rec.ipo_entity.ipo_id,
            "company_name": raw_rec.ipo_entity.company_name,
            "segment": raw_rec.ipo_entity.segment.value,
            "status": raw_rec.ipo_status.status.value,
            "issue_parameters": {
                "issue_size_cr": raw_rec.issue_structure.issue_size.value,
                "fresh_issue_cr": raw_rec.issue_structure.fresh_issue_amount.value,
                "ofs_amount_cr": raw_rec.issue_structure.ofs_amount.value,
                "price_band_low": raw_rec.issue_structure.price_band_low.value,
                "price_band_high": raw_rec.issue_structure.price_band_high.value,
                "lot_size": raw_rec.issue_structure.lot_size.value,
                "minimum_investment": raw_rec.issue_structure.minimum_investment.value,
            },
            "growth_analytics": growth_metrics,
            "valuation_analytics": valuation_metrics,
            "subscription_momentum": subscription_metrics,
            "scenario_40_percent": {
                "reference_price": raw_rec.scenario_40_percent.reference_price,
                "target_price_40": raw_rec.scenario_40_percent.target_price,
                "required_move": raw_rec.scenario_40_percent.required_price_movement,
                "target_pe": raw_rec.scenario_40_percent.target_pe,
                "scenario_status": raw_rec.scenario_40_percent.scenario_status.value,
            },
            "data_quality": {
                "completeness_status": raw_rec.data_quality.completeness_status.value,
                "source_verification_status": raw_rec.data_quality.source_verification_status.value,
                "last_verified": raw_rec.data_quality.last_verified,
            },
        }

        return normalized_dataset

    @classmethod
    def save_normalized_dataset(
        cls, record: MasterIPORecord, output_dir: str = "data/processed"
    ) -> str:
        """Generates and writes a normalized JSON dataset file to the target output directory."""
        dataset = cls.generate_normalized_dataset(record)
        ipo_id = dataset["ipo_id"]
        filename = f"{ipo_id}_normalized.json"

        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        return filepath
