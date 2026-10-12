"""
Notifications Module for Indian IPO Platform.
Exposes pluggable notifiers, multi-channel dispatcher, and notification service facade.
"""

from ipo_platform.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationMessage,
    NotificationResult,
    NotificationType,
)
from ipo_platform.notifications.dispatcher import (
    NotificationDispatcher,
    NotificationService,
)
from ipo_platform.notifications.email_notifier import EmailNotifier
from ipo_platform.notifications.slack_notifier import SlackNotifier
from ipo_platform.notifications.telegram_notifier import TelegramNotifier

__all__ = [
    "BaseNotifier",
    "NotificationChannel",
    "NotificationMessage",
    "NotificationResult",
    "NotificationType",
    "NotificationDispatcher",
    "NotificationService",
    "TelegramNotifier",
    "SlackNotifier",
    "EmailNotifier",
]
