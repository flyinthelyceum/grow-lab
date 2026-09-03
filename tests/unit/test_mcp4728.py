"""Tests for the MCP4728 quad DAC driver."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pi.drivers.mcp4728 import (
    MAX_CODE,
    MIDPOINT_CODE,
    MCP4728,
    clamp_code,
    differential_codes,
)


class TestClampCode:
    def test_passes_in_range(self):
        assert clamp_code(2048) == 2048

    def test_clamps_both_ends(self):
        assert clamp_code(-100) == 0
        assert clamp_code(99999) == MAX_CODE


class TestDifferentialCodes:
    def test_centre_is_equal_channels(self):
        pos, neg = differential_codes(0.0)
        assert pos == neg == MIDPOINT_CODE

    def test_full_right_splits_the_rails(self):
        pos, neg = differential_codes(1.0)
        assert pos == MAX_CODE or pos == MIDPOINT_CODE + MIDPOINT_CODE
        assert neg == 0

    def test_full_left_is_the_mirror_of_full_right(self):
        rpos, rneg = differential_codes(1.0)
        lpos, lneg = differential_codes(-1.0)
        assert (lpos, lneg) == (rneg, rpos)

    def test_half_deflection_is_half_the_delta(self):
        pos, neg = differential_codes(0.5, midpoint=2048, span_counts=2000)
        assert pos == 3048
        assert neg == 1048

    def test_clamps_out_of_range_input(self):
        assert differential_codes(9.0) == differential_codes(1.0)
        assert differential_codes(-9.0) == differential_codes(-1.0)

    def test_narrow_span_keeps_needle_near_centre(self):
        pos, neg = differential_codes(1.0, midpoint=2048, span_counts=100)
        assert pos == 2148
        assert neg == 1948


class TestMCP4728:
    def _connected(self):
        dac = MCP4728()
        bus = MagicMock()
        with patch.dict("sys.modules", {"smbus2": MagicMock(SMBus=lambda n: bus)}):
            assert dac.connect() is True
        return dac, bus

    def test_not_available_before_connect(self):
        assert MCP4728().is_available is False

    def test_connect_failure_reports_false(self):
        dac = MCP4728()
        broken = MagicMock()
        broken.SMBus.side_effect = OSError("no bus")
        with patch.dict("sys.modules", {"smbus2": broken}):
            assert dac.connect() is False
        assert dac.is_available is False

    def test_write_all_sends_eight_data_bytes(self):
        dac, bus = self._connected()
        assert dac.write_all((0x000, 0x800, 0xFFF, 0x123)) is True

        addr, first, rest = bus.write_i2c_block_data.call_args.args
        assert addr == 0x60
        payload = [first] + list(rest)
        assert len(payload) == 8
        # Two bytes per channel, upper nibble carries D11-D8 with PD bits clear.
        assert payload == [0x00, 0x00, 0x08, 0x00, 0x0F, 0xFF, 0x01, 0x23]

    def test_write_all_clamps_and_records(self):
        dac, _ = self._connected()
        dac.write_all((-5, 99999, 100, 200))
        assert dac.codes == (0, MAX_CODE, 100, 200)

    def test_write_all_without_bus_is_false(self):
        assert MCP4728().write_all((0, 0, 0, 0)) is False

    def test_centre_all_writes_midpoint_everywhere(self):
        dac, _ = self._connected()
        assert dac.centre_all() is True
        assert dac.codes == (MIDPOINT_CODE,) * 4

    def test_eeprom_write_uses_sequential_command(self):
        dac, bus = self._connected()
        assert dac.write_eeprom_defaults((MIDPOINT_CODE,) * 4) is True

        _, first, rest = bus.write_i2c_block_data.call_args.args
        # Sequential Write from channel A: C2=0 C1=1 C0=0 W1=1 W0=0.
        assert first == 0b01010000
        assert len(rest) == 8
        # VREF=0 (VDD) in the high nibble, D11-D8 in the low.
        assert rest[0] == 0x08 and rest[1] == 0x00

    def test_write_failure_reports_false(self):
        dac, bus = self._connected()
        bus.write_i2c_block_data.side_effect = OSError("nak")
        assert dac.write_all((0, 0, 0, 0)) is False

    def test_close_centres_then_releases(self):
        dac, bus = self._connected()
        dac.write_all((0, 0, 0, 0))
        dac.close()
        # Last write before closing put every channel back at midpoint.
        assert dac.codes == (MIDPOINT_CODE,) * 4
        bus.close.assert_called_once()
        assert dac.is_available is False
