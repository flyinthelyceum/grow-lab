"""Application orchestrator — starts polling and optional dashboard.

Entry point for `growlab start`. Wires together config, discovery,
registry, repository, and polling service.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from pathlib import Path

from pi.config.loader import load_config
from pi.config.schema import AppConfig
from pi.data.models import SystemEvent
from pi.data.repository import SensorRepository
from pi.discovery.registry import build_registry
from pi.discovery.scanner import scan_all
from pi.services.alerts import AlertService
from pi.services.irrigation import IrrigationService
from pi.services.polling import PollingService

logger = logging.getLogger(__name__)


def _get_sd_notify():
    """Return a systemd notify function, or a no-op if unavailable."""
    try:
        import socket
        addr = os.environ.get("NOTIFY_SOCKET")
        if addr:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            if addr.startswith("@"):
                addr = "\0" + addr[1:]
            def _notify(msg: str) -> None:
                try:
                    sock.sendto(msg.encode(), addr)
                except OSError:
                    pass
            return _notify
    except Exception:
        pass
    return lambda msg: None


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

    # Start alert service (threshold monitoring)
    from pi.dashboard.connections import ConnectionManager
    from pi.services.notifications import NotificationService

    connection_manager = ConnectionManager()
    notification_svc = NotificationService(config.notifications)

    async def _on_alert(event):
        """Push alert events to dashboard clients and notification channels."""
        await connection_manager.broadcast_json({
            "type": "alert",
            "alert": {
                "timestamp": event.iso_timestamp,
                "event_type": event.event_type,
                "description": event.description,
            },
        })
        await notification_svc.dispatch(event)

    alert_svc = AlertService(repo, on_alert=_on_alert)
    await alert_svc.start()

    # Start fan service (temperature-triggered PWM)
    fan_svc = None
    if config.fan.enabled:
        from pi.drivers.fan_pwm import FanPWMDriver
        from pi.services.fan import FanService

        fan_driver = FanPWMDriver(
            gpio_pin=config.fan.gpio_pin,
            frequency=config.fan.frequency,
            min_duty=config.fan.min_duty,
            max_duty=config.fan.max_duty,
            ramp_temp_low_f=config.fan.ramp_temp_low_f,
            ramp_temp_high_f=config.fan.ramp_temp_high_f,
        )
        fan_svc = FanService(fan_driver, repo, config.fan)
        await fan_svc.start()

    # Start lighting scheduler (requires ESP32 for LED PWM)
    lighting_svc = None
    esp32_lighting = None
    if config.lighting.on_hour != config.lighting.off_hour:
        from pi.drivers.esp32_serial import ESP32Serial
        from pi.services.lighting import LightingScheduler

        # Reuse the pump ESP32 connection if pump_controller is esp32,
        # otherwise open a dedicated connection for lighting.
        if pump is not None and config.irrigation.pump_controller == "esp32":
            esp32_lighting = pump
        else:
            esp32_lighting = ESP32Serial(
                port=config.serial.port,
                baud=config.serial.baud,
                timeout=config.serial.timeout,
            )
            if not esp32_lighting.connect():
                logger.warning("Lighting scheduler disabled — ESP32 not available on %s", config.serial.port)
                esp32_lighting = None

        if esp32_lighting is not None:
            lighting_svc = LightingScheduler(esp32_lighting, repo, config.lighting)
            await lighting_svc.start()

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()

    def _signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    logger.info("System running. Press Ctrl+C to stop.")

    # Notify systemd watchdog periodically while waiting for shutdown
    sd_notify = _get_sd_notify()
    sd_notify("READY=1")
    while not shutdown_event.is_set():
        sd_notify("WATCHDOG=1")
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=120)
        except asyncio.TimeoutError:
            pass  # Loop back to send next watchdog ping

    # Clean shutdown
    logger.info("Shutting down...")
    if lighting_svc is not None:
        await lighting_svc.stop()
    if esp32_lighting is not None and esp32_lighting is not pump:
        esp32_lighting.close()
    if fan_svc is not None:
        await fan_svc.stop()
    await alert_svc.stop()
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
