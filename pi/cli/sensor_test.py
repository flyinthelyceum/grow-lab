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


@sensor_group.command(name="ph-slope")
@click.pass_context
def ph_slope(ctx: click.Context) -> None:
    """Report pH probe health from the EZO-pH `Slope,?` command.

    Slope is the manufacturer's own end-of-life indicator: how closely the
    probe's calibrated response matched an ideal probe, plus how far its zero
    point sits from 0 mV. It is the way to decide whether a probe is worth
    reconditioning rather than reading a buffer and squinting at the number.

    Two things to know before trusting the answer:

    \b
    - Slope only updates when you calibrate. It reports the probe as of its
      last calibration, not as of now. Calibrate first, then read this.
    - A bad number can mean contaminated calibration solution rather than a
      bad probe. Use fresh solution before condemning anything.
    """
    from pi.drivers.ezo_ph import (
        OFFSET_DEGRADED_MV,
        OFFSET_HEALTHY_MV,
        SLOPE_HEALTHY_PERCENT,
        EZOPhDriver,
    )

    config: AppConfig = ctx.obj["config"]
    driver = EZOPhDriver(bus_number=config.i2c.bus)

    async def _go():
        try:
            if not await driver.is_available():
                return None, "no EZO-pH responding on the bus"
            return await driver.read_slope(), None
        finally:
            await driver.close()

    slope, error = _run_async(_go())

    if error:
        click.echo(f"Error: {error}")
        ctx.exit(1)
    if slope is None:
        click.echo("Error: no valid Slope response from the circuit")
        ctx.exit(1)

    click.echo(f"  acid slope   {slope.acid_percent:6.1f} %   "
               f"(healthy >= {SLOPE_HEALTHY_PERCENT:g})")
    click.echo(f"  base slope   {slope.base_percent:6.1f} %   "
               f"(healthy >= {SLOPE_HEALTHY_PERCENT:g})")
    click.echo(f"  zero offset  {slope.offset_mv:+6.2f} mV  "
               f"(healthy within +/-{OFFSET_HEALTHY_MV:g}, "
               f"degraded beyond +/-{OFFSET_DEGRADED_MV:g})")
    click.echo()

    verdict = slope.verdict
    if verdict == "uncalibrated":
        click.echo("  UNCALIBRATED — the circuit is reporting its pre-calibration")
        click.echo("  default (100, 100, 0). Run a 3-point calibration, then re-read.")
    elif verdict == "healthy":
        click.echo("  HEALTHY — within the datasheet's new-probe figures.")
    elif verdict == "marginal":
        click.echo("  MARGINAL — slope holds but the zero point has drifted.")
        click.echo("  Usable; watch it, and recalibrate more often.")
    else:
        click.echo("  FAILING — outside the datasheet's limits.")
        click.echo("  Recondition or replace. Confirm with fresh calibration")
        click.echo("  solution first: contaminated solution reads the same way.")




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
