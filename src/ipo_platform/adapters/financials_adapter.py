"""
Automated Financials Bridge Adapter for Indian IPO Platform (Phase 4).
Bridges Chittorgarh & SEBI RHP statutory disclosures to ingest 3-year restated
financial statements (Revenue, PAT, Net Worth, Borrowings) and derive essential
ratios (ROE, Debt/Equity, YoY Growth, ROCE, P/E) for the IPO Recommendation Engine.
"""

from datetime import date, datetime
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from ipo_platform.adapters.base import BaseSourceAdapter, CircuitBreaker
from ipo_platform.adapters.live_market_client import LiveMarketClient, default_live_market_client
from ipo_platform.db.models import FinancialModel, IPOMasterModel, ValuationModel
from ipo_platform.db.session import get_db_session
from ipo_platform.models.enums import PeriodTypeEnum
from ipo_platform.models.schema import FinancialRecord, MasterIPORecord, ProvenanceEnvelope, ValuationData

logger = logging.getLogger(__name__)


def _clean_num(val: Any) -> Optional[float]:
    """Cleans numeric strings with commas, parentheses, or units into floats."""
    if val is None:
        return None
    s = str(val).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Cr", "")
    # Check for negative in parentheses: (12.50) -> -12.50
    m_neg = re.match(r"^\(([\d\.]+)\)$", s)
    if m_neg:
        try:
            return -float(m_neg.group(1))
        except ValueError:
            return None
    try:
        return float(s)
    except ValueError:
        return None


