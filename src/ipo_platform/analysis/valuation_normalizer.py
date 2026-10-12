"""
Valuation Normalizer & Relative Benchmarking Engine.
Computes P/E, P/B, market cap, and relative valuation spreads against peer medians and sector averages.
"""

from typing import Any, Dict, List, Optional
from ..models.schema import MasterIPORecord
from ..engine.ratio_calculator import RatioCalculator


class ValuationNormalizer:
    """Computes valuation metrics and comparative spreads relative to listed peers."""

    @staticmethod
    def compute_peer_median_pe(peers: List[Any]) -> Optional[float]:
        """Calculates median P/E multiple across direct listed peers."""
        pe_values = [p.PE for p in peers if p.PE is not None and p.PE > 0]
        if not pe_values:
            return None
        sorted_pe = sorted(pe_values)
        n = len(sorted_pe)
        mid = n // 2
        if n % 2 == 1:
            return round(sorted_pe[mid], 2)
        else:
            return round((sorted_pe[mid - 1] + sorted_pe[mid]) / 2.0, 2)

    @classmethod
    def analyze_valuation(cls, record: MasterIPORecord) -> Dict[str, Any]:
        """Extracts and computes complete valuation analytics dataset."""
        ref_price = record.valuation_data.reference_price
        ref_eps = record.valuation_data.reference_eps
        ref_bv = record.valuation_data.reference_book_value_per_share

        issue_pe = RatioCalculator.calculate_pe(ref_price, ref_eps)
        issue_pb = RatioCalculator.calculate_pb(ref_price, ref_bv)

        peer_median_pe = cls.compute_peer_median_pe(record.peer_companies)

        valuation_spread_peers = None
        if issue_pe is not None and peer_median_pe is not None:
            valuation_spread_peers = RatioCalculator.calculate_valuation_spread(
                issue_pe, peer_median_pe
            )

        industry_pe_val = (
            record.valuation_data.industry_pe.value
            if record.valuation_data.industry_pe and isinstance(record.valuation_data.industry_pe.value, (int, float))
            else None
        )

        valuation_spread_industry = None
        if issue_pe is not None and industry_pe_val is not None:
            valuation_spread_industry = RatioCalculator.calculate_valuation_spread(
                issue_pe, float(industry_pe_val)
            )

        return {
            "reference_price": ref_price,
            "reference_eps": ref_eps,
            "reference_book_value_per_share": ref_bv,
            "issue_pe": issue_pe,
            "issue_pb": issue_pb,
            "peer_median_pe": peer_median_pe,
            "valuation_spread_vs_peers_percent": valuation_spread_peers,
            "industry_pe": industry_pe_val,
            "valuation_spread_vs_industry_percent": valuation_spread_industry,
            "valuation_method": record.valuation_data.valuation_method,
            "valuation_source": record.valuation_data.valuation_source,
        }
