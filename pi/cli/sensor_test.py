"""Sensor CLI commands — scan, read, and test individual sensors."""

from __future__ import annotations

import asyncio

import click

from pi.config.schema import AppConfig


def _run_async(coro):
    return asyncio.run(coro)


@click.group()
def sensor_group() -> None:
    """Sensor tools — scan, read, test."""
    pass


@sensor_group.command(name="scan")
@click.pass_context
def sensor_scan(ctx: click.Context) -> None:
    """Scan hardware buses and show detected sensors."""
    config: AppConfig = ctx.obj["config"]

    from pi.discovery.scanner import scan_all

    click.echo("Scanning hardware buses...\n")
    result = scan_all(
        i2c_bus=config.i2c.bus,
        serial_port=config.serial.port,
    )

    # I²C devices
    if result.i2c_devices:
        click.echo(f"I²C bus {config.i2c.bus}:")
        from pi.discovery.registry import I2C_ADDRESS_MAP

        for dev in result.i2c_devices:
            name = I2C_ADDRESS_MAP.get(dev.address, "unknown")
            click.echo(f"  0x{dev.address:02X}  {name}")
    else:
        click.echo("I²C: no devices found")

    # 1-Wire devices
    if result.onewire_devices:
        click.echo(f"\n1-Wire:")
        for dev in result.onewire_devices:
            click.echo(f"  {dev.device_id}  (DS18B20)")
    else:
        click.echo("1-Wire: no devices found")

    # Serial devices
    if result.serial_devices:
        click.echo(f"\nSerial:")
        for dev in result.serial_devices:
            click.echo(f"  {dev.port}  (ESP32)")
    else:
        click.echo("Serial: no devices found")

    # Build registry to show status
    click.echo("\n--- Sensor Status ---")
    from pi.discovery.registry import build_registry

    registry = build_registry(config, result)
    for status in registry.all_statuses:
        indicator = "OK" if status.available else "--"
        click.echo(f"  [{indicator}] {status.sensor_id:20s} {status.reason}")

    available = len(registry.available_drivers)
    total = len(registry.all_statuses)
    click.echo(f"\n{available}/{total} sensors available")


@sensor_group.command(name="read")
@click.argument("sensor_name")
@click.pass_context
def sensor_read(ctx: click.Context, sensor_name: str) -> None:
    """Read current values from a specific sensor."""
    config: AppConfig = ctx.obj["config"]

    async def _read():
        from pi.discovery.registry import build_registry
        from pi.discovery.scanner import scan_all

        result = scan_all(
            i2c_bus=config.i2c.bus,
            serial_port=config.serial.port,
        )
        registry = build_registry(config, result)

        driver = registry.get_driver(sensor_name)
        if driver is None:
            # Check if it's a known sensor that's unavailable
            for status in registry.all_statuses:
                if status.sensor_id == sensor_name:
                    click.echo(
                        f"Sensor '{sensor_name}' is not available: {status.reason}"
                    )
                    return
            click.echo(f"Unknown sensor: '{sensor_name}'")
            click.echo(
                f"Available: {', '.join(d for d in registry.available_drivers)}"
            )
            return

        readings = await driver.read()
        if not readings:
            click.echo(f"No readings from {sensor_name} (read returned empty)")
            return

        for r in readings:
            click.echo(f"  {r.sensor_id:30s} {r.value:>10.2f} {r.unit}")
        click.echo(f"\n  timestamp: {readings[0].iso_timestamp}")

    _run_async(_read())


@sensor_group.command(name="status")
@click.pass_context
def sensor_status(ctx: click.Context) -> None:
    """Show the status of all configured sensors."""
    config: AppConfig = ctx.obj["config"]

    from pi.discovery.registry import build_registry
    from pi.discovery.scanner import scan_all

    result = scan_all(
        i2c_bus=config.i2c.bus,
        serial_port=config.serial.port,
    )
    registry = build_registry(config, result)

    for status in registry.all_statuses:
        indicator = "OK" if status.available else "--"
        click.echo(f"  [{indicator}] {status.sensor_id:20s} {status.reason}")


