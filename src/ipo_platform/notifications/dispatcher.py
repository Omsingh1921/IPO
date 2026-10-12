"""
Notification Dispatcher and Application Service Facade for Indian IPO Platform.
Provides multi-channel dispatch aggregation, routing, and high-level notifications API.
"""

import logging
from typing import Dict, List, Optional, Union

from ipo_platform.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationMessage,
    NotificationResult,
    NotificationType,
)
from ipo_platform.notifications.email_notifier import EmailNotifier
from ipo_platform.notifications.slack_notifier import SlackNotifier
from ipo_platform.notifications.telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Orchestrates notification dispatch across registered channel notifiers."""

    def __init__(self, notifiers: Optional[List[BaseNotifier]] = None) -> None:
        """
        Initializes NotificationDispatcher with dependency injection.

        Args:
            notifiers: Optional initial list of BaseNotifier instances.
        """
        self._notifiers: Dict[NotificationChannel, BaseNotifier] = {}
        if notifiers:
            for n in notifiers:
                self.register_notifier(n)

    def register_notifier(self, notifier: BaseNotifier) -> None:
        """Registers or replaces a channel notifier."""
        self._notifiers[notifier.channel] = notifier
        logger.debug("Registered notifier for channel: %s", notifier.channel.value)

    def get_notifier(self, channel: Union[NotificationChannel, str]) -> Optional[BaseNotifier]:
        """Retrieves a registered notifier by channel enum or string."""
        key = NotificationChannel(channel) if isinstance(channel, str) else channel
        return self._notifiers.get(key)

    def get_registered_channels(self) -> List[NotificationChannel]:
        """Returns list of channels currently registered."""
        return list(self._notifiers.keys())

    def dispatch(
        self,
        message: NotificationMessage,
        channels: Optional[List[Union[NotificationChannel, str]]] = None,
        dry_run: bool = False,
    ) -> List[NotificationResult]:
        """
        Dispatches a message across specified channels or all configured channels.

        Args:
            message: Standardized NotificationMessage container.
            channels: Optional list of channels to target. If None, targets all configured.
            dry_run: When True, simulates delivery without making network requests.

        Returns:
            List of NotificationResult objects for each targeted channel.
        """
        target_notifiers: List[BaseNotifier] = []

        if channels:
            for ch in channels:
                enum_ch = NotificationChannel(ch) if isinstance(ch, str) else ch
                n = self._notifiers.get(enum_ch)
                if n:
                    target_notifiers.append(n)
                else:
                    logger.warning("Requested notification channel '%s' is not registered.", enum_ch.value)
        else:
            # Default: all registered and configured channels
            target_notifiers = [n for n in self._notifiers.values() if n.is_configured or dry_run]

        if not target_notifiers:
            logger.info("No active or configured notification channels found for dispatch.")
            return []

        results: List[NotificationResult] = []
        for notifier in target_notifiers:
            try:
                res = notifier.send(message, dry_run=dry_run)
                results.append(res)
            except Exception as err:
                logger.error("Unhandled exception in notifier '%s': %s", notifier.channel.value, err, exc_info=True)
                results.append(
                    NotificationResult(
                        channel=notifier.channel,
                        success=False,
                        message=f"Unhandled dispatch exception: {err}",
                    )
                )

        return results


class NotificationService:
    """
    Application Service facade providing high-level business notification workflows:
    - Daily briefing reports delivery
    - High-conviction IPO scenario alerts
    - Event deadline reminders
    """

    def __init__(self, dispatcher: Optional[NotificationDispatcher] = None) -> None:
        """
        Initializes NotificationService with dependency injection.
        Defaults to auto-discovering configured standard notifiers (Telegram, Slack, Email).
        """
        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            self.dispatcher = NotificationDispatcher([
                TelegramNotifier(),
                SlackNotifier(),
                EmailNotifier(),
            ])

    def send_daily_briefing(
        self,
        briefing_markdown: str,
        target_date: str,
        channels: Optional[List[Union[NotificationChannel, str]]] = None,
        dry_run: bool = False,
    ) -> List[NotificationResult]:
        """
        Dispatches daily morning intelligence briefing to configured channels.
        """
        title = f"IPO Platform: Daily Intelligence Briefing — {target_date}"
        message = NotificationMessage(
            title=title,
            body_markdown=briefing_markdown,
            notification_type=NotificationType.DAILY_BRIEFING,
            metadata={"target_date": target_date},
        )
        return self.dispatcher.dispatch(message, channels=channels, dry_run=dry_run)

    def send_high_conviction_alert(
        self,
        company_name: str,
        ipo_id: str,
        target_price: float,
        gmp_percentage: float,
        summary: str,
        channels: Optional[List[Union[NotificationChannel, str]]] = None,
        dry_run: bool = False,
    ) -> List[NotificationResult]:
        """
        Dispatches an urgent alert when a 40%+ upside scenario or surge momentum occurs.
        """
        title = f"🚨 High-Conviction IPO Alert: {company_name} ({ipo_id})"
        body = f"""**Company:** {company_name} (`{ipo_id}`)
**Target Scenario Price:** ₹{target_price:.2f}
**Latest GMP Surge:** {gmp_percentage:.1f}%

**Thesis Summary:**
{summary}

*Disclaimer: Strictly research scenario analytics. Not financial advice.*
"""
        message = NotificationMessage(
            title=title,
            body_markdown=body,
            notification_type=NotificationType.HIGH_CONVICTION_ALERT,
            metadata={"ipo_id": ipo_id, "target_price": target_price, "gmp": gmp_percentage},
        )
        return self.dispatcher.dispatch(message, channels=channels, dry_run=dry_run)
