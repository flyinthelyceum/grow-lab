"""CLI commands for lighting control.

Provides manual light adjustment and status display.
"""

from __future__ import annotations

import click


@click.group("light")
def light_group() -> None:
    """Lighting control commands."""


@light_group.command("set")
@click.argument("pwm", type=click.IntRange(0, 255))
@click.pass_context
def light_set(ctx: click.Context, pwm: int) -> None:
    """Set LED brightness (0-255)."""
    import asyncio

    from pi.data.repository import SensorRepository
    from pi.drivers.esp32_serial import ESP32Serial
    from pi.services.lighting import LightingScheduler

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

    async def _set() -> None:
        repo = SensorRepository(config.system.db_path)
        await repo.connect()
        try:
            scheduler = LightingScheduler(esp32, repo, config.lighting)
            await scheduler.set_manual(pwm)
            click.echo(f"Light PWM set to {pwm}")
        finally:
            await repo.close()
            esp32.close()

    asyncio.run(_set())


@light_group.command("status")
@click.pass_context
def light_status(ctx: click.Context) -> None:
    """Show current light status from ESP32."""
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
        response = esp32.get_status()
        if response.ok:
            data = response.data
            click.echo(f"PWM:    {data.get('pwm', '?')}")
            click.echo(f"Pump:   {'ON' if data.get('pump') else 'OFF'}")
            click.echo(f"Uptime: {data.get('uptime', '?')}s")
        else:
            click.echo(f"Error: {response.error}")
    finally:
        esp32.close()


@light_group.command("schedule")
@click.pass_context
def light_schedule(ctx: click.Context) -> None:
    """Show the current lighting schedule configuration."""
    config = ctx.obj["config"]
    lc = config.lighting

    click.echo(f"Mode:      {lc.mode}")
    click.echo(f"On hour:   {lc.on_hour:02d}:00")
    click.echo(f"Off hour:  {lc.off_hour:02d}:00")
    click.echo(f"Intensity: {lc.intensity}")
    click.echo(f"Ramp:      {lc.ramp_minutes} min")

    from datetime import time

    from pi.services.lighting import _is_light_on, compute_ramp_intensity

    from pi.services.lighting import _time_now
    now = _time_now()
    on = _is_light_on(lc, now)
    target = compute_ramp_intensity(lc, now)

    click.echo(f"\nCurrent:   {'ON' if on else 'OFF'} (PWM {target})")
