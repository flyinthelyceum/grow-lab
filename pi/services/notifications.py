"""Notification service — dispatches alert events via webhook.

Sends notifications when alert thresholds are crossed. Each channel
runs fire-and-forget to avoid blocking the alert pipeline. Per-sensor
cooldown prevents notification storms.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from pi.config.schema import NotificationConfig
from pi.data.models import SystemEvent

logger = logging.getLogger(__name__)

NTFY_FORMAT = "ntfy"

# ntfy renders these headers as the notification title, urgency and icon.
_NTFY_TITLES = {
    "alert_critical": ("GROWLAB critical", "urgent", "rotating_light"),
    "alert_warning": ("GROWLAB warning", "high", "warning"),
    "watchdog": ("GROWLAB recovered", "high", "wrench"),
}
_NTFY_DEFAULT = ("GROWLAB", "default", "seedling")


def _ascii_header(value: str) -> str:
    """Coerce a header value to ASCII.

    HTTP headers are latin-1 at best; a stray em dash or "µ" from a sensor
    label raises UnicodeEncodeError and the whole notification is lost.
    The message body is separately UTF-8 encoded and keeps its symbols.
    """
    return value.encode("ascii", "replace").decode("ascii")


def _ntfy_headers(event: SystemEvent) -> dict[str, str]:
    """Map an event onto ntfy's Title/Priority/Tags headers."""
    title, priority, tags = _NTFY_TITLES.get(event.event_type, _NTFY_DEFAULT)
    if event.metadata:
        title = f"{title} - {event.metadata}"
    return {
        "Title": _ascii_header(title),
        "Priority": priority,
        "Tags": tags,
    }



class NotificationService:
    """Dispatches alert notifications via configured channels."""

    def __init__(self, config: NotificationConfig) -> None:
        self._config = config
        self._last_sent: dict[str, datetime] = {}
        self._http_client: httpx.AsyncClient | None = None

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
        self._last_sent = {**self._last_sent, key: datetime.now(timezone.utc)}

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient()
        return self._http_client

    async def close(self) -> None:
        """Close shared HTTP client."""
        if self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def dispatch(self, event: SystemEvent) -> None:
        """Send notifications for an alert event, respecting cooldown."""
        if event.metadata and event.metadata in self._config.muted_sensors:
            logger.debug("Notification muted for %s: %s", event.metadata, event.description)
            return

        if not self._is_cooled_down(event):
            logger.debug("Notification suppressed (cooldown): %s", event.description)
            return

        # Record cooldown on attempt to prevent storm on repeated failures
        self._record_sent(event)

        if self._config.webhook.enabled:
            try:
                await self._send_webhook(event)
            except Exception as exc:
                logger.warning("Webhook notification failed: %s", exc)

    async def _send_webhook(self, event: SystemEvent) -> None:
        """POST the alert to the configured webhook URL."""
        client = await self._get_http_client()

        if self._config.webhook.format == NTFY_FORMAT:
            response = await client.post(
                self._config.webhook.url,
                content=event.description.encode("utf-8"),
                headers=_ntfy_headers(event),
                timeout=self._config.webhook.timeout_seconds,
            )
        else:
            payload = {
                "event_type": event.event_type,
                "description": event.description,
                "timestamp": event.iso_timestamp,
                "sensor_id": event.metadata,
            }
            response = await client.post(
                self._config.webhook.url,
                json=payload,
                timeout=self._config.webhook.timeout_seconds,
            )
        response.raise_for_status()
        logger.info(
            "Webhook sent (%d): %s", response.status_code, event.description
        )
