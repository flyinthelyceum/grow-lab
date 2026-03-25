"""AS7341 spectral light sensor driver.

Reads the AS7341 in two SMUX passes so the application gets one primary
lux-like light reading plus the individual spectral channels. The derived
lux value is an exposure-normalized approximation intended for relative
canopy monitoring rather than calibrated photometry.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from pi.calibration.runtime_estimator import AS7341RuntimeEstimator
from pi.data.models import SensorReading

logger = logging.getLogger(__name__)

REG_ENABLE = 0x80
REG_ATIME = 0x81
REG_ID = 0x92
REG_ASTATUS = 0x94
REG_STATUS2 = 0xA3
REG_CFG0 = 0xA9
REG_CFG1 = 0xAA
REG_CFG6 = 0xAF
REG_ASTEP_L = 0xCA
REG_ASTEP_H = 0xCB

ENABLE_PON = 0x01
ENABLE_SP_EN = 0x02
ENABLE_SMUX_EN = 0x10

STATUS2_AVALID = 0x40

CFG6_SMUX_CMD_MASK = 0x18
CFG6_SMUX_CMD_WRITE = 0x10

DEFAULT_ATIME = 29
DEFAULT_ASTEP = 599
DEFAULT_GAIN = 7  # 64x
DEFAULT_ADDRESS = 0x39
DEVICE_ID = 0x09

GAIN_FACTORS = {
    0: 0.5,
    1: 1.0,
    2: 2.0,
    3: 4.0,
    4: 8.0,
    5: 16.0,
    6: 32.0,
    7: 64.0,
    8: 128.0,
    9: 256.0,
    10: 512.0,
}

SPECTRAL_CHANNELS = (
    "as7341_415nm",
    "as7341_445nm",
    "as7341_480nm",
    "as7341_515nm",
    "as7341_555nm",
    "as7341_590nm",
    "as7341_630nm",
    "as7341_680nm",
    "as7341_clear",
    "as7341_nir",
)


def _calculate_lux_like(channels: dict[str, int], gain: int, atime: int, astep: int) -> float:
    """Convert spectral channels into a single relative lux-like value."""
    weighted_counts = (
        channels["as7341_415nm"] * 0.01
        + channels["as7341_445nm"] * 0.05
        + channels["as7341_480nm"] * 0.20
        + channels["as7341_515nm"] * 0.45
        + channels["as7341_555nm"] * 1.00
        + channels["as7341_590nm"] * 0.55
        + channels["as7341_630nm"] * 0.15
        + channels["as7341_680nm"] * 0.03
    )

    integration_ms = (atime + 1) * (astep + 1) * 0.00278
    gain_factor = GAIN_FACTORS.get(gain, 64.0)
    if integration_ms <= 0 or gain_factor <= 0:
        return 0.0

    normalized = weighted_counts / (gain_factor * max(integration_ms / 100.0, 0.01))
    return round(max(normalized, 0.0), 2)


class AS7341Driver:
    """I2C driver for the ams AS7341 spectral sensor."""

    _LOW_SMUX = (
        0x20, 0x01, 0x00, 0x00, 0x00,
        0x31, 0x00, 0x00, 0x50, 0x00,
        0x00, 0x00, 0x20, 0x03, 0x00,
        0x40, 0x01, 0x50, 0x00, 0x06,
    )
    _HIGH_SMUX = (
        0x00, 0x00, 0x00, 0x40, 0x01,
        0x00, 0x60, 0x02, 0x50, 0x60,
        0x02, 0x00, 0x00, 0x00, 0x13,
        0x00, 0x00, 0x50, 0x00, 0x06,
    )

    def __init__(
        self,
        bus_number: int = 1,
        address: int = DEFAULT_ADDRESS,
        gain: int = DEFAULT_GAIN,
        atime: int = DEFAULT_ATIME,
        astep: int = DEFAULT_ASTEP,
        ppfd_estimator: AS7341RuntimeEstimator | None = None,
        node_id: str = "",
    ) -> None:
        self._bus_number = bus_number
        self._address = address
        self._gain = gain
        self._atime = atime
        self._astep = astep
        self._ppfd_estimator = ppfd_estimator
        self._node_id = node_id
        self._bus = None

    @property
    def sensor_id(self) -> str:
        return "as7341"

    def _get_bus(self):
        if self._bus is None:
            import smbus2

            self._bus = smbus2.SMBus(self._bus_number)
        return self._bus

    def _read_byte(self, reg: int) -> int:
        return self._get_bus().read_byte_data(self._address, reg)

    def _write_byte(self, reg: int, value: int) -> None:
        self._get_bus().write_byte_data(self._address, reg, value & 0xFF)

    def _write_word(self, reg: int, value: int) -> None:
        self._write_byte(reg, value & 0xFF)
        self._write_byte(reg + 1, (value >> 8) & 0xFF)

    def _set_bits(self, reg: int, mask: int, value: int) -> None:
        current = self._read_byte(reg)
        current = (current & ~mask) | (value & mask)
        self._write_byte(reg, current)

    def _power_on(self) -> None:
        self._set_bits(REG_ENABLE, ENABLE_PON, ENABLE_PON)

    def _power_off(self) -> None:
        self._set_bits(REG_ENABLE, ENABLE_PON | ENABLE_SP_EN, 0x00)

    def _configure(self) -> None:
        self._write_byte(REG_ATIME, self._atime)
        self._write_word(REG_ASTEP_L, self._astep)
        self._write_byte(REG_CFG1, self._gain)

    def _set_low_bank(self, enabled: bool) -> None:
        self._set_bits(REG_CFG0, 0x10, 0x10 if enabled else 0x00)

    def _configure_smux(self, values: tuple[int, ...]) -> None:
        self._set_bits(REG_ENABLE, ENABLE_SP_EN, 0x00)
        self._set_low_bank(False)
        self._set_bits(REG_CFG6, CFG6_SMUX_CMD_MASK, CFG6_SMUX_CMD_WRITE)
        for offset, value in enumerate(values):
            self._write_byte(offset, value)
        self._set_bits(REG_ENABLE, ENABLE_SMUX_EN, ENABLE_SMUX_EN)
        deadline = time.monotonic() + 0.25
        while self._read_byte(REG_ENABLE) & ENABLE_SMUX_EN:
            if time.monotonic() > deadline:
                raise RuntimeError("AS7341 SMUX configuration timed out")
            time.sleep(0.001)
        self._set_bits(REG_ENABLE, ENABLE_SP_EN, ENABLE_SP_EN)

    def _wait_for_data(self, timeout: float = 1.0) -> None:
        deadline = time.monotonic() + timeout
        while not (self._read_byte(REG_STATUS2) & STATUS2_AVALID):
            if time.monotonic() > deadline:
                raise RuntimeError("AS7341 data-ready timeout")
            time.sleep(0.005)

    def _read_latched_channels(self) -> tuple[int, int, int, int, int, int]:
        data = self._get_bus().read_i2c_block_data(self._address, REG_ASTATUS, 13)
        words = []
        for index in range(1, 13, 2):
            words.append(data[index] | (data[index + 1] << 8))
        return tuple(words)  # type: ignore[return-value]

    def _read_all_channels(self) -> dict[str, int]:
        self._power_on()
        self._configure()

        self._configure_smux(self._LOW_SMUX)
        self._wait_for_data()
        low = self._read_latched_channels()

        self._configure_smux(self._HIGH_SMUX)
        self._wait_for_data()
        high = self._read_latched_channels()

        self._power_off()

        return {
            "as7341_415nm": low[0],
            "as7341_445nm": low[1],
            "as7341_480nm": low[2],
            "as7341_515nm": low[3],
            "as7341_555nm": high[0],
            "as7341_590nm": high[1],
            "as7341_630nm": high[2],
            "as7341_680nm": high[3],
            "as7341_clear": high[4],
            "as7341_nir": high[5],
        }

    async def read(self) -> list[SensorReading]:
        try:
            channels = await asyncio.to_thread(self._read_all_channels)
            now = datetime.now(timezone.utc)
            lux = _calculate_lux_like(channels, self._gain, self._atime, self._astep)
            estimator_status = "unconfigured"
            estimator_metadata = None
            ppfd = None

            if self._ppfd_estimator is not None:
                ppfd, estimator_status = self._ppfd_estimator.estimate(
                    channels,
                    gain=self._gain,
                    integration_time=self._atime,
                    astep=self._astep,
                    node_id=self._node_id,
                )
                estimator_metadata = self._ppfd_estimator.metadata_json(estimator_status)

            readings = [
                SensorReading(
                    timestamp=now,
                    sensor_id="as7341_lux",
                    value=lux,
                    unit="lux",
                    metadata=estimator_metadata,
                )
            ]
            readings.extend(
                SensorReading(
                    timestamp=now,
                    sensor_id=sensor_id,
                    value=float(channels[sensor_id]),
                    unit="raw",
                    metadata=estimator_metadata,
                )
                for sensor_id in SPECTRAL_CHANNELS
            )
            if ppfd is not None:
                readings.append(
                    SensorReading(
                        timestamp=now,
                        sensor_id="estimated_ppfd",
                        value=ppfd,
                        unit="umol/m2/s",
                        metadata=estimator_metadata,
                    )
                )
            return readings
        except Exception as exc:
            logger.error("AS7341 read failed: %s", exc)
            return []

    async def is_available(self) -> bool:
        try:
            device_id = await asyncio.to_thread(self._read_byte, REG_ID)
            return (device_id >> 2) == DEVICE_ID
        except Exception:
            return False

    async def close(self) -> None:
        if self._bus is not None:
            self._bus.close()
            self._bus = None