@sensor_group.command(name="ezo-setup")
@click.option(
    "--sensor",
    type=click.Choice(["ph", "ec"]),
    required=True,
    help="EZO sensor type to switch",
)
@click.option("--port", default="/dev/ttyUSB0", help="UART serial port")
@click.option("--baud", default=9600, type=int, help="UART baud rate (EZO default: 9600)")
@click.pass_context
def ezo_setup(ctx: click.Context, sensor: str, port: str, baud: int) -> None:
    """Switch an Atlas EZO sensor from UART to I2C mode.

    Connect the EZO sensor via a USB-UART adapter, then run this command.
    The sensor will reboot into I2C mode at its default address.
    """
    import time

    from pi.drivers.ezo_uart import EZO_ADDRESSES, switch_to_i2c

    address = EZO_ADDRESSES[sensor]
    click.echo(f"EZO {sensor.upper()} -> I2C mode at address 0x{address:02X} ({address})")
    click.echo(f"UART port: {port} @ {baud} baud")
    click.echo()

    if not click.confirm("This will reboot the sensor into I2C mode. Continue?"):
        click.echo("Aborted.")
        return

    try:
        response = switch_to_i2c(port, baud, address)
    except Exception as exc:
        click.echo(f"UART error: {exc}")
        click.echo("Check that the sensor is connected and the port is correct.")
        return

    if response in ("*OK", "*RS"):
        click.echo(f"Sensor responded: {response}")
        click.echo("Waiting 2s for sensor reboot...")
        time.sleep(2)

        # Verify on I2C bus
        config: AppConfig = ctx.obj["config"]
        from pi.discovery.scanner import scan_i2c

        devices = scan_i2c(config.i2c.bus)
        found = any(d.address == address for d in devices)
        if found:
            click.echo(f"[PASS] EZO {sensor.upper()} detected at 0x{address:02X} on I2C bus")
        else:
            click.echo(f"[WARN] EZO {sensor.upper()} not yet visible on I2C bus")
            click.echo("  The sensor may need a power cycle. Disconnect and reconnect power,")
            click.echo("  then run: growlab sensor scan")
    else:
        click.echo(f"Unexpected response: {response!r}")
        click.echo("The sensor may not be connected or may already be in I2C mode.")


def _c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


# Sensor IDs whose values are stored as C and should display as F
_TEMP_SENSOR_IDS = {"bme280_temperature", "ds18b20_temperature"}


@sensor_group.command(name="validate-all")
@click.pass_context
def validate_all(ctx: click.Context) -> None:
    """Quick hardware smoke test -- scan, read every sensor, report pass/fail."""
    config: AppConfig = ctx.obj["config"]

    async def _validate():
        from pi.discovery.registry import build_registry
        from pi.discovery.scanner import scan_all

        click.echo("Scanning hardware buses...\n")
        result = scan_all(
            i2c_bus=config.i2c.bus,
            serial_port=config.serial.port,
        )
        registry = build_registry(config, result)

        passed = 0
        failed = 0
        not_detected = 0

        for status in registry.all_statuses:
            if not status.available:
                click.echo(f"  [--]   {status.sensor_id:20s} Not detected ({status.reason})")
                not_detected += 1
                continue

            driver = registry.get_driver(status.sensor_id)
            try:
                readings = await driver.read()
                if not readings:
                    click.echo(f"  [FAIL] {status.sensor_id:20s} Read returned empty")
                    failed += 1
                    continue

                parts = []
                for r in readings:
                    value = r.value
                    unit = r.unit
                    if r.sensor_id in _TEMP_SENSOR_IDS:
                        value = _c_to_f(value)
                        unit = "F"
                    parts.append(f"{value:.1f} {unit}")
                click.echo(f"  [PASS] {status.sensor_id:20s} {' | '.join(parts)}")
                passed += 1
            except Exception as exc:
                click.echo(f"  [FAIL] {status.sensor_id:20s} Read error: {exc}")
                failed += 1

        click.echo()
        detected = passed + failed
        click.echo(
            f"{passed}/{detected} detected sensors passed. "
            f"{not_detected} configured sensor(s) not detected."
        )

    _run_async(_validate())
