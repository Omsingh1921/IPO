"""
Unit Tests for Multi-Channel Alert & Notification Dispatch Engine.
Verifies Telegram, Slack, and Email notifiers, dry-run simulation, message models,
channel configuration discovery, dispatch aggregation, error resilience, and CLI integration.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ipo_platform.cli import main
from ipo_platform.db import get_engine, init_db
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
from ipo_platform.services.briefing_service import DailyBriefingService


class TestNotifications(unittest.TestCase):
    def setUp(self):
        """Sets up test messages and mock configurations."""
        self.test_message = NotificationMessage(
            title="Test Morning IPO Briefing",
            body_markdown="**Test Company Ltd** is listing today at ₹250.00.",
            notification_type=NotificationType.DAILY_BRIEFING,
            metadata={"test_key": "test_value"},
        )

    def test_telegram_notifier_unconfigured(self):
        notifier = TelegramNotifier(bot_token=None, chat_id=None)
        self.assertFalse(notifier.is_configured)
        self.assertEqual(notifier.channel, NotificationChannel.TELEGRAM)

        res = notifier.send(self.test_message)
        self.assertFalse(res.success)
        self.assertIn("not configured", res.message)

    def test_telegram_notifier_dry_run(self):
        notifier = TelegramNotifier(bot_token="dummy_token_123", chat_id="12345678")
        self.assertTrue(notifier.is_configured)

        res = notifier.send(self.test_message, dry_run=True)
        self.assertTrue(res.success)
        self.assertIn("[DRY-RUN]", res.message)
        self.assertEqual(res.channel, NotificationChannel.TELEGRAM)

    @patch("urllib.request.urlopen")
    def test_telegram_notifier_send_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        notifier = TelegramNotifier(bot_token="dummy_token_123", chat_id="12345678")
        res = notifier.send(self.test_message, dry_run=False)
        self.assertTrue(res.success)
        self.assertEqual(res.channel, NotificationChannel.TELEGRAM)
        self.assertIn("dispatched successfully", res.message)

    def test_slack_notifier_unconfigured(self):
        notifier = SlackNotifier(webhook_url=None)
        self.assertFalse(notifier.is_configured)
        self.assertEqual(notifier.channel, NotificationChannel.SLACK)

        res = notifier.send(self.test_message)
        self.assertFalse(res.success)
        self.assertIn("not configured", res.message)

    def test_slack_notifier_dry_run(self):
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/T00/B00/X00")
        self.assertTrue(notifier.is_configured)

        res = notifier.send(self.test_message, dry_run=True)
        self.assertTrue(res.success)
        self.assertIn("[DRY-RUN]", res.message)
        self.assertEqual(res.channel, NotificationChannel.SLACK)

    @patch("urllib.request.urlopen")
    def test_slack_notifier_send_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_response.read.return_value = b"ok"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/T00/B00/X00")
        res = notifier.send(self.test_message, dry_run=False)
        self.assertTrue(res.success)
        self.assertEqual(res.channel, NotificationChannel.SLACK)
        self.assertIn("dispatched successfully", res.message)

    def test_email_notifier_unconfigured(self):
        with patch.dict(os.environ, {"SMTP_HOST": "", "SMTP_USER": "", "MAIL_USERNAME": "", "EMAIL_FROM": "", "EMAIL_TO": "", "NOTIFICATION_EMAIL_TO": ""}):
            notifier = EmailNotifier(smtp_host=None, from_addr=None, to_addr=None)
            self.assertFalse(notifier.is_configured)
            self.assertEqual(notifier.channel, NotificationChannel.EMAIL)

            res = notifier.send(self.test_message)
            self.assertFalse(res.success)
            self.assertIn("not configured", res.message)

    def test_email_notifier_dry_run(self):
        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_addr="ipo-alerts@example.com",
            to_addr="research@fund.com",
        )
        self.assertTrue(notifier.is_configured)

        res = notifier.send(self.test_message, dry_run=True)
        self.assertTrue(res.success)
        self.assertIn("[DRY-RUN]", res.message)
        self.assertEqual(res.channel, NotificationChannel.EMAIL)

    @patch("smtplib.SMTP")
    def test_email_notifier_send_success(self, mock_smtp_class):
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        notifier = EmailNotifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            from_addr="ipo-alerts@example.com",
            to_addr="research@fund.com",
            username="user",
            password="pwd",
        )
        res = notifier.send(self.test_message, dry_run=False)
        self.assertTrue(res.success)
        self.assertEqual(res.channel, NotificationChannel.EMAIL)
        mock_server.sendmail.assert_called_once()

    def test_dispatcher_multi_channel_routing(self):
        t_notif = TelegramNotifier(bot_token="t_tok", chat_id="123")
        s_notif = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        e_notif = EmailNotifier(smtp_host="smtp.test.com", from_addr="a@b.com", to_addr="c@d.com")

        dispatcher = NotificationDispatcher([t_notif, s_notif, e_notif])
        self.assertEqual(len(dispatcher.get_registered_channels()), 3)

        # Dispatch across all channels in dry_run mode
        results = dispatcher.dispatch(self.test_message, dry_run=True)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))

        # Filtered channel dispatch
        telegram_only = dispatcher.dispatch(self.test_message, channels=["telegram"], dry_run=True)
        self.assertEqual(len(telegram_only), 1)
        self.assertEqual(telegram_only[0].channel, NotificationChannel.TELEGRAM)

    def test_notification_service_facade_workflows(self):
        t_notif = TelegramNotifier(bot_token="t_tok", chat_id="123")
        s_notif = SlackNotifier(webhook_url="https://hooks.slack.com/test")
        dispatcher = NotificationDispatcher([t_notif, s_notif])
        service = NotificationService(dispatcher=dispatcher)

        # 1. Test Daily Briefing workflow
        briefing_results = service.send_daily_briefing(
            briefing_markdown="# Morning Briefing",
            target_date="2026-10-12",
            dry_run=True,
        )
        self.assertEqual(len(briefing_results), 2)
        self.assertTrue(all(r.success for r in briefing_results))

        # 2. Test High-Conviction Alert workflow
        alert_results = service.send_high_conviction_alert(
            company_name="Apex Precision Engineering Ltd",
            ipo_id="APEX-MB-001",
            target_price=420.0,
            gmp_percentage=45.5,
            summary="Strong QIB subscription momentum with supported valuation multiples.",
            dry_run=True,
        )
        self.assertEqual(len(alert_results), 2)
        self.assertTrue(all(r.success for r in alert_results))

    def test_daily_briefing_service_integrated_dispatch(self):
        engine = get_engine("sqlite:///:memory:")
        init_db(engine)

        mock_notif_service = MagicMock()
        mock_notif_service.send_daily_briefing.return_value = [
            NotificationResult(channel=NotificationChannel.TELEGRAM, success=True, message="Sent")
        ]

        temp_reports = tempfile.mkdtemp()
        briefing_service = DailyBriefingService(
            engine=engine,
            reports_dir=temp_reports,
            notification_service=mock_notif_service,
        )

        # Generate briefing with notify=True
        briefing_service.generate_daily_briefing(target_date="2026-10-12", notify=True, dry_run=True)
        mock_notif_service.send_daily_briefing.assert_called_once()

    def test_cli_briefing_with_notify_dry_run(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
            db_path = tf.name

        db_url = f"sqlite:///{db_path}"
        engine = get_engine(db_url)
        init_db(engine)
        engine.dispose()

        try:
            with patch("sys.stdout"):
                code = main([
                    "--db-url", db_url,
                    "briefing",
                    "--date", "2026-10-12",
                    "--notify", "telegram,slack",
                    "--dry-run",
                ])
                self.assertEqual(code, 0)
        finally:
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
