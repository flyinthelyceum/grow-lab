"""Panel meter service — drives the two centre-zero Weston movements.

Reads the latest pH and EC from the repository, maps each to a normalised
deflection about its target, eases the needle toward it, and writes both
differential DAC pairs in one transaction.

Design notes that this implements (see docs/BOM.md):

- **Deviation, not absolute value.** Centre means on target. Drift reads as
  asymmetry, so the instrument is legible without reading numbers.
- **Damped motion.** Sensor values arrive every few minutes; the needle is
  commanded at ~30 Hz and eased with an exponential time constant, so it moves
  like an instrument rather than stepping.
- **Faults ease to centre.** A stale or missing reading walks the needle home
  and raises a flag. A needle is never driven into a stop to signal an error.
- **Per-meter calibration.** The two movements share neither gain nor
  linearity, so each has its own span and optional piecewise-linear table.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time

from pi.config.schema import MeterChannelConfig, MetersConfig
from pi.drivers.mcp4728 import differential_codes

logger = logging.getLogger(__name__)

# Channel name -> index in the A,B,C,D code tuple.
_CHANNEL_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}


def normalise(value: float, centre: float, span: float) -> float:
    """Map a sensor value to -1.0 .. +1.0 about its target.

    ``span`` is the half-range: the deflection reaching a full endpoint.
    """
    if span <= 0:
        return 0.0
    return max(-1.0, min(1.0, (value - centre) / span))


def apply_calibration(x: float, points: tuple[tuple[float, float], ...]) -> float:
    """Piecewise-linear correction of a normalised deflection.

    ``points`` are ``(commanded, actual)`` pairs in ascending commanded order —
    typically five: left endpoint, left mid, centre, right mid, right endpoint.
    Returns the command that lands the needle where ``x`` asks for. With fewer
    than two points the input passes through untouched.
    """
    if len(points) < 2:
        return x

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        if x0 <= x <= x1:
            if x1 == x0:
                return ys[i]
            t = (x - x0) / (x1 - x0)
            return ys[i] + t * (ys[i + 1] - ys[i])
    return x


def ease_alpha(dt: float, time_constant: float) -> float:
    """Exponential smoothing factor for a step of ``dt`` toward a target.

    Framed as a time constant rather than a raw coefficient so the feel of the
    needle is independent of the update rate.
    """
    if time_constant <= 0:
        return 1.0
    return 1.0 - math.exp(-dt / time_constant)


class _Needle:
    """Live state for one movement."""

    def __init__(self, config: MeterChannelConfig) -> None:
        self.config = config
        self.target = 0.0  # where the reading says it should be
        self.displayed = 0.0  # where it actually is, after easing
        self.override: float | None = None
        self.last_valid: float | None = None  # monotonic time of last good read
        self.faulted = False

    def codes(self) -> tuple[int, int]:
        commanded = apply_calibration(self.displayed, self.config.calibration)
        if self.config.invert:
            commanded = -commanded
        return differential_codes(
            commanded,
            midpoint=self.config.midpoint_code,
            span_counts=self.config.span_counts,
        )


class MeterService:
    """Background service easing both needles toward their sensor values."""

    def __init__(self, dac, repo, config: MetersConfig) -> None:
        self._dac = dac
        self._repo = repo
        self._config = config
        self._task: asyncio.Task | None = None
        self._needles: dict[str, _Needle] = {
            "ph": _Needle(config.ph),
            "ec": _Needle(config.ec),
        }

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> dict:
        """Current state of both needles, for the API and service mode."""
        return {
            name: {
                "sensor_id": n.config.sensor_id,
                "centre": n.config.centre,
                "span": n.config.span,
                "target": round(n.target, 4),
                "displayed": round(n.displayed, 4),
                "override": n.override,
                "faulted": n.faulted,
            }
            for name, n in self._needles.items()
        }

    def set_override(self, meter: str, x: float) -> bool:
        """Pin one needle to a normalised deflection for service tests."""
        needle = self._needles.get(meter)
        if needle is None:
            return False
        needle.override = max(-1.0, min(1.0, float(x)))
        return True

    def clear_override(self, meter: str | None = None) -> None:
        """Return one needle, or both, to following their sensor."""
        for name, needle in self._needles.items():
            if meter is None or name == meter:
                needle.override = None

    async def start(self) -> None:
        if self.is_running:
            return

        if not self._config.enabled:
            logger.info("Meter service disabled in config")
            return

        if not self._dac.is_available and not self._dac.connect():
            logger.warning("MCP4728 not available — meter service not started")
            return

        # Needles rest at centre before anything else happens.
        self._dac.centre_all()

        logger.info(
            "Meter service started (%d Hz, tau %.1fs, pH centre %.2f, EC centre %.2f)",
            self._config.update_hz,
            self._config.time_constant_seconds,
            self._config.ph.centre,
            self._config.ec.centre,
        )
        self._task = asyncio.create_task(self._animate_loop(), name="meters")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._dac.close()

    async def _animate_loop(self) -> None:
        """Ease both needles at the frame rate; refresh targets more slowly."""
        interval = 1.0 / max(1, self._config.update_hz)
        alpha = ease_alpha(interval, self._config.time_constant_seconds)
        last_sample = 0.0

        while True:
            try:
                now = time.monotonic()

                if now - last_sample >= self._config.sample_interval_seconds:
                    await self._refresh_targets(now)
                    last_sample = now

                for needle in self._needles.values():
                    goal = needle.override if needle.override is not None else needle.target
                    needle.displayed += (goal - needle.displayed) * alpha

                self._write_all()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("Meter loop error: %s", exc, exc_info=True)

            await asyncio.sleep(interval)

    async def _refresh_targets(self, now: float) -> None:
        """Pull the latest reading for each needle and set its target."""
        for name, needle in self._needles.items():
            cfg = needle.config
            try:
                reading = await self._repo.get_latest(cfg.sensor_id)
            except Exception as exc:
                logger.error("Meter %s read failed: %s", name, exc)
                reading = None

            if reading is None:
                self._check_fault(name, needle, now)
                continue

            value = reading.value * cfg.scale
            needle.target = normalise(value, cfg.centre, cfg.span)
            needle.last_valid = now
            if needle.faulted:
                logger.info("Meter %s recovered", name)
                needle.faulted = False

    def _check_fault(self, name: str, needle: _Needle, now: float) -> None:
        """Ease a stale needle home rather than freezing or slamming it."""
        if needle.last_valid is None:
            needle.last_valid = now
            return

        if now - needle.last_valid >= self._config.fault_timeout_seconds:
            if not needle.faulted:
                logger.warning(
                    "Meter %s stale for %.0fs — easing to centre",
                    name,
                    now - needle.last_valid,
                )
                needle.faulted = True
            needle.target = 0.0

    def _write_all(self) -> None:
        """Compose both differential pairs into one DAC transaction."""
        codes = list(self._dac.codes)
        for needle in self._needles.values():
            pos, neg = needle.codes()
            codes[_CHANNEL_INDEX[needle.config.dac_positive]] = pos
            codes[_CHANNEL_INDEX[needle.config.dac_negative]] = neg
        self._dac.write_all(tuple(codes))
