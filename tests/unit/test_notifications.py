"""Tests for the notification service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import EmailConfig, NotificationConfig, WebhookConfig
from pi.data.models import SystemEvent
from pi.services.notifications import NotificationService


def _alert_event(
    event_type: str = "alert_warning",
    description: str = "Air warning: 82.4 °F",
    metadata: str | None = "bme280_temperature",
) -> SystemEvent:
    return SystemEvent(
        timestamp=datetime.now(timezone.utc),
        event_type=event_type,
        description=description,
        metadata=metadata,
    )


@pytest.fixture
def disabled_config():
    return NotificationConfig()


@pytest.fixture
def webhook_config():
    return NotificationConfig(
        webhook=WebhookConfig(enabled=True, url="https://example.com/hook"),
        cooldown_seconds=300,
    )


@pytest.fixture
def email_config():
    return NotificationConfig(
        email=EmailConfig(
            enabled=True,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user",
            smtp_password="pass",
            from_address="growlab@example.com",
            to_addresses=("user@example.com",),
        ),
        cooldown_seconds=300,
    )


class TestNotificationServiceInit:
    def test_creates_with_defaults(self, disabled_config):
        svc = NotificationService(disabled_config)
        assert svc._config is disabled_config


class TestCooldown:
    async def test_first_dispatch_not_cooled_down(self, webhook_config):
        svc = NotificationService(webhook_config)
        event = _alert_event()
        assert svc._is_cooled_down(event) is True

    async def test_second_dispatch_within_cooldown_suppressed(self, webhook_config):
        svc = NotificationService(webhook_config)
        event = _alert_event()
        with patch.object(svc, "_send_webhook", new_callable=AsyncMock):
            await svc.dispatch(event)
        # Same sensor, should be suppressed
        assert svc._is_cooled_down(_alert_event()) is False

    async def test_different_sensor_not_suppressed(self, webhook_config):
        svc = NotificationService(webhook_config)
        event1 = _alert_event(metadata="bme280_temperature")
        with patch.object(svc, "_send_webhook", new_callable=AsyncMock):
            await svc.dispatch(event1)
        event2 = _alert_event(metadata="bme280_humidity")
        assert svc._is_cooled_down(event2) is True

    async def test_cooldown_expires(self, webhook_config):
        config = NotificationConfig(
            webhook=WebhookConfig(enabled=True, url="https://example.com/hook"),
            cooldown_seconds=0,  # Immediate expiry
        )
        svc = NotificationService(config)
        event = _alert_event()
        with patch.object(svc, "_send_webhook", new_callable=AsyncMock):
            await svc.dispatch(event)
        assert svc._is_cooled_down(_alert_event()) is True

    async def test_no_metadata_uses_event_type_for_cooldown(self, webhook_config):
        svc = NotificationService(webhook_config)
        event = _alert_event(metadata=None)
        with patch.object(svc, "_send_webhook", new_callable=AsyncMock):
            await svc.dispatch(event)
        assert svc._is_cooled_down(_alert_event(metadata=None)) is False


class TestDisabledChannels:
    async def test_no_dispatch_when_all_disabled(self, disabled_config):
        svc = NotificationService(disabled_config)
        event = _alert_event()
        # Should not raise, should do nothing
        await svc.dispatch(event)

    async def test_webhook_not_called_when_disabled(self, disabled_config):
        svc = NotificationService(disabled_config)
        with patch.object(svc, "_send_webhook", new_callable=AsyncMock) as mock_wh:
            await svc.dispatch(_alert_event())
            mock_wh.assert_not_called()


class TestWebhookChannel:
    async def test_sends_post_request(self, webhook_config):
        svc = NotificationService(webhook_config)
        event = _alert_event()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("pi.services.notifications.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            await svc._send_webhook(event)

            mock_client.post.assert_called_once()
            call_kwargs = mock_client.post.call_args
            assert call_kwargs[0][0] == "https://example.com/hook"
            payload = call_kwargs[1]["json"]
            assert payload["event_type"] == "alert_warning"
            assert "description" in payload
            assert "timestamp" in payload

    async def test_webhook_error_propagates(self, webhook_config):
        """Webhook errors propagate (caught by dispatch, not _send_webhook)."""
        svc = NotificationService(webhook_config)
        event = _alert_event()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

        with patch("pi.services.notifications.httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            with pytest.raises(Exception, match="connection refused"):
                await svc._send_webhook(event)

    async def test_dispatch_catches_webhook_error(self, webhook_config):
        """dispatch() should catch webhook errors and not raise."""
        svc = NotificationService(webhook_config)
        event = _alert_event()

        with patch.object(svc, "_send_webhook", new_callable=AsyncMock) as mock_wh:
            mock_wh.side_effect = Exception("webhook failed")
            # Should not raise
            await svc.dispatch(event)


class TestEmailChannel:
    async def test_sends_email(self, email_config):
        svc = NotificationService(email_config)
        event = _alert_event()

        with patch("pi.services.notifications.smtplib.SMTP") as MockSMTP:
            mock_smtp = MagicMock()
            MockSMTP.return_value.__enter__ = MagicMock(return_value=mock_smtp)
            MockSMTP.return_value.__exit__ = MagicMock(return_value=False)

            await svc._send_email(event)

            mock_smtp.sendmail.assert_called_once()
            call_args = mock_smtp.sendmail.call_args[0]
            assert call_args[0] == "growlab@example.com"
            assert call_args[1] == ["user@example.com"]

    async def test_handles_smtp_error(self, email_config):
        """SMTP errors should propagate (caught by dispatch, not _send_email)."""
        svc = NotificationService(email_config)
        event = _alert_event()

        with patch("pi.services.notifications.smtplib.SMTP") as MockSMTP:
            MockSMTP.side_effect = Exception("SMTP connection failed")

            with pytest.raises(Exception, match="SMTP connection failed"):
                await svc._send_email(event)

    async def test_dispatch_catches_email_error(self, email_config):
        """dispatch() should catch email errors and not raise."""
        svc = NotificationService(email_config)
        event = _alert_event()

        with patch.object(svc, "_send_email", new_callable=AsyncMock) as mock_email:
            mock_email.side_effect = Exception("SMTP failed")
            # Should not raise
            await svc.dispatch(event)
