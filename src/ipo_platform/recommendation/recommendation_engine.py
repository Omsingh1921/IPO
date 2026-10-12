"""
Recommendation Intelligence Engine for Indian IPO Platform.
Orchestrates quantitative factor scoring, data provenance ingestion,
confidence score weighting, risk classification, and deterministic rationale synthesis.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from ipo_platform.models.schema import GMPData, MasterIPORecord
from ipo_platform.recommendation.recommendation_result import RecommendationResult
from ipo_platform.recommendation.scoring_models import (
    FactorScore,
    FactorWeights,
    RecommendationCategory,
    RiskLevel,
    score_debt_ratio,
    score_gmp,
    score_nii_subscription,
    score_pat_growth,
    score_pe_valuation,
    score_qib_subscription,
    score_retail_subscription,
    score_revenue_growth,
    score_roe,
)

logger = logging.getLogger(__name__)


class IPORecommendationEngine:
    """
    Quantitative Recommendation Intelligence Engine.
    Evaluates IPO investment opportunities across 9 key financial & market factors:
    1. GMP (Grey Market Premium)
    2. Retail Subscription
    3. QIB Subscription
    4. NII Subscription
    5. Revenue Growth
    6. PAT Growth
    7. ROE (Return on Equity)
    8. Debt-to-Equity Ratio
    9. PE Valuation
    """

    def __init__(
        self,
        weights: Optional[FactorWeights] = None,
        strong_subscribe_threshold: float = 75.0,
        subscribe_threshold: float = 60.0,
        neutral_threshold: float = 45.0,
    ) -> None:
        self.weights = weights or FactorWeights()
        self.weights.validate()
        self.strong_subscribe_threshold = strong_subscribe_threshold
        self.subscribe_threshold = subscribe_threshold
        self.neutral_threshold = neutral_threshold

    def evaluate(
        self,
        record: MasterIPORecord,
        gmp_override: Optional[GMPData] = None,
    ) -> RecommendationResult:
        """
        Executes full quantitative evaluation of a single MasterIPORecord.
        Extracts 9 factors, computes individual and composite scores,
        determines confidence score based on data completeness,
        identifies critical risks, and assigns a final recommendation category.
        """
        ipo_id = "UNKNOWN"
        company_name = "Unknown"
        if hasattr(record, "ipo_entity") and record.ipo_entity:
            ipo_id = getattr(record.ipo_entity, "ipo_id", "UNKNOWN")
            company_name = getattr(record.ipo_entity, "company_name", "Unknown")
        elif hasattr(record, "basic_info") and record.basic_info:
            ipo_id = getattr(record, "ipo_id", "UNKNOWN")
            company_name = getattr(record.basic_info, "company_name", "Unknown")
        elif hasattr(record, "ipo_id"):
            ipo_id = getattr(record, "ipo_id", "UNKNOWN")

        # 1. Factor Extraction
        factors_data = self._extract_factors(record, gmp_override)

        # 2. Factor Scoring
        factor_scores, composite_score = self._compute_factor_scores(factors_data)

        # 3. Confidence Score Assessment
        confidence_score = self._compute_confidence_score(factors_data, record)

        # 4. Veto Rules & Risk Analysis
        veto_applied, strengths, risks = self._analyze_veto_and_qualitative_signals(
            factors_data, factor_scores
        )

        # 5. Determine Final Recommendation Category
        if veto_applied:
            recommendation = RecommendationCategory.AVOID
        else:
            recommendation = self._map_score_to_category(composite_score)

        # 6. Determine Risk Level
        risk_level = self._compute_risk_level(composite_score, factors_data, veto_applied)

        # 7. Synthesize Summary Rationale
        summary_rationale = self._synthesize_rationale(
            company_name=company_name,
            recommendation=recommendation,
            composite_score=composite_score,
            confidence_score=confidence_score,
            risk_level=risk_level,
            strengths=strengths,
            risks=risks,
            veto_applied=veto_applied,
        )

        return RecommendationResult(
            ipo_id=ipo_id,
            company_name=company_name,
            recommendation=recommendation,
            composite_score=round(composite_score, 2),
            confidence_score=round(confidence_score, 2),
            risk_level=risk_level,
            factor_scores=factor_scores,
            strengths=strengths,
            risks=risks,
            veto_applied=veto_applied,
            summary_rationale=summary_rationale,
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def evaluate_batch(
        self,
        records: List[MasterIPORecord],
    ) -> List[RecommendationResult]:
        """Evaluates multiple MasterIPORecords sequentially."""
        return [self.evaluate(rec) for rec in records]

    def _extract_factors(
        self,
        record: MasterIPORecord,
        gmp_override: Optional[GMPData] = None,
    ) -> Dict[str, Any]:
        """Extracts 9 fundamental and market factors from domain models safely."""
        factors: Dict[str, Any] = {
            "gmp": None,
            "qib_subscription": None,
            "nii_subscription": None,
            "retail_subscription": None,
            "revenue_growth": None,
            "pat_growth": None,
            "roe": None,
            "debt_ratio": None,
            "issue_pe": None,
            "benchmark_pe": None,
        }

        # 1. GMP Factor
        gmp_source = gmp_override or getattr(record, "gmp_data", None)
        if gmp_source:
            if getattr(gmp_source, "gmp_percentage", None) is not None:
                factors["gmp"] = self._safe_float(gmp_source.gmp_percentage)
            elif getattr(gmp_source, "gmp_value", None) is not None:
                issue_price = None
                if hasattr(record, "issue_structure") and record.issue_structure:
                    raw_ip = record.issue_structure.issue_price
                    issue_price = self._safe_float(getattr(raw_ip, "value", raw_ip))
                elif hasattr(record, "issue_details") and record.issue_details:
                    raw_ip = record.issue_details.issue_price
                    issue_price = self._safe_float(getattr(raw_ip, "value", raw_ip))

                if issue_price and issue_price > 0:
                    factors["gmp"] = (self._safe_float(gmp_source.gmp_value) / issue_price) * 100.0

        # 2-4. Subscriptions
        if record.subscription_data:
            qib_sub = record.subscription_data.get("QIB")
            if qib_sub:
                factors["qib_subscription"] = self._safe_float(qib_sub.subscription_multiple)

            nii_sub = record.subscription_data.get("NII")
            if nii_sub:
                factors["nii_subscription"] = self._safe_float(nii_sub.subscription_multiple)

            retail_sub = record.subscription_data.get("Retail")
            if retail_sub:
                factors["retail_subscription"] = self._safe_float(retail_sub.subscription_multiple)

        # 5-8. Financial Ratios (from latest available financial record)
        if record.financial_data and len(record.financial_data) > 0:
            latest_fin = record.financial_data[-1]

            if latest_fin.revenue_growth and latest_fin.revenue_growth.value is not None:
                factors["revenue_growth"] = self._safe_float(latest_fin.revenue_growth.value)

            if latest_fin.PAT_growth and latest_fin.PAT_growth.value is not None:
                factors["pat_growth"] = self._safe_float(latest_fin.PAT_growth.value)

            if latest_fin.ROE and latest_fin.ROE.value is not None:
                factors["roe"] = self._safe_float(latest_fin.ROE.value)

            if latest_fin.debt_equity and latest_fin.debt_equity.value is not None:
                factors["debt_ratio"] = self._safe_float(latest_fin.debt_equity.value)

        # 9. Valuation (P/E & Benchmark)
        if record.valuation_data:
            if record.valuation_data.issue_pe and record.valuation_data.issue_pe.value is not None:
                factors["issue_pe"] = self._safe_float(record.valuation_data.issue_pe.value)

            if (
                record.valuation_data.peer_average_pe
                and record.valuation_data.peer_average_pe.value is not None
            ):
                factors["benchmark_pe"] = self._safe_float(
                    record.valuation_data.peer_average_pe.value
                )
            elif (
                record.valuation_data.industry_pe
                and record.valuation_data.industry_pe.value is not None
            ):
                factors["benchmark_pe"] = self._safe_float(record.valuation_data.industry_pe.value)

        # Peer companies benchmark fallback
        if factors["benchmark_pe"] is None and getattr(record, "peer_companies", None):
            peer_pes = [
                self._safe_float(p.PE)
                for p in record.peer_companies
                if getattr(p, "PE", None) is not None
            ]
            valid_pes = [p for p in peer_pes if p is not None and p > 0]
            if valid_pes:
                factors["benchmark_pe"] = sum(valid_pes) / len(valid_pes)

        return factors

    def _compute_factor_scores(
        self,
        factors: Dict[str, Any],
    ) -> Tuple[Dict[str, FactorScore], float]:
        """Calculates normalized and weighted scores for each factor and computes composite score."""
        scores: Dict[str, FactorScore] = {}

        # GMP
        gmp_val = factors.get("gmp")
        gmp_norm = score_gmp(gmp_val)
        scores["gmp"] = FactorScore(
            name="GMP (Grey Market Premium)",
            raw_value=gmp_val,
            normalized_score=gmp_norm,
            weight=self.weights.gmp,
            weighted_score=gmp_norm * self.weights.gmp,
            description=f"GMP: {f'{gmp_val:.1f}%' if gmp_val is not None else 'N/A'}",
            is_available=gmp_val is not None,
        )

        # QIB
        qib_val = factors.get("qib_subscription")
        qib_norm = score_qib_subscription(qib_val)
        scores["qib_subscription"] = FactorScore(
            name="QIB Subscription",
            raw_value=qib_val,
            normalized_score=qib_norm,
            weight=self.weights.qib_subscription,
            weighted_score=qib_norm * self.weights.qib_subscription,
            description=f"QIB Demand: {f'{qib_val:.2f}x' if qib_val is not None else 'N/A'}",
            is_available=qib_val is not None,
        )

        # NII
        nii_val = factors.get("nii_subscription")
        nii_norm = score_nii_subscription(nii_val)
        scores["nii_subscription"] = FactorScore(
            name="NII Subscription",
            raw_value=nii_val,
            normalized_score=nii_norm,
            weight=self.weights.nii_subscription,
            weighted_score=nii_norm * self.weights.nii_subscription,
            description=f"NII Demand: {f'{nii_val:.2f}x' if nii_val is not None else 'N/A'}",
            is_available=nii_val is not None,
        )

        # Retail
        retail_val = factors.get("retail_subscription")
        retail_norm = score_retail_subscription(retail_val)
        scores["retail_subscription"] = FactorScore(
            name="Retail Subscription",
            raw_value=retail_val,
            normalized_score=retail_norm,
            weight=self.weights.retail_subscription,
            weighted_score=retail_norm * self.weights.retail_subscription,
            description=f"Retail Demand: {f'{retail_val:.2f}x' if retail_val is not None else 'N/A'}",
            is_available=retail_val is not None,
        )

        # Revenue Growth
        rev_val = factors.get("revenue_growth")
        rev_norm = score_revenue_growth(rev_val)
        scores["revenue_growth"] = FactorScore(
            name="Revenue Growth",
            raw_value=rev_val,
            normalized_score=rev_norm,
            weight=self.weights.revenue_growth,
            weighted_score=rev_norm * self.weights.revenue_growth,
            description=f"Rev Growth: {f'{rev_val:.1f}%' if rev_val is not None else 'N/A'}",
            is_available=rev_val is not None,
        )

        # PAT Growth
        pat_val = factors.get("pat_growth")
        pat_norm = score_pat_growth(pat_val)
        scores["pat_growth"] = FactorScore(
            name="PAT Growth",
            raw_value=pat_val,
            normalized_score=pat_norm,
            weight=self.weights.pat_growth,
            weighted_score=pat_norm * self.weights.pat_growth,
            description=f"PAT Growth: {f'{pat_val:.1f}%' if pat_val is not None else 'N/A'}",
            is_available=pat_val is not None,
        )

        # ROE
        roe_val = factors.get("roe")
        roe_norm = score_roe(roe_val)
        scores["roe"] = FactorScore(
            name="Return on Equity (ROE)",
            raw_value=roe_val,
            normalized_score=roe_norm,
            weight=self.weights.roe,
            weighted_score=roe_norm * self.weights.roe,
            description=f"ROE: {f'{roe_val:.1f}%' if roe_val is not None else 'N/A'}",
            is_available=roe_val is not None,
        )

        # Debt Ratio
        debt_val = factors.get("debt_ratio")
        debt_norm = score_debt_ratio(debt_val)
        scores["debt_ratio"] = FactorScore(
            name="Debt-to-Equity Ratio",
            raw_value=debt_val,
            normalized_score=debt_norm,
            weight=self.weights.debt_ratio,
            weighted_score=debt_norm * self.weights.debt_ratio,
            description=f"D/E Ratio: {f'{debt_val:.2f}' if debt_val is not None else 'N/A'}",
            is_available=debt_val is not None,
        )

        # PE Valuation
        pe_val = factors.get("issue_pe")
        bench_val = factors.get("benchmark_pe")
        pe_norm = score_pe_valuation(pe_val, bench_val)
        scores["pe_valuation"] = FactorScore(
            name="P/E Valuation Multiple",
            raw_value=pe_val,
            normalized_score=pe_norm,
            weight=self.weights.pe_valuation,
            weighted_score=pe_norm * self.weights.pe_valuation,
            description=f"P/E: {f'{pe_val:.1f}x' if pe_val is not None else 'N/A'} (Benchmark: {f'{bench_val:.1f}x' if bench_val is not None else 'N/A'})",
            is_available=pe_val is not None,
        )

        composite_score = sum(fs.weighted_score for fs in scores.values())
        return scores, composite_score

    def _compute_confidence_score(
        self,
        factors: Dict[str, Any],
        record: MasterIPORecord,
    ) -> float:
        """
        Assesses confidence score (0.0 to 1.0) based on data availability and data quality flags.
        """
        core_factors = [
            factors.get("gmp"),
            factors.get("qib_subscription"),
            factors.get("retail_subscription"),
            factors.get("revenue_growth"),
            factors.get("pat_growth"),
            factors.get("roe"),
            factors.get("debt_ratio"),
            factors.get("issue_pe"),
        ]
        available_count = sum(1 for f in core_factors if f is not None)
        base_confidence = available_count / len(core_factors)

        # Data quality provenance bonus/penalty
        if record.data_quality and record.data_quality.completeness_status:
            status_val = (
                record.data_quality.completeness_status.value
                if hasattr(record.data_quality.completeness_status, "value")
                else str(record.data_quality.completeness_status)
            )
            if status_val.lower() == "complete":
                base_confidence = min(1.0, base_confidence * 1.1)
            elif status_val.lower() == "partial":
                base_confidence = base_confidence * 0.95
            elif "insufficient" in status_val.lower() or status_val.lower() == "poor":
                base_confidence = base_confidence * 0.70

        return max(0.1, min(1.0, base_confidence))

    def _analyze_veto_and_qualitative_signals(
        self,
        factors: Dict[str, Any],
        scores: Dict[str, FactorScore],
    ) -> Tuple[Optional[str], List[str], List[str]]:
        """
        Detects catastrophic deal-breakers (vetoes) and generates strengths and risk factors.
        """
        strengths: List[str] = []
        risks: List[str] = []
        veto: Optional[str] = None

        gmp = factors.get("gmp")
        qib = factors.get("qib_subscription")
        debt = factors.get("debt_ratio")
        pat_growth = factors.get("pat_growth")
        roe = factors.get("roe")
        pe = factors.get("issue_pe")

        # 1. Veto checks
        # Veto 1: Discount GMP (< 0%) and institutional rejection (QIB < 1.0x)
        if gmp is not None and gmp < 0.0 and qib is not None and qib < 1.0:
            veto = "Negative GMP accompanied by QIB institutional undersubscription (< 1.0x)"

        # Veto 2: Toxic leverage (> 3.5x D/E) combined with contracting profitability (PAT Growth < 0%)
        elif debt is not None and debt > 3.5 and pat_growth is not None and pat_growth < 0.0:
            veto = f"Excessive debt-to-equity ({debt:.2f}x) combined with negative PAT growth ({pat_growth:.1f}%)"

        # 2. Strengths
        if gmp is not None and gmp >= 25.0:
            strengths.append(f"Strong grey market premium of {gmp:.1f}% indicates positive listing expectation.")
        if qib is not None and qib >= 10.0:
            strengths.append(f"Institutional QIB subscription of {qib:.2f}x reflects strong smart-money backing.")
        if scores["revenue_growth"].normalized_score >= 80.0:
            strengths.append("Robust revenue expansion (> 20% YoY) demonstrating core business momentum.")
        if roe is not None and roe >= 18.0:
            strengths.append(f"High Return on Equity ({roe:.1f}%) showcasing capital efficiency.")
        if debt is not None and debt <= 0.3:
            strengths.append(f"Conservative balance sheet with low leverage (D/E: {debt:.2f}x).")
        if scores["pe_valuation"].normalized_score >= 80.0:
            strengths.append("Attractive valuation multiple compared to industry peers.")

        # 3. Risks
        if gmp is not None and gmp < 5.0:
            risks.append(f"Subdued or negative GMP ({gmp:.1f}%) creates listing loss risk.")
        if qib is not None and qib < 2.0:
            risks.append(f"Muted QIB institutional interest ({qib:.2f}x) signals cautious institutional reception.")
        if debt is not None and debt > 1.8:
            risks.append(f"Elevated debt-to-equity ratio ({debt:.2f}x) elevates balance sheet vulnerability.")
        if pat_growth is not None and pat_growth < 0.0:
            risks.append(f"Contracting profit after tax ({pat_growth:.1f}% YoY) indicates margin pressure.")
        if scores["pe_valuation"].normalized_score <= 30.0:
            risks.append(f"Aggressive valuation pricing (P/E {pe:.1f}x) leaves little margin of safety.")

        return veto, strengths, risks

    def _map_score_to_category(self, score: float) -> RecommendationCategory:
        """Maps composite normalized score (0–100) to recommendation category."""
        if score >= self.strong_subscribe_threshold:
            return RecommendationCategory.STRONG_SUBSCRIBE
        elif score >= self.subscribe_threshold:
            return RecommendationCategory.SUBSCRIBE
        elif score >= self.neutral_threshold:
            return RecommendationCategory.NEUTRAL
        else:
            return RecommendationCategory.AVOID

    def _compute_risk_level(
        self,
        score: float,
        factors: Dict[str, Any],
        veto_applied: Optional[str],
    ) -> RiskLevel:
        """Determines overall investment risk level."""
        if veto_applied or score < 40.0:
            return RiskLevel.VERY_HIGH

        debt = factors.get("debt_ratio")
        gmp = factors.get("gmp")

        if (debt is not None and debt > 2.0) or (gmp is not None and gmp < 0.0):
            return RiskLevel.HIGH

        if score >= 75.0:
            return RiskLevel.LOW
        elif score >= 60.0:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    def _synthesize_rationale(
        self,
        company_name: str,
        recommendation: RecommendationCategory,
        composite_score: float,
        confidence_score: float,
        risk_level: RiskLevel,
        strengths: List[str],
        risks: List[str],
        veto_applied: Optional[str],
    ) -> str:
        """Generates clear, diagnostic human-readable investment rationale."""
        lines = [
            f"**Recommendation**: {recommendation.value} (Composite Score: {composite_score:.1f}/100, Confidence: {confidence_score * 100:.0f}%, Risk: {risk_level.value})"
        ]

        if veto_applied:
            lines.append(f"CRITICAL RED FLAG VETO: {veto_applied}")

        if strengths:
            lines.append("Key Strengths: " + " ".join(strengths[:3]))
        if risks:
            lines.append("Key Risks: " + " ".join(risks[:3]))

        return "\n".join(lines)

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        """Safely parses float from numeric types or strings."""
        if val is None:
            return None
        try:
            parsed = float(val)
            return None if parsed != parsed else parsed  # Check for NaN
        except (ValueError, TypeError):
            return None
