"""
Email Channel Notifier for Indian IPO Platform.
Dispatches formatted HTML and plaintext email notifications via standard SMTP.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from ipo_platform.notifications.base import (
    BaseNotifier,
    NotificationChannel,
    NotificationMessage,
    NotificationResult,
)

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Notifier implementation for SMTP email dispatch."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_addr: Optional[str] = None,
        to_addr: Optional[str] = None,
        use_tls: bool = True,
    ) -> None:
        """
        Initializes EmailNotifier with injected or environment SMTP parameters.
        """
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST") or os.getenv("MAIL_HOST")
        env_port = os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT")
        self.smtp_port = smtp_port or (int(env_port) if env_port else 587)
        self.username = username or os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD") or os.getenv("MAIL_PASSWORD")
        self.from_addr = from_addr or os.getenv("EMAIL_FROM") or self.username
        self.to_addr = to_addr or os.getenv("EMAIL_TO") or os.getenv("NOTIFICATION_EMAIL_TO") or self.username
        self.use_tls = use_tls

    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    @property
    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.from_addr and self.to_addr)

    def send(self, message: NotificationMessage, dry_run: bool = False) -> NotificationResult:
        """
        Sends formatted email to configured recipients.
        """
        if not self.is_configured:
            return NotificationResult(
                channel=self.channel,
                success=False,
                message="EmailNotifier is not configured (missing SMTP_HOST, EMAIL_FROM, or EMAIL_TO).",
            )

        if dry_run:
            logger.info("[DRY-RUN] Email notification simulated: %s", message.title)
            return NotificationResult(
                channel=self.channel,
                success=True,
                message="[DRY-RUN] Email notification simulated successfully.",
                details={"to": self.to_addr, "subject": message.title},
            )

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = self.from_addr
            msg["To"] = self.to_addr

            # Plain text part
            text_part = MIMEText(message.body_markdown, "plain", "utf-8")
            msg.attach(text_part)

            # Basic HTML conversion for enhanced email clients
            html_body = f"""<html>
<head><style>body {{ font-family: sans-serif; line-height: 1.5; }} pre {{ background: #f4f4f4; padding: 10px; }}</style></head>
<body>
<h2>{message.title}</h2>
<pre>{message.body_markdown}</pre>
</body>
</html>"""
            html_part = MIMEText(html_body, "html", "utf-8")
            msg.attach(html_part)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, [self.to_addr], msg.as_string())

            return NotificationResult(
                channel=self.channel,
                success=True,
                message="Email message dispatched successfully.",
                details={"recipient": self.to_addr},
            )
        except Exception as err:
            err_msg = f"Email dispatch failed: {err}"
            logger.error(err_msg, exc_info=True)
            return NotificationResult(channel=self.channel, success=False, message=err_msg)
