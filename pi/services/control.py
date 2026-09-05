"""Control service — reconciles hardware toward desired state in the database.

The dashboard and the orchestrator run as separate systemd units sharing only
the SQLite file, so the dashboard cannot reach a live `FanService` to act on a
click. The `control_state` table is the channel: the dashboard writes what it
wants, this service reads it and applies it.

Two properties of that design matter more than the plumbing:

- **Desired state, not a command queue.** One row per control, overwritten in
  place. Nothing accumulates while the orchestrator is down, nothing replays
  twice when it comes back, and a missed poll costs latency rather than
  correctness.
- **Edge-triggered application.** A value is pushed into a service only when it
  *changes*. The database is authoritative for what the web asked for, but a
  steady row does not keep stamping on an override set locally by
  `growlab fan set` at the bench. Change the row and the database wins again.

Overrides carry an expiry, applied by `ControlEntry.effective_value`, so a
manual duty left on by accident lapses back to automatic rather than holding
the fan at 0% through a hot afternoon.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Control keys, also written by the dashboard. Keep these in one place: a typo
# on either side is a control that silently never applies.
FAN_OVERRIDE = "fan.override_duty"

CONTROL_KEYS = (FAN_OVERRIDE,)


def parse_duty(value: str | None) -> int | None:
    """Parse a stored fan duty, clamped to 0-100. Unparseable reads as auto."""
    if value is None:
        return None
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        logger.warning("Ignoring unparseable fan duty in control_state: %r", value)
        return None


class ControlService:
    """Polls `control_state` and pushes changes into the live services."""

    def __init__(
        self,
        repo,
        config,
        *,
        fan_service=None,
    ) -> None:
        self._repo = repo
        self._config = config
        self._fan = fan_service
        self._task: asyncio.Task | None = None
        # Last value seen per key, so application is edge-triggered. Starts
        # empty rather than None-filled: the first poll applies whatever the
        # database holds, which is how an override survives a restart.
        self._applied: dict[str, str | None] = {}

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.is_running:
            return

        if not self._config.enabled:
            logger.info("Control service disabled in config")
            return

        if self._fan is None:
            logger.info("Control service has nothing to drive — not started")
            return

        logger.info(
            "Control service started (poll %.1fs, override TTL %.0fs)",
            self._config.poll_interval_seconds,
            self._config.override_ttl_seconds,
        )
        self._task = asyncio.create_task(self._poll_loop(), name="control")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _poll_loop(self) -> None:
        while True:
            try:
                await self.reconcile_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Control reconcile error: %s", exc, exc_info=True)

            await asyncio.sleep(self._config.poll_interval_seconds)

    async def reconcile_once(self, now: datetime | None = None) -> dict[str, str | None]:
        """Read desired state and apply anything that changed.

        Returns the effective value of each known control, whether or not it
        changed — useful for tests and for logging what the box thinks it is
        being told.
        """
        now = now or datetime.now(timezone.utc)
        rows = await self._repo.get_all_control()

        effective: dict[str, str | None] = {}
        for key in CONTROL_KEYS:
            entry = rows.get(key)
            effective[key] = entry.effective_value(now) if entry else None

        for key, value in effective.items():
            if key in self._applied and self._applied[key] == value:
                continue
            self._apply(key, value)
            self._applied[key] = value

        return effective

    def _apply(self, key: str, value: str | None) -> None:
        if key == FAN_OVERRIDE:
            self._apply_fan(value)

    def _apply_fan(self, value: str | None) -> None:
        if self._fan is None:
            return
        duty = parse_duty(value)
        if duty is None:
            self._fan.clear_override()
            logger.info("Fan returned to auto by control_state")
        else:
            self._fan.set_override(duty)
            logger.info("Fan override %d%% applied from control_state", duty)
