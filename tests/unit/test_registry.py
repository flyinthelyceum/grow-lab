"""Tests for the sensor registry."""

from unittest.mock import AsyncMock, MagicMock, patch

from pi.config.schema import AppConfig, SensorEntry, SensorsConfig
from pi.discovery.registry import SensorRegistry, SensorStatus, build_registry
from pi.discovery.scanner import I2CDevice, ScanResult


def _make_scan(*i2c_addresses: int) -> ScanResult:
    """Create a ScanResult with given I²C addresses."""
    return ScanResult(
        i2c_devices=tuple(I2CDevice(bus=1, address=a) for a in i2c_addresses),
        onewire_devices=(),
        serial_devices=(),
    )


class TestSensorRegistry:
    def test_empty_registry(self):
        registry = SensorRegistry(())
        assert registry.available_drivers == {}
        assert registry.all_statuses == ()

    def test_available_drivers(self):
        mock_driver = MagicMock()
        mock_driver.sensor_id = "bme280"
        statuses = (
            SensorStatus("bme280", True, mock_driver, "detected"),
            SensorStatus("ds18b20", False, None, "not found"),
        )
        registry = SensorRegistry(statuses)

        assert registry.is_available("bme280")
        assert not registry.is_available("ds18b20")
        assert registry.get_driver("bme280") is mock_driver
        assert registry.get_driver("ds18b20") is None
        assert len(registry.available_drivers) == 1


class TestBuildRegistry:
    def test_bme280_detected(self):
        scan = _make_scan(0x76)
        config = AppConfig()

        with patch("pi.drivers.bme280.BME280Driver") as MockDriver:
            mock_instance = MagicMock()
            MockDriver.return_value = mock_instance
            registry = build_registry(config, scan)

        assert registry.is_available("bme280")
        MockDriver.assert_called_once_with(bus_number=1, address=0x76)

    def test_bme280_not_found(self):
        scan = _make_scan()  # empty bus
        config = AppConfig()

        registry = build_registry(config, scan)

        assert not registry.is_available("bme280")
        statuses_by_id = {s.sensor_id: s for s in registry.all_statuses}
        assert "not found" in statuses_by_id["bme280"].reason

    def test_bme280_disabled(self):
        scan = _make_scan(0x76)
        config = AppConfig(
            sensors=SensorsConfig(
                bme280=SensorEntry(address=0x76, enabled=False),
            )
        )

        registry = build_registry(config, scan)
        # Should not attempt to register disabled sensor
        statuses_by_id = {s.sensor_id: s for s in registry.all_statuses}
        assert "bme280" not in statuses_by_id

    def test_ezo_ph_not_found_shows_uart_warning(self):
        scan = _make_scan()  # no devices
        config = AppConfig()

        registry = build_registry(config, scan)

        statuses_by_id = {s.sensor_id: s for s in registry.all_statuses}
        assert "UART mode" in statuses_by_id["ezo_ph"].reason

    def test_multiple_sensors_detected(self):
        scan = _make_scan(0x76, 0x63, 0x64, 0x48)
        config = AppConfig()

        with patch("pi.drivers.bme280.BME280Driver"):
            registry = build_registry(config, scan)

        # All sensors with drivers should be available
        assert registry.is_available("bme280")
        statuses_by_id = {s.sensor_id: s for s in registry.all_statuses}
        assert statuses_by_id["ezo_ph"].available
        assert statuses_by_id["ezo_ph"].reason == "detected"
        assert statuses_by_id["ezo_ec"].available
        assert statuses_by_id["ezo_ec"].reason == "detected"
        assert statuses_by_id["soil_moisture"].available
        assert statuses_by_id["soil_moisture"].reason == "detected"

    def test_bme280_init_failure(self):
        scan = _make_scan(0x76)
        config = AppConfig()

        with patch(
            "pi.drivers.bme280.BME280Driver",
            side_effect=RuntimeError("bus error"),
        ):
            registry = build_registry(config, scan)

        assert not registry.is_available("bme280")
        statuses_by_id = {s.sensor_id: s for s in registry.all_statuses}
        assert "init failed" in statuses_by_id["bme280"].reason
