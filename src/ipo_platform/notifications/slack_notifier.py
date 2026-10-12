"""
Slack Channel Notifier for Indian IPO Platform.
Dispatches formatted notifications to Slack channels via Incoming Webhooks.
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


class SlackNotifier(BaseNotifier):
    """Notifier implementation for Slack Incoming Webhooks."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
    ) -> None:
        """
        Initializes SlackNotifier with injected or environment webhook URL.

        Args:
            webhook_url: Slack incoming webhook URL (defaults to SLACK_WEBHOOK_URL env var).
        """
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SLACK

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, message: NotificationMessage, dry_run: bool = False) -> NotificationResult:
        """
        Sends formatted Block Kit message to configured Slack incoming webhook.
        """
        if not self.is_configured:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="SlackNotifier is not configured (missing SLACK_WEBHOOK_URL).",
            )

        # Truncate text if exceeding Slack block limits
        body_text = message.body_markdown
        if len(body_text) > 2900:
            body_text = body_text[:2890] + "\n\n...(truncated)"

        if dry_run:
            logger.info("[DRY-RUN] Slack notification simulated: %s", message.title)
            return NotificationResult(
                channel=self.channel,
                success=True,
                message="[DRY-RUN] Slack notification simulated successfully.",
                details={"webhook_url": self.webhook_url[:20] + "...", "text_length": len(body_text)},
            )

        payload = {
            "text": f"*{message.title}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": message.title[:150],
                        "emoji": True,
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": body_text,
                    },
                },
            ],
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url,
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
                    message="Slack message dispatched successfully.",
                    details={"status_code": status_code, "response": response_body},
                )
        except urllib.error.HTTPError as err:
            err_msg = f"Slack Webhook HTTP error {err.code}: {err.reason}"
            logger.error(err_msg)
            return NotificationResult(channel=self.channel, success=False, message=err_msg)
        except Exception as err:
            err_msg = f"Slack dispatch failed: {err}"
            logger.error(err_msg, exc_info=True)
            return NotificationResult(channel=self.channel, success=False, message=err_msg)
