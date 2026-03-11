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
