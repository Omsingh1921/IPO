"""
Daily Briefing Service for Indian IPO Platform.
Aggregates active offerings, closing today, listing today, latest GMP quotes,
and subscription momentum into an executive morning Markdown intelligence report.
"""

import os
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Engine

from ipo_platform.engine.ratio_calculator import RatioCalculator
from ipo_platform.db.mappers import to_float_safe
from ipo_platform.db.repository import GMPRepository, IPOReadRepository
from ipo_platform.db.session import get_db_session
from ipo_platform.engine.scenario_evaluator import Scenario40PercentEvaluator
from ipo_platform.models.enums import IPOStatusEnum
from ipo_platform.models.schema import GMPData, MasterIPORecord
from ipo_platform.security.hardening import safe_write_file, validate_output_directory


class DailyBriefingService:
    """Application Service facade managing daily intelligence briefing generation."""

    def __init__(
        self,
        engine: Engine,
        reports_dir: str = "reports/daily",
        read_repo: type[IPOReadRepository] = IPOReadRepository,
        gmp_repo: type[GMPRepository] = GMPRepository,
        notification_service: Optional[Any] = None,
    ) -> None:
        """
        Initializes DailyBriefingService with dependency injection.

        Args:
            engine: SQLAlchemy Engine instance.
            reports_dir: Output directory path for generated reports.
            read_repo: IPOReadRepository class or instance.
            gmp_repo: GMPRepository class or instance.
            notification_service: Optional NotificationService instance.
        """
        self.engine = engine
        self.reports_dir = reports_dir
        self.read_repo = read_repo
        self.gmp_repo = gmp_repo
        self.notification_service = notification_service

    def generate_daily_briefing(self, target_date: Optional[str] = None, notify: bool = False, dry_run: bool = False) -> str:
        """
        Generates and saves the daily 9:00 AM IST executive briefing report.
        Optionally dispatches notifications if notify=True and notification_service is configured.

        Args:
            target_date: Target date ISO string (YYYY-MM-DD). Defaults to current date.
            notify: When True, dispatches briefing to notification_service.
            dry_run: When True, simulates notification dispatch.

        Returns:
            Generated Markdown report text content.
        """
        current_date_str = target_date or date.today().isoformat()
        os.makedirs(self.reports_dir, exist_ok=True)

        with get_db_session(self.engine) as session:
            all_records = self.read_repo.list_all(session, skip=0, limit=1000)

            # Categorize IPOs by date & status
            active_ipos: List[MasterIPORecord] = []
            closing_today: List[MasterIPORecord] = []
            listing_today: List[MasterIPORecord] = []

            for rec in all_records:
                st = rec.ipo_status.status
                open_d = rec.ipo_status.open_date
                close_d = rec.ipo_status.close_date
                list_d = rec.ipo_status.listing_date

                # Active IPO check
                if st in (IPOStatusEnum.UPCOMING, IPOStatusEnum.OPENING_TODAY, IPOStatusEnum.CURRENTLY_OPEN, IPOStatusEnum.CLOSING_TODAY):
                    active_ipos.append(rec)

                # Closing today check
                if close_d == current_date_str:
                    closing_today.append(rec)

                # Listing today check
                if list_d == current_date_str:
                    listing_today.append(rec)

            # Build Markdown Report
            exec_time = os.getenv("BRIEFING_EXECUTION_TIME", "12:01")
            report_lines: List[str] = []
            report_lines.append(f"# Daily IPO Intelligence Briefing — {current_date_str}")
            report_lines.append("")
            report_lines.append(f"**Generated Date:** {current_date_str} {exec_time}:00 IST")
            report_lines.append(f"**Total Active Offerings Tracked:** {len(active_ipos)}")
            report_lines.append(f"**Offerings Closing Today:** {len(closing_today)}")
            report_lines.append(f"**Offerings Listing Today:** {len(listing_today)}")
            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")

            # Section 1: Active Offerings & Valuation Summary
            report_lines.append("## 1. Active IPOs & Market Valuation Summary")
            report_lines.append("")
            if not active_ipos:
                report_lines.append("*No active IPO offerings currently open or upcoming.*")
                report_lines.append("")
            else:
                report_lines.append("| Company Name | Segment | Status | Issue Price | Issue P/E | 40% Target Hypothesis | Latest GMP |")
                report_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
                for rec in active_ipos:
                    cname = rec.ipo_entity.company_name
                    seg = rec.ipo_entity.segment.value if hasattr(rec.ipo_entity.segment, "value") else str(rec.ipo_entity.segment)
                    status_str = rec.ipo_status.status.value if hasattr(rec.ipo_status.status, "value") else str(rec.ipo_status.status)
                    iprice = f"₹{rec.issue_structure.price_band_high.value:.2f}" if rec.issue_structure.price_band_high.value != "Not available" else "N/A"

                    # Calculate P/E ratio
                    pe_val = to_float_safe(rec.valuation_data.issue_pe)
                    if pe_val is None:
                        ref_p = to_float_safe(rec.issue_structure.price_band_high)
                        pe_val = RatioCalculator.calculate_pe(ref_p, rec.valuation_data.reference_eps)
                    pe_str = f"{pe_val:.2f}x" if isinstance(pe_val, float) else "N/A"

                    # Evaluate 40% target scenario
                    scen = rec.scenario_40_percent
                    target_p = f"₹{scen.target_price:.2f}" if (scen and hasattr(scen, "target_price")) else "N/A"
                    scen_status = scen.scenario_status.value if (scen and hasattr(scen.scenario_status, "value")) else (str(scen.scenario_status) if scen else "N/A")

                    # Fetch latest GMP
                    gmp_quote = self.gmp_repo.get_latest_gmp(session, rec.ipo_entity.ipo_id)
                    gmp_str = f"₹{gmp_quote.gmp_value:.2f} ({gmp_quote.gmp_percentage:.1f}%)" if gmp_quote else "N/A"

                    report_lines.append(f"| **{cname}** | {seg} | {status_str} | {iprice} | {pe_str} | {target_p} ({scen_status}) | {gmp_str} |")
                report_lines.append("")

            # Section 2: Offerings Closing Today
            report_lines.append("## 2. Offerings Closing Today")
            report_lines.append("")
            if not closing_today:
                report_lines.append("*No IPO offerings scheduled to close today.*")
                report_lines.append("")
            else:
                for rec in closing_today:
                    report_lines.append(f"### {rec.ipo_entity.company_name} (`{rec.ipo_entity.ipo_id}`)")
                    report_lines.append(f"- **Close Date:** {rec.ipo_status.close_date}")
                    report_lines.append(f"- **Issue Price Band:** ₹{rec.issue_structure.price_band_low.value} - ₹{rec.issue_structure.price_band_high.value}")
                    # Subscription details
                    sub_data = rec.subscription_data
                    if sub_data:
                        sub_summary = ", ".join([f"{k}: {v.subscription_multiple:.2f}x" for k, v in sub_data.items() if v.subscription_multiple is not None])
                        report_lines.append(f"- **Subscription Multiples:** {sub_summary}")
                    else:
                        report_lines.append("- **Subscription Multiples:** Data pending exchange update.")
                    report_lines.append("")

            # Section 3: Offerings Listing Today
            report_lines.append("## 3. Offerings Listing Today")
            report_lines.append("")
            if not listing_today:
                report_lines.append("*No IPO listings scheduled for today's trading session.*")
                report_lines.append("")
            else:
                for rec in listing_today:
                    report_lines.append(f"### {rec.ipo_entity.company_name} (`{rec.ipo_entity.ticker_symbol}`)")
                    report_lines.append(f"- **Listing Date:** {rec.ipo_status.listing_date}")
                    report_lines.append(f"- **Issue Price:** ₹{rec.issue_structure.issue_price.value}")
                    report_lines.append("")

            # Section 4: Governance & Disclaimers
            report_lines.append("---")
            report_lines.append("### Regulatory Governance & Disclaimer")
            report_lines.append("1. **Research & Information Purpose Only:** This daily briefing is generated automatically for internal research and educational analysis. It does not constitute investment advice or a recommendation to buy/sell securities.")
            report_lines.append("2. **GMP Disclaimer:** Grey Market Premium (GMP) data represents indicative unofficial market sentiment from un-regulated intermediaries and is subject to extreme volatility and manipulation.")
            report_lines.append("3. **40% Target Hypothesis:** The +40% target price is a conditional mathematical scenario hypothesis based on valuation multiples and does not imply guaranteed returns.")

            report_content = "\n".join(report_lines)

            # Write report to disk using atomic and path-safe writer
            report_filename = f"briefing_{current_date_str}.md"
            file_path = os.path.join(self.reports_dir, report_filename)
            safe_write_file(
                target_path=file_path,
                content=report_content,
                base_dir=self.reports_dir,
                overwrite=True,
            )

            if notify and self.notification_service:
                self.notification_service.send_daily_briefing(
                    briefing_markdown=report_content,
                    target_date=current_date_str,
                    dry_run=dry_run,
                )

            return report_content