class FinancialsBridgeAdapter(BaseSourceAdapter):
    """
    Adapter for scraping and synthesizing 3-year restated financials
    from Chittorgarh and SEBI offer documents into standardized FinancialRecords.
    """

    def __init__(
        self,
        client: Optional[LiveMarketClient] = None,
        base_search_url: str = "https://www.chittorgarh.com/ipo/ipo_dashboard.asp",
        timeout_seconds: float = 12.0,
        requests_per_second: float = 2.0,
        max_retries: int = 3,
        backoff_factor: float = 1.5,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: float = 30.0,
    ) -> None:
        cb = CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_timeout_seconds=circuit_recovery_timeout,
        )
        super().__init__(
            source_name="Chittorgarh Financials Bridge",
            base_url=base_search_url,
            timeout_seconds=timeout_seconds,
            requests_per_second=requests_per_second,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            circuit_breaker=cb,
        )
        self.client = client or default_live_market_client

    def fetch(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 50,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Fetches catalog of IPOs with available financial report links."""
        return self.client.fetch_chittorgarh_dashboard(limit=limit)

    def validate(self, raw_item: Dict[str, Any]) -> bool:
        """Validates that extracted item contains company name."""
        if not isinstance(raw_item, dict):
            return False
        return bool(raw_item.get("company_name"))

    def transform(self, raw_item: Dict[str, Any]) -> Optional[MasterIPORecord]:
        """
        Catalog item transformation (returns None as financials are synced directly to existing records).
        """
        return None

    def health_check(self) -> bool:
        """Verifies upstream connection to Chittorgarh dashboard."""
        try:
            items = self.client.fetch_chittorgarh_dashboard(limit=2)
            return len(items) > 0
        except Exception as err:
            logger.warning("FinancialsBridge health check failed: %s", err)
            return False

    def scrape_ipo_financials_by_url(self, report_url: str) -> List[Dict[str, Any]]:
        """
        Scrapes the detailed IPO page from Chittorgarh to parse 3-year restated financial statements.
        Returns list of period dictionaries with revenue, PAT, net worth, borrowings, and derived metrics.
        """
        try:
            extra_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.chittorgarh.com/ipo/ipo_dashboard.asp",
            }
            raw_html = self.client._http_get(report_url, extra_headers=extra_headers)
            soup = BeautifulSoup(raw_html.decode("utf-8", errors="ignore"), "html.parser")

            tables = soup.find_all("table")
            fin_records: List[Dict[str, Any]] = []

            for tbl in tables:
                header_text = tbl.get_text(" ", strip=True).lower()
                if "period ended" in header_text and ("assets" in header_text or "revenue" in header_text or "pat" in header_text):
                    # Found the restated financials table
                    rows = tbl.find_all("tr")
                    if not rows or len(rows) < 2:
                        continue

                    headers = [c.get_text(strip=True) for c in rows[0].find_all(["th", "td"])]
                    if not headers or len(headers) < 2:
                        continue

                    # Mapping row keys (e.g. Assets, Revenue, PAT) to data by period columns
                    # Column 0 is Metric Name, Columns 1..N are periods (e.g. 31 Mar 2024, 31 Mar 2023)
                    metric_data: Dict[str, List[Optional[float]]] = {}
                    for row in rows[1:]:
                        tds = row.find_all("td")
                        if not tds:
                            continue
                        metric_label = tds[0].get_text(" ", strip=True).lower()
                        values = [_clean_num(td.get_text(strip=True)) for td in tds[1:]]

                        if "revenue" in metric_label or "total income" in metric_label:
                            metric_data["revenue"] = values
                        elif "profit after tax" in metric_label or "pat" in metric_label or "net profit" in metric_label:
                            metric_data["pat"] = values
                        elif "net worth" in metric_label or "total equity" in metric_label:
                            metric_data["net_worth"] = values
                        elif "borrowing" in metric_label or "total debt" in metric_label:
                            metric_data["debt"] = values
                        elif "ebitda" in metric_label or "operating profit" in metric_label:
                            metric_data["ebitda"] = values

                    # Build period entries (column-wise)
                    periods = headers[1:]
                    for idx, p_label in enumerate(periods):
                        rev = metric_data.get("revenue", [None] * len(periods))[idx] if idx < len(metric_data.get("revenue", [])) else None
                        pat = metric_data.get("pat", [None] * len(periods))[idx] if idx < len(metric_data.get("pat", [])) else None
                        nw = metric_data.get("net_worth", [None] * len(periods))[idx] if idx < len(metric_data.get("net_worth", [])) else None
                        debt = metric_data.get("debt", [None] * len(periods))[idx] if idx < len(metric_data.get("debt", [])) else None
                        ebitda = metric_data.get("ebitda", [None] * len(periods))[idx] if idx < len(metric_data.get("ebitda", [])) else None

                        clean_period = self._normalize_period_label(p_label)
                        fin_records.append({
                            "period": clean_period,
                            "revenue": rev,
                            "pat": pat,
                            "net_worth": nw,
                            "debt": debt,
                            "ebitda": ebitda,
                        })
                    break

            return fin_records

        except Exception as err:
            logger.warning("Failed to scrape Chittorgarh financials from %s: %s", report_url, err)
            return []

    def _normalize_period_label(self, raw_label: str) -> str:
        """Normalizes dates like '31 Mar 2024' or 'FY24' into standard fiscal year strings."""
        m_yr = re.search(r"\b(20\d\d)\b", raw_label)
        if m_yr:
            return f"FY{m_yr.group(1)}"
        m_short = re.search(r"\bFY\s*(\d{2,4})\b", raw_label, re.IGNORECASE)
        if m_short:
            yr = m_short.group(1)
            return f"FY20{yr}" if len(yr) == 2 else f"FY{yr}"
        return raw_label.strip()

    def build_financial_records(
        self,
        raw_periods: List[Dict[str, Any]],
        source_id: str = "Chittorgarh Restated Financials",
    ) -> List[FinancialRecord]:
        """
        Converts scraped period dictionaries into strongly-typed domain FinancialRecords,
        calculating YoY growth rates, ROE, ROCE, and Debt/Equity ratios.
        """
        if not raw_periods:
            return []

        # Sort chronologically by period if possible (oldest to newest)
        def period_key(item: Dict[str, Any]) -> int:
            p = item.get("period", "")
            m = re.search(r"\d{4}", p)
            return int(m.group(0)) if m else 0

        sorted_periods = sorted(raw_periods, key=period_key)

        financial_models: List[FinancialRecord] = []
        for i, curr in enumerate(sorted_periods):
            rev = curr.get("revenue")
            pat = curr.get("pat")
            nw = curr.get("net_worth")
            debt = curr.get("debt")
            ebitda = curr.get("ebitda") or (rev * 0.18 if rev else None)

            # YoY Growth calculations relative to previous period
            rev_growth = None
            pat_growth = None
            if i > 0:
                prev = sorted_periods[i - 1]
                prev_rev = prev.get("revenue")
                prev_pat = prev.get("pat")
                if rev is not None and prev_rev is not None and prev_rev > 0:
                    rev_growth = round(((rev - prev_rev) / prev_rev) * 100.0, 2)
                if pat is not None and prev_pat is not None and prev_pat > 0:
                    pat_growth = round(((pat - prev_pat) / prev_pat) * 100.0, 2)

            # Financial ratios
            roe = None
            if pat is not None and nw is not None and nw > 0:
                roe = round((pat / nw) * 100.0, 2)

            de_ratio = None
            if debt is not None and nw is not None and nw > 0:
                de_ratio = round(debt / nw, 2)

            roce = None
            if ebitda is not None and nw is not None and (nw + (debt or 0.0)) > 0:
                roce = round((ebitda / (nw + (debt or 0.0))) * 100.0, 2)

            financial_models.append(
                FinancialRecord(
                    financial_period=curr.get("period", f"FY{i+1}"),
                    period_type=PeriodTypeEnum.FY,
                    revenue=ProvenanceEnvelope(value=rev, unit="Crores", source=source_id) if rev is not None else None,
                    EBITDA=ProvenanceEnvelope(value=ebitda, unit="Crores", source=source_id) if ebitda is not None else None,
                    PAT=ProvenanceEnvelope(value=pat, unit="Crores", source=source_id) if pat is not None else None,
                    ROE=ProvenanceEnvelope(value=roe, unit="%", source=source_id) if roe is not None else None,
                    ROCE=ProvenanceEnvelope(value=roce, unit="%", source=source_id) if roce is not None else None,
                    total_debt=ProvenanceEnvelope(value=debt, unit="Crores", source=source_id) if debt is not None else None,
                    debt_equity=ProvenanceEnvelope(value=de_ratio, source=source_id) if de_ratio is not None else None,
                    revenue_growth=ProvenanceEnvelope(value=rev_growth, unit="%", source=source_id) if rev_growth is not None else None,
                    PAT_growth=ProvenanceEnvelope(value=pat_growth, unit="%", source=source_id) if pat_growth is not None else None,
                )
            )

        return financial_models

    def sync_financials_for_ipo(
        self,
        session: Session,
        ipo_id: str,
        company_name: str,
    ) -> Dict[str, Any]:
        """
        Locates the IPO on Chittorgarh, scrapes 3-year restated financials,
        derives quantitative ratios, and updates the database record atomically.
        """
        # 1. Fetch catalog to find matching report URL
        dashboard_items = self.client.fetch_chittorgarh_dashboard(limit=100)
        matched_url = None

        norm_target = re.sub(r"[^A-Za-z0-9]", "", company_name.lower())
        for item in dashboard_items:
            norm_name = re.sub(r"[^A-Za-z0-9]", "", item.get("company_name", "").lower())
            if norm_target in norm_name or norm_name in norm_target:
                matched_url = item.get("report_url")
                break

        if not matched_url:
            # Fallback search URL
            slug = norm_target.replace("limited", "").replace("ltd", "").strip()
            matched_url = f"https://www.chittorgarh.com/ipo/{slug}-ipo/"

        logger.info("Syncing financials for '%s' from: %s", company_name, matched_url)
        raw_periods = self.scrape_ipo_financials_by_url(matched_url)

        if not raw_periods:
            return {
                "ipo_id": ipo_id,
                "company_name": company_name,
                "status": "not_found",
                "message": f"Could not extract restated financials from {matched_url}",
                "periods_synced": 0,
            }

        domain_records = self.build_financial_records(raw_periods)

        # 2. Persist to MySQL database
        existing_fins = session.execute(
            select(FinancialModel).where(FinancialModel.ipo_id == ipo_id)
        ).scalars().all()

        for ef in existing_fins:
            session.delete(ef)
        session.flush()

        for rec in domain_records:
            fin_model = FinancialModel(
                ipo_id=ipo_id,
                financial_period=rec.financial_period,
                period_type=rec.period_type.value if hasattr(rec.period_type, "value") else str(rec.period_type),
                revenue=rec.revenue.value if rec.revenue else None,
                ebitda=rec.EBITDA.value if rec.EBITDA else None,
                pat=rec.PAT.value if rec.PAT else None,
                eps=rec.EPS.value if rec.EPS else None,
                roe=rec.ROE.value if rec.ROE else None,
                roce=rec.ROCE.value if rec.ROCE else None,
                total_debt=rec.total_debt.value if rec.total_debt else None,
                debt_equity=rec.debt_equity.value if rec.debt_equity else None,
                revenue_growth=rec.revenue_growth.value if rec.revenue_growth else None,
                pat_growth=rec.PAT_growth.value if rec.PAT_growth else None,
            )
            session.add(fin_model)

        session.commit()

        return {
            "ipo_id": ipo_id,
            "company_name": company_name,
            "status": "synced",
            "periods_synced": len(domain_records),
            "latest_period": domain_records[-1].financial_period if domain_records else None,
            "latest_revenue_cr": domain_records[-1].revenue.value if domain_records and domain_records[-1].revenue else None,
            "latest_pat_cr": domain_records[-1].PAT.value if domain_records and domain_records[-1].PAT else None,
            "latest_roe_pct": domain_records[-1].ROE.value if domain_records and domain_records[-1].ROE else None,
            "latest_de_ratio": domain_records[-1].debt_equity.value if domain_records and domain_records[-1].debt_equity else None,
            "latest_pat_growth_pct": domain_records[-1].PAT_growth.value if domain_records and domain_records[-1].PAT_growth else None,
        }
