"""
Daily Briefing Job Runner for Indian IPO Platform.
Executes the DailyBriefingService to generate morning intelligence briefings.
"""

import logging
from typing import Optional

from sqlalchemy import Engine

from ipo_platform.services.briefing_service import DailyBriefingService

logger = logging.getLogger(__name__)


def run_daily_briefing_job(
    engine: Engine,
    target_date: Optional[str] = None,
    reports_dir: str = "reports/daily",
    notify_channels: Optional[list] = None,
    dry_run: bool = False,
) -> str:
    """
    Executes the daily briefing job runner manually or via scheduler.

    Args:
        engine: SQLAlchemy Engine instance.
        target_date: Optional target date ISO string (YYYY-MM-DD).
        reports_dir: Output directory path for report files.
        notify_channels: Optional list of notification channels to dispatch report to.
        dry_run: When True, simulates notification delivery.

    Returns:
        Generated briefing Markdown report content.
    """
    logger.info("Executing daily briefing job runner...")
    service = DailyBriefingService(engine, reports_dir=reports_dir)
    report_content = service.generate_daily_briefing(target_date=target_date)
    logger.info("Daily briefing job executed successfully.")

    if notify_channels:
        from ipo_platform.notifications import NotificationService
        notif_service = NotificationService()
        effective_date = target_date or service.reports_dir
        notif_service.send_daily_briefing(
            briefing_markdown=report_content,
            target_date=target_date or "today",
            channels=notify_channels,
            dry_run=dry_run,
        )

    return report_content

