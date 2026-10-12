"""
Base Notification Contracts and Data Models for Indian IPO Platform.
Defines notification messages, delivery outcomes, and abstract dispatcher interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class NotificationChannel(str, Enum):
    """Supported destination notification channels."""
    TELEGRAM = "telegram"
    SLACK = "slack"
    EMAIL = "email"


class NotificationType(str, Enum):
    """Categorization of notification triggers and contents."""
    DAILY_BRIEFING = "daily_briefing"
    HIGH_CONVICTION_ALERT = "high_conviction_alert"
    EVENT_REMINDER = "event_reminder"
    SYSTEM_ALERT = "system_alert"


@dataclass
class NotificationMessage:
    """Standardized notification envelope passed to notifiers."""
    title: str
    body_markdown: str
    notification_type: NotificationType = NotificationType.DAILY_BRIEFING
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NotificationResult:
    """Outcome report for an individual notifier channel dispatch."""
    channel: NotificationChannel
    success: bool
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = field(default_factory=dict)


class BaseNotifier(ABC):
    """Abstract base class that all notification channel adapters must implement."""

    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Returns the channel enum identifier for this notifier."""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if required credentials/endpoints are configured."""
        pass

    @abstractmethod
    def send(self, message: NotificationMessage, dry_run: bool = False) -> NotificationResult:
        """
        Sends the notification message via the specific channel.

        Args:
            message: Standardized NotificationMessage container.
            dry_run: When True, simulates delivery without making external network calls.

        Returns:
            NotificationResult describing success or failure.
        """
        pass
