"""CLI commands for pump/irrigation control.

Provides manual pump pulses and schedule display.
"""

from __future__ import annotations

import click


@click.group("pump")
def pump_group() -> None:
    """Pump and irrigation control commands."""


@pump_group.command("pulse")
@click.argument("duration", type=click.IntRange(1, 120), default=10)
@click.pass_context
def pump_pulse(ctx: click.Context, duration: int) -> None:
    """Run a single pump pulse (default 10s, max clamped by config)."""
    import asyncio

    from pi.data.repository import SensorRepository
    from pi.drivers.esp32_serial import ESP32Serial
    from pi.services.irrigation import IrrigationService

    config = ctx.obj["config"]

    esp32 = ESP32Serial(
        port=config.serial.port,
        baud=config.serial.baud,
        timeout=config.serial.timeout,
    )

    if not esp32.connect():
        click.echo("Error: Could not connect to ESP32")
        ctx.exit(1)
        return

    async def _pulse() -> None:
        repo = SensorRepository(config.system.db_path)
        await repo.connect()
        try:
            service = IrrigationService(esp32, repo, config.irrigation)
            effective = min(duration, config.irrigation.max_runtime_seconds)
            click.echo(f"Pump pulse: {effective}s...")
            ok = await service.pulse(duration)
            if ok:
                click.echo("Pump pulse complete")
            else:
                click.echo("Pump pulse blocked (cooldown period)")
        finally:
            await repo.close()
            esp32.close()

    asyncio.run(_pulse())


@pump_group.command("on")
@click.option("--max-seconds", default=60, type=click.IntRange(1, 300),
              help="Auto-shutoff after N seconds (default 60, max 300)")
@click.pass_context
def pump_on(ctx: click.Context, max_seconds: int) -> None:
    """Turn the pump on with auto-shutoff safety (default 60s)."""
    import time as _time

    config = ctx.obj["config"]

    from pi.drivers.esp32_serial import ESP32Serial

    esp32 = ESP32Serial(
        port=config.serial.port,
        baud=config.serial.baud,
        timeout=config.serial.timeout,
    )

    if not esp32.connect():
        click.echo("Error: Could not connect to ESP32")
        ctx.exit(1)
        return

    try:
        response = esp32.set_pump(True)
        if response.ok:
            click.echo(f"Pump ON (auto-shutoff in {max_seconds}s — Ctrl+C to stop early)")
            try:
                _time.sleep(max_seconds)
            except KeyboardInterrupt:
                click.echo("\nInterrupted")
        else:
            click.echo(f"Error: {response.error}")
            return
    finally:
        esp32.set_pump(False)
        esp32.close()
        click.echo("Pump OFF")


@pump_group.command("off")
@click.pass_context
def pump_off(ctx: click.Context) -> None:
    """Turn the pump off."""
    config = ctx.obj["config"]

    from pi.drivers.esp32_serial import ESP32Serial

    esp32 = ESP32Serial(
        port=config.serial.port,
        baud=config.serial.baud,
        timeout=config.serial.timeout,
    )

    if not esp32.connect():
        click.echo("Error: Could not connect to ESP32")
        ctx.exit(1)
        return

    try:
        response = esp32.set_pump(False)
        if response.ok:
            click.echo("Pump OFF")
        else:
            click.echo(f"Error: {response.error}")
    finally:
        esp32.close()


@pump_group.command("schedule")
@click.pass_context
def pump_schedule(ctx: click.Context) -> None:
    """Show the current irrigation schedule."""
    config = ctx.obj["config"]
    ic = config.irrigation

    click.echo(f"Max runtime:    {ic.max_runtime_seconds}s")
    click.echo(f"Min interval:   {ic.min_interval_minutes} min")
    click.echo(f"Relay GPIO:     {ic.relay_gpio}")
    click.echo(f"\nScheduled pulses ({len(ic.schedules)}):")
    for i, s in enumerate(ic.schedules, 1):
        click.echo(f"  {i}. {s.hour:02d}:{s.minute:02d} — {s.duration_seconds}s")
