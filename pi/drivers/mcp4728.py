"""MCP4728 driver — quad 12-bit I²C DAC, drives the front-panel meters.

Communicates over I²C using smbus2. Default address 0x60 (no conflict with
EZO-pH 0x63, EZO-EC 0x64, ADS1115 0x48, AS7341 0x39, OLED 0x3c).

Each centre-zero Weston movement sits between two DAC channels with a fixed
resistor in each leg, so needle current is set by the *difference* between the
pair. Both channels rest at the same midpoint code, which is zero volts across
the movement and a centred needle:

    DAC A/C ── R_LEFT ── movement ── R_RIGHT ── DAC B/D

Series resistance is what protects the movement, not firmware: even a full
opposite-rail fault lands just under full scale. See docs/BOM.md.

Command formats are from the MCP4728 datasheet DS22187E section 5.6:

  Fast Write (C2=0, C1=0):  eight data bytes, channels A-D in order, two each
                            [0 0 PD1 PD0 D11 D10 D9 D8][D7..D0]
                            Updates DAC registers only. EEPROM untouched.

  Sequential Write (C2=0, C1=1, C0=0, W1=1, W0=0):
                            [0 1 0 1 0 DAC1 DAC0 UDAC]
                            then per channel through D:
                            [VREF PD1 PD0 Gx D11 D10 D9 D8][D7..D0]
                            Writes DAC registers *and* EEPROM, so the codes
                            are restored at power-up.

VREF bit: 0 = VDD, 1 = internal 2.048V. This build runs the DAC from its supply
rail and uses VDD as reference, so VREF = 0 and the gain bit does not apply.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_ADDRESS = 0x60

# Channel indices, in the order the chip writes them.
CHANNELS = ("A", "B", "C", "D")

MAX_CODE = 0xFFF  # 12-bit
MIDPOINT_CODE = 0x800  # 2048 — zero volts across a differential pair

# Sequential Write command byte: C2=0 C1=1 C0=0 W1=1 W0=0, starting channel A,
# UDAC=0 so outputs update as the write lands.
_SEQ_WRITE_FROM_A = 0b01010000

# Third-byte flags for Sequential Write: VREF=0 (VDD), PD=00 (normal), Gx=0.
_VREF_VDD_NORMAL = 0b0000


def clamp_code(code: int) -> int:
    """Clamp a DAC code into the 12-bit range."""
    return max(0, min(MAX_CODE, int(code)))


def differential_codes(
    x: float,
    *,
    midpoint: int = MIDPOINT_CODE,
    span_counts: int = MIDPOINT_CODE,
) -> tuple[int, int]:
    """Codes for a differential pair from a normalised deflection.

    ``x`` runs -1.0 (full left) through 0.0 (centred) to +1.0 (full right).
    The positive channel rises as the negative channel falls by the same
    amount, so the midpoint cancels and the needle sees only the difference.

    Returns ``(positive_code, negative_code)``, both clamped.
    """
    x = max(-1.0, min(1.0, float(x)))
    delta = x * span_counts
    return clamp_code(round(midpoint + delta)), clamp_code(round(midpoint - delta))


class MCP4728:
    """Quad 12-bit DAC over I²C."""

    def __init__(
        self,
        bus_number: int = 1,
        address: int = DEFAULT_ADDRESS,
    ) -> None:
        self._bus_number = bus_number
        self._address = address
        self._bus = None
        self._codes = [MIDPOINT_CODE] * 4

    @property
    def address(self) -> int:
        return self._address

    @property
    def codes(self) -> tuple[int, int, int, int]:
        """Last codes written, channels A-D."""
        return tuple(self._codes)  # type: ignore[return-value]

    @property
    def is_available(self) -> bool:
        return self._bus is not None

    def connect(self) -> bool:
        """Open the I²C bus. Returns True on success."""
        if self._bus is not None:
            return True
        try:
            import smbus2

            self._bus = smbus2.SMBus(self._bus_number)
            logger.info("MCP4728 connected on i2c-%d at 0x%02x", self._bus_number, self._address)
            return True
        except Exception as exc:
            logger.error("MCP4728 connect failed: %s", exc)
            self._bus = None
            return False

    def write_all(self, codes: tuple[int, int, int, int]) -> bool:
        """Fast Write all four channels. DAC registers only, EEPROM untouched.

        This is the animation path — one 8-byte transaction moves both needles.
        """
        if self._bus is None:
            logger.warning("MCP4728 write_all with no bus")
            return False

        payload: list[int] = []
        clamped = [clamp_code(c) for c in codes]
        for code in clamped:
            payload.append((code >> 8) & 0x0F)  # PD1 PD0 = 00, upper 4 data bits
            payload.append(code & 0xFF)

        try:
            # No register byte in Fast Write: the first data byte takes that slot.
            self._bus.write_i2c_block_data(self._address, payload[0], payload[1:])
            self._codes = clamped
            logger.debug("MCP4728 fast write %s", clamped)
            return True
        except Exception as exc:
            logger.error("MCP4728 write_all failed: %s", exc)
            return False

    def write_eeprom_defaults(self, codes: tuple[int, int, int, int]) -> bool:
        """Sequential Write all four channels to DAC registers *and* EEPROM.

        Call once at commissioning with the midpoint codes so both needles are
        centred through boot, reset and power-down — never parked against a
        stop. EEPROM has a finite write endurance, so this is not for the
        animation loop.
        """
        if self._bus is None:
            logger.warning("MCP4728 write_eeprom_defaults with no bus")
            return False

        payload: list[int] = []
        clamped = [clamp_code(c) for c in codes]
        for code in clamped:
            payload.append((_VREF_VDD_NORMAL << 4) | ((code >> 8) & 0x0F))
            payload.append(code & 0xFF)

        try:
            self._bus.write_i2c_block_data(self._address, _SEQ_WRITE_FROM_A, payload)
            self._codes = clamped
            logger.info("MCP4728 EEPROM defaults written: %s", clamped)
            return True
        except Exception as exc:
            logger.error("MCP4728 write_eeprom_defaults failed: %s", exc)
            return False

    def centre_all(self) -> bool:
        """Drive every channel to the midpoint — both needles to rest."""
        return self.write_all((MIDPOINT_CODE,) * 4)

    def close(self) -> None:
        """Centre the needles, then release the bus."""
        if self._bus is not None:
            try:
                self.centre_all()
            except Exception as exc:
                logger.debug("MCP4728 centre-on-close failed: %s", exc)
            try:
                self._bus.close()
            except Exception as exc:
                logger.debug("MCP4728 bus close error: %s", exc)
        self._bus = None
