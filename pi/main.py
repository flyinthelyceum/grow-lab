"""Application orchestrator — starts polling and optional dashboard.

Entry point for `growlab start`. Wires together config, discovery,
registry, repository, and polling service.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from pathlib import Path

from pi.config.loader import load_config
from pi.config.schema import AppConfig
from pi.data.models import SystemEvent
from pi.data.repository import SensorRepository
from pi.discovery.registry import build_registry
from pi.discovery.scanner import scan_all
from pi.services.irrigation import IrrigationService
from pi.services.polling import PollingService

logger = logging.getLogger(__name__)


def _build_pump_controller(config: AppConfig):
    """Build pump controller from config (gpio or esp32)."""
    backend = config.irrigation.pump_controller

    if backend == "gpio":
        from pi.drivers.gpio_relay import GPIORelayPump

        return GPIORelayPump(gpio_pin=config.irrigation.relay_gpio)

    if backend == "esp32":
        from pi.drivers.esp32_serial import ESP32Serial

        esp32 = ESP32Serial(
            port=config.serial.port,
            baud=config.serial.baud,
            timeout=config.serial.timeout,
        )
        if esp32.connect():
            return esp32
        logger.error("ESP32 pump controller failed to connect on %s", config.serial.port)
        return None

    logger.error("Unknown pump_controller '%s'", backend)
    return None


async def run(config: AppConfig) -> None:
    """Main application loop — scan, build registry, poll, serve."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.system.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("GROWLAB starting...")

    # Ensure data directory exists
    config.system.data_dir.mkdir(parents=True, exist_ok=True)

    # Connect to database
    repo = SensorRepository(config.system.db_path)
    await repo.connect()

    # Log startup event
    from datetime import datetime, timezone

    await repo.save_event(
        SystemEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="system_start",
            description="GROWLAB started",
        )
    )

    # Scan hardware and build registry
    logger.info("Scanning hardware buses...")
    scan_result = scan_all(
        i2c_bus=config.i2c.bus,
        serial_port=config.serial.port,
    )

    registry = build_registry(config, scan_result)

    available = len(registry.available_drivers)
    total = len(registry.all_statuses)
    logger.info("Sensor registry: %d/%d available", available, total)

    for status in registry.all_statuses:
        level = logging.INFO if status.available else logging.WARNING
        logger.log(level, "  %s: %s", status.sensor_id, status.reason)

    # Start polling
    poller = PollingService(registry, repo, config)
    await poller.start()

    # Set up camera for pump-triggered captures
    camera_svc = None
    if config.camera.enabled:
        from pi.drivers.camera import CameraDriver
        from pi.services.camera_capture import CameraCaptureService

        camera = CameraDriver(resolution=config.camera.resolution)
        camera_svc = CameraCaptureService(camera, repo, config.camera)

    async def _on_pump_active():
        """Capture an image while the pump relay is active (LED lit)."""
        if camera_svc is not None and camera_svc._camera.is_available:
            logger.info("Pump-active camera capture (relay LED on)")
            await camera_svc.capture_now()

    # Start irrigation scheduler
    irrigator: IrrigationService | None = None
    pump = _build_pump_controller(config)
    if pump is not None:
        irrigator = IrrigationService(
            pump, repo, config.irrigation,
            on_pulse_start=_on_pump_active,
            pulse_start_delay=3.0,
        )
        await irrigator.start()
    else:
        logger.warning("Irrigation scheduler disabled — pump controller unavailable")

    # Start display service
    display_svc = None
    if config.display.enabled:
        from pi.drivers.oled_ssd1306 import OLEDDriver
        from pi.services.display import DisplayService

        oled = OLEDDriver(
            address=config.display.address,
            controller=config.display.controller,
        )
        display_svc = DisplayService(
            oled=oled,
            repo=repo,
            config=config.display,
            irrigation_config=config.irrigation,
            irrigator=irrigator,
        )
        await display_svc.start()

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    logger.info("System running. Press Ctrl+C to stop.")

    # Wait for shutdown
    await shutdown_event.wait()

    # Clean shutdown
    logger.info("Shutting down...")
    if display_svc is not None:
        await display_svc.stop()
    if irrigator is not None:
        await irrigator.stop()
    await poller.stop()
    if camera_svc is not None:
        camera_svc._camera.close()

    # Close sensor drivers
    for driver in registry.available_drivers.values():
        await driver.close()

    # Log shutdown event
    await repo.save_event(
        SystemEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="system_stop",
            description="GROWLAB stopped",
        )
    )

    await repo.close()
    logger.info("Shutdown complete.")


def start(config_path: Path | None = None) -> None:
    """Synchronous entry point for the orchestrator."""
    config = load_config(config_path)
    asyncio.run(run(config))
