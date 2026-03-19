"""Notification service — dispatches alert events via webhook and email.

Sends notifications when alert thresholds are crossed. Each channel
runs fire-and-forget to avoid blocking the alert pipeline. Per-sensor
cooldown prevents notification storms.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

import httpx

from pi.config.schema import NotificationConfig
from pi.data.models import SystemEvent

logger = logging.getLogger(__name__)


class NotificationService:
    """Dispatches alert notifications via configured channels."""

    def __init__(self, config: NotificationConfig) -> None:
        self._config = config
        self._last_sent: dict[str, datetime] = {}

    def _is_cooled_down(self, event: SystemEvent) -> bool:
        """Check if enough time has passed since the last notification for this sensor."""
        key = event.metadata or event.event_type
        last = self._last_sent.get(key)
        if last is None:
            return True
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return elapsed >= self._config.cooldown_seconds

    def _record_sent(self, event: SystemEvent) -> None:
        key = event.metadata or event.event_type
        self._last_sent[key] = datetime.now(timezone.utc)

    async def dispatch(self, event: SystemEvent) -> None:
        """Send notifications for an alert event, respecting cooldown."""
        if not self._is_cooled_down(event):
            logger.debug("Notification suppressed (cooldown): %s", event.description)
            return

        sent = False

        if self._config.webhook.enabled:
            try:
                await self._send_webhook(event)
                sent = True
            except Exception as exc:
                logger.warning("Webhook notification failed: %s", exc)

        if self._config.email.enabled:
            try:
                await self._send_email(event)
                sent = True
            except Exception as exc:
                logger.warning("Email notification failed: %s", exc)

        if sent:
            self._record_sent(event)

    async def _send_webhook(self, event: SystemEvent) -> None:
        """POST alert as JSON to the configured webhook URL."""
        payload = {
            "event_type": event.event_type,
            "description": event.description,
            "timestamp": event.iso_timestamp,
            "sensor_id": event.metadata,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._config.webhook.url,
                json=payload,
                timeout=self._config.webhook.timeout_seconds,
            )
            logger.info(
                "Webhook sent (%d): %s", response.status_code, event.description
            )

    async def _send_email(self, event: SystemEvent) -> None:
        """Send alert email via SMTP (runs in thread to avoid blocking)."""
        cfg = self._config.email

        def _smtp_send():
            msg = EmailMessage()
            msg["Subject"] = f"GROWLAB Alert: {event.description}"
            msg["From"] = cfg.from_address
            msg["To"] = ", ".join(cfg.to_addresses)
            msg.set_content(
                f"GROWLAB Alert\n\n"
                f"Type: {event.event_type}\n"
                f"Description: {event.description}\n"
                f"Time: {event.iso_timestamp}\n"
                f"Sensor: {event.metadata or 'unknown'}\n"
            )

            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
                if cfg.use_tls:
                    server.starttls()
                if cfg.smtp_user:
                    server.login(cfg.smtp_user, cfg.smtp_password)
                server.sendmail(
                    cfg.from_address,
                    list(cfg.to_addresses),
                    msg.as_string(),
                )

        await asyncio.to_thread(_smtp_send)
        logger.info("Email sent: %s", event.description)
