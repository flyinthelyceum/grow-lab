"""CLI commands for canopy fan control.

Bench helpers for the Noctua NF-A12x25 PWM fan on Pi hardware PWM
(GPIO18 by default). Useful during bring-up, before the fan is handed
over to FanService.

These commands drive the GPIO directly. If the `growlab` service is
running, FanService also owns that pin and will reassert its own duty
on its next tick, so stop the service first for a clean bench sweep:

    sudo systemctl stop growlab
"""

from __future__ import annotations

import click


def _driver(config):
    """Build a FanPWMDriver from the [fan] config block."""
    from pi.drivers.fan_pwm import FanPWMDriver

    fc = config.fan
    return FanPWMDriver(
        gpio_pin=fc.gpio_pin,
        frequency=fc.frequency,
        min_duty=fc.min_duty,
        max_duty=fc.max_duty,
        ramp_temp_low_f=fc.ramp_temp_low_f,
        ramp_temp_high_f=fc.ramp_temp_high_f,
    )


@click.group("fan")
def fan_group() -> None:
    """Canopy fan control commands."""


@fan_group.command("set")
@click.argument("duty", type=click.IntRange(0, 100))
@click.pass_context
def fan_set(ctx: click.Context, duty: int) -> None:
    """Set fan duty cycle (0-100). 0 is off."""
    config = ctx.obj["config"]
    fan = _driver(config)

    if not fan.is_available:
        click.echo("Error: GPIO PWM unavailable (RPi.GPIO not found)")
        ctx.exit(1)
        return

    if fan.set_duty(duty):
        actual = fan.duty_cycle
        if actual != duty:
            click.echo(f"Fan duty set to {actual}% (requested {duty}%, clamped)")
        else:
            click.echo(f"Fan duty set to {actual}%")
    else:
        click.echo("Error: failed to set fan duty")
        ctx.exit(1)


@fan_group.command("sweep")
@click.option("--dwell", type=click.FloatRange(0.5, 60.0), default=5.0,
              show_default=True, help="Seconds to hold each step.")
@click.pass_context
def fan_sweep(ctx: click.Context, dwell: float) -> None:
    """Step the fan 0-100% to verify PWM control and find the stall floor.

    Watch and listen at each step. If the fan buzzes or fails to spin at
    the lowest non-zero step, raise [fan] min_duty — the stall point
    varies unit to unit.
    """
    import time

    config = ctx.obj["config"]
    fan = _driver(config)

    if not fan.is_available:
        click.echo("Error: GPIO PWM unavailable (RPi.GPIO not found)")
        ctx.exit(1)
        return

    steps = [0, 20, 40, 60, 80, 100]
    click.echo(f"Sweeping GPIO{config.fan.gpio_pin} at {config.fan.frequency} Hz, "
               f"{dwell:g}s per step. Ctrl-C to stop.")
    try:
        for step in steps:
            if not fan.set_duty(step):
                click.echo(f"  {step:>3}% -> FAILED")
                continue
            click.echo(f"  {step:>3}% -> duty {fan.duty_cycle}%")
            time.sleep(dwell)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
    finally:
        fan.set_duty(0)
        fan.close()
        click.echo("Sweep complete; fan off and GPIO released.")


@fan_group.command("status")
@click.pass_context
def fan_status(ctx: click.Context) -> None:
    """Show fan config and the duty the temperature ramp would command."""
    import asyncio

    from pi.data.repository import SensorRepository
    from pi.drivers.fan_pwm import FanPWMDriver

    config = ctx.obj["config"]
    fc = config.fan

    click.echo(f"Enabled:   {fc.enabled}")
    click.echo(f"GPIO:      {fc.gpio_pin} @ {fc.frequency} Hz")
    click.echo(f"Duty span: {fc.min_duty}-{fc.max_duty}%")
    click.echo(f"Ramp:      {fc.ramp_temp_low_f:.0f}-{fc.ramp_temp_high_f:.0f}°F")

    async def _read():
        repo = SensorRepository(config.system.db_path)
        await repo.connect()
        try:
            return await repo.get_latest("bme280_temperature")
        finally:
            await repo.close()

    reading = asyncio.run(_read())

    if reading is None:
        click.echo("\nNo bme280_temperature reading — cannot compute target duty.")
        return

    temp_f = reading.value * 9.0 / 5.0 + 32.0
    duty = FanPWMDriver.static_duty_for_temperature(
        temp_f,
        min_duty=fc.min_duty,
        max_duty=fc.max_duty,
        ramp_low=fc.ramp_temp_low_f,
        ramp_high=fc.ramp_temp_high_f,
    )
    click.echo(f"\nAir temp:  {temp_f:.1f}°F")
    click.echo(f"Target:    {duty}% duty")
