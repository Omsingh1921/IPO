"""
Telegram Channel Notifier for Indian IPO Platform.
Dispatches formatted notifications to Telegram chats/channels via Bot API.
"""

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Optional

from ipo_platform.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationMessage,
    NotificationResult,
)

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Notifier implementation for Telegram Bot API."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> None:
        """
        Initializes TelegramNotifier with injected or environment credentials.

        Args:
            bot_token: Telegram Bot Token (defaults to TELEGRAM_BOT_TOKEN env var).
            chat_id: Target Chat/Channel ID (defaults to TELEGRAM_CHAT_ID env var).
        """
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.TELEGRAM

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, message: NotificationMessage, dry_run: bool = False) -> NotificationResult:
        """
        Sends formatted message to configured Telegram chat.
        """
        if not self.is_configured:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="TelegramNotifier is not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID).",
            )

        # Truncate or chunk if exceeding Telegram 4096 character limit
        full_text = f"*{message.title}*\n\n{message.body_markdown}"
        if len(full_text) > 4000:
            full_text = full_text[:3990] + "\n\n...(truncated)"

        if dry_run:
            logger.info("[DRY-RUN] Telegram notification simulated: %s", message.title)
            return NotificationResult(
                channel=self.channel,
                success=True,
                message="[DRY-RUN] Telegram notification simulated successfully.",
                details={"chat_id": self.chat_id, "text_length": len(full_text)},
            )

        api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": full_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.getcode()
                response_body = resp.read().decode("utf-8")
                return NotificationResult(
                    channel=self.channel,
                    success=status_code == 200,
                    message="Telegram message dispatched successfully.",
                    details={"status_code": status_code, "response": response_body},
                )
        except urllib.error.HTTPError as err:
            err_msg = f"Telegram API HTTP error {err.code}: {err.reason}"
            logger.error(err_msg)
            return NotificationResult(channel=self.channel, success=False, message=err_msg)
        except Exception as err:
            err_msg = f"Telegram dispatch failed: {err}"
            logger.error(err_msg, exc_info=True)
            return NotificationResult(channel=self.channel, success=False, message=err_msg)
