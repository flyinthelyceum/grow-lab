"""Threshold alerting service — logs events when readings cross boundaries.

Periodically checks the latest sensor readings against configurable
threshold rules. Generates SystemEvent entries for warning and critical
transitions. Suppresses duplicate alerts while a sensor remains in the
same alert state.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from pi.data.models import SystemEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThresholdRule:
    """Defines alert thresholds for a single sensor.

    Values are in display units (e.g., °F for temperature).
    If the sensor stores values in a different unit (e.g., °C),
    provide a convert_fn to transform before comparison.
    """

    sensor_id: str
    warning_low: float
    warning_high: float
    critical_low: float
    critical_high: float
    convert_fn: Callable[[float], float] | None = field(default=None)
    label: str = ""
    unit: str = ""


def classify_reading(value: float, rule: ThresholdRule) -> str:
    """Classify a reading against a threshold rule.

    Returns "normal", "warning", or "critical".
    """
    if value < rule.critical_low or value > rule.critical_high:
        return "critical"
    if value < rule.warning_low or value > rule.warning_high:
        return "warning"
    return "normal"


# Default rules matching the dashboard range indicators
DEFAULT_RULES: tuple[ThresholdRule, ...] = (
    ThresholdRule(
        sensor_id="bme280_temperature",
        warning_low=65.0,
        warning_high=80.0,
        critical_low=60.0,
        critical_high=85.0,
        convert_fn=lambda c: c * 9.0 / 5.0 + 32.0,
        label="Air",
        unit="°F",
    ),
    ThresholdRule(
        sensor_id="bme280_humidity",
        warning_low=40.0,
        warning_high=70.0,
        critical_low=30.0,
        critical_high=80.0,
        label="Humidity",
        unit="%",
    ),
    ThresholdRule(
        sensor_id="ezo_ph",
        warning_low=5.8,
        warning_high=6.2,
        critical_low=5.0,
        critical_high=7.5,
        label="pH",
        unit="",
    ),
    ThresholdRule(
        sensor_id="ezo_ec",
        warning_low=800.0,
        warning_high=1200.0,
        critical_low=400.0,
        critical_high=1600.0,
        label="EC",
        unit="µS/cm",
    ),
)

# The pH and EC entries above are the same numbers ReservoirConfig defaults to,
# and they are here only so AlertService still has something sane when it is
# constructed without a config. Anything that HAS a config should call
# rules_from_config, which is the one path that cannot drift from the dials.
_RESERVOIR_SENSORS = ("ezo_ph", "ezo_ec")


def rules_from_config(config) -> tuple[ThresholdRule, ...]:
    """DEFAULT_RULES with the reservoir bands taken from `[reservoir]`.

    Before this existed the EC band lived in three places -- the runbook's
    prose, this module's constants, and the dial's centre -- and the three had
    already drifted apart: the docs said a reading of 1,300 uS/cm was out of
    range and this file said it was fine. Now the docs describe what the config
    says, and the alert and the needle are computed from the same two numbers.
    """
    r = config.reservoir
    overrides = {
        "ezo_ph": ThresholdRule(
            sensor_id="ezo_ph",
            warning_low=r.ph_warning_low,
            warning_high=r.ph_warning_high,
            critical_low=r.ph_critical_low,
            critical_high=r.ph_critical_high,
            label="pH",
            unit="",
        ),
        "ezo_ec": ThresholdRule(
            sensor_id="ezo_ec",
            warning_low=r.ec_warning_low_us,
            warning_high=r.ec_warning_high_us,
            critical_low=r.ec_critical_low_us,
            critical_high=r.ec_critical_high_us,
            label="EC",
            unit="µS/cm",
        ),
    }
    return tuple(
        overrides.get(rule.sensor_id, rule)
        if rule.sensor_id in _RESERVOIR_SENSORS
        else rule
        for rule in DEFAULT_RULES
    )


class AlertService:
    """Background service that checks sensor readings against thresholds."""

    def __init__(
        self,
        repo,
        rules: list[ThresholdRule] | None = None,
        poll_interval: int = 60,
        on_alert: Callable | None = None,
    ) -> None:
        self._repo = repo
        self._rules = list(rules) if rules is not None else list(DEFAULT_RULES)
        self._poll_interval = poll_interval
        self._on_alert = on_alert
        self._task: asyncio.Task | None = None
        # Track last alert state per sensor to avoid duplicate events
        self._last_state: dict[str, str] = {}

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        """Start the alert checking loop."""
        if self.is_running:
            return

        logger.info(
            "Alert service started (%d rules, %ds interval)",
            len(self._rules),
            self._poll_interval,
        )
        self._task = asyncio.create_task(
            self._check_loop(), name="alert-check"
        )

    async def stop(self) -> None:
        """Stop the alert service."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _check_loop(self) -> None:
        """Periodically evaluate all threshold rules."""
        while True:
            for rule in self._rules:
                try:
                    await self._evaluate_rule(rule)
                except Exception as exc:
                    logger.warning("Alert check error for %s: %s", rule.sensor_id, exc)

            await asyncio.sleep(self._poll_interval)

    async def _evaluate_rule(self, rule: ThresholdRule) -> None:
        """Check one sensor against its threshold rule."""
        reading = await self._repo.get_latest(rule.sensor_id)
        if reading is None:
            return

        value = reading.value
        if rule.convert_fn is not None:
            value = rule.convert_fn(value)

        state = classify_reading(value, rule)
        prev_state = self._last_state.get(rule.sensor_id, "normal")

        if state == prev_state:
            return  # No transition

        self._last_state[rule.sensor_id] = state

        if state == "normal":
            # Recovery — clear state, no event needed
            return

        label = rule.label or rule.sensor_id
        unit_str = f" {rule.unit}" if rule.unit else ""
        event = SystemEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=f"alert_{state}",
            description=f"{label} {state}: {value:.1f}{unit_str}",
            metadata=rule.sensor_id,
        )
        await self._repo.save_event(event)
        logger.warning(
            "Alert: %s %s — %s %.1f%s",
            label,
            state,
            rule.sensor_id,
            value,
            unit_str,
        )

        if self._on_alert is not None:
            try:
                await self._on_alert(event)
            except Exception as exc:
                logger.warning("on_alert callback error: %s", exc)
