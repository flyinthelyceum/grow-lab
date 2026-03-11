"""Tests for the SSD1306 OLED driver."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from pi.drivers.oled_ssd1306 import OLEDDriver


class TestOLEDInit:
    def test_defaults(self) -> None:
        driver = OLEDDriver()
        assert driver._address == 0x3C
        assert driver._bus == 1
        assert driver.WIDTH == 128
        assert driver.HEIGHT == 64

    def test_custom_address(self) -> None:
        driver = OLEDDriver(address=0x3D, bus=0)
        assert driver._address == 0x3D
        assert driver._bus == 0

    def test_not_available_without_hardware(self) -> None:
        driver = OLEDDriver()
        # On Mac, luma.oled won't find a device
        assert driver.is_available is False

    def test_available_with_mock_device(self) -> None:
        driver = OLEDDriver()
        driver._device = MagicMock()  # Simulate successful init
        assert driver.is_available is True


class TestOLEDDrawing:
    def test_clear_resets_image(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        # Image should be blank (all zeros)
        pixels = list(driver._image.getdata())
        assert all(p == 0 for p in pixels)

    def test_draw_text(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        driver.draw_text(0, 0, "HELLO")
        # Some pixels should be non-zero after drawing text
        pixels = list(driver._image.getdata())
        assert any(p > 0 for p in pixels)

    def test_draw_text_position(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        # Drawing at different positions should produce different images
        driver.draw_text(0, 0, "A")
        img1 = driver._image.copy()

        driver.clear()
        driver.draw_text(50, 30, "A")
        img2 = driver._image.copy()

        assert list(img1.getdata()) != list(img2.getdata())

    def test_draw_bar_empty_less_than_full(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        driver.draw_bar(0, 0, 100, 8, fill=0.0)
        pixels_empty = sum(1 for p in driver._image.getdata() if p > 0)

        driver.clear()
        driver.draw_bar(0, 0, 100, 8, fill=1.0)
        pixels_full = sum(1 for p in driver._image.getdata() if p > 0)

        # Full bar should have more lit pixels than empty bar
        assert pixels_full > pixels_empty

    def test_draw_bar_full(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        driver.draw_bar(0, 0, 100, 8, fill=1.0)
        pixels = sum(1 for p in driver._image.getdata() if p > 0)
        assert pixels > 50  # Mostly filled

    def test_draw_bar_clamps(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        # Should not crash with out-of-range values
        driver.draw_bar(0, 0, 100, 8, fill=-0.5)
        driver.draw_bar(0, 0, 100, 8, fill=1.5)

    def test_draw_sparkline_empty(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        driver.draw_sparkline(0, 0, 100, 30, values=[])
        # Should not crash, image stays blank

    def test_draw_sparkline_single_value(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        driver.draw_sparkline(0, 0, 100, 30, values=[5.0])
        # Should draw a flat line

    def test_draw_sparkline_with_data(self) -> None:
        driver = OLEDDriver()
        driver.clear()
        driver.draw_sparkline(0, 0, 100, 30, values=[1.0, 3.0, 2.0, 5.0, 4.0])
        pixels = list(driver._image.getdata())
        assert any(p > 0 for p in pixels)


class TestOLEDShow:
    def test_show_with_device(self) -> None:
        driver = OLEDDriver()
        mock_device = MagicMock()
        driver._device = mock_device
        driver.draw_text(0, 0, "TEST")
        driver.show()
        mock_device.display.assert_called_once()

    def test_show_without_device(self) -> None:
        driver = OLEDDriver()
        # No device — should not crash
        driver.show()


class TestOLEDClose:
    def test_close_with_device(self) -> None:
        driver = OLEDDriver()
        mock_device = MagicMock()
        driver._device = mock_device
        driver.close()
        mock_device.hide.assert_called_once()
        assert driver._device is None

    def test_close_without_device(self) -> None:
        driver = OLEDDriver()
        driver.close()  # Should not crash

    def test_close_handles_error(self) -> None:
        driver = OLEDDriver()
        mock_device = MagicMock()
        mock_device.hide.side_effect = RuntimeError("bus error")
        driver._device = mock_device
        driver.close()  # Should not raise
        assert driver._device is None
