"""CLI commands for the front-panel meters.

Bench service mode for the two centre-zero Weston movements: centre them,
step them to known deflections, and sweep them end to end. Use these to set
mechanical zero, check polarity, and gather the five-point calibration data
that `[meters.ph] calibration` and `[meters.ec] calibration` hold.

These drive the DAC directly. If the `growlab` service is running it also
owns the DAC and will reassert its own codes, so stop it first:

    sudo systemctl stop growlab

Series resistors, not this tool, are what keep a movement safe — no command
here can exceed what the hardware allows. See docs/BOM.md.
"""

from __future__ import annotations

import click

_METERS = ("ph", "ec")


def _open_dac(ctx: click.Context):
    """Connect to the DAC, or exit with a message."""
    from pi.drivers.mcp4728 import MCP4728

    config = ctx.obj["config"]
    dac = MCP4728(bus_number=config.i2c.bus, address=config.meters.i2c_address)
    if not dac.connect():
        click.echo(
            f"Error: no MCP4728 on i2c-{config.i2c.bus} at "
            f"0x{config.meters.i2c_address:02x}"
        )
        ctx.exit(1)
    return dac, config


def _channel_config(config, meter: str):
    return config.meters.ph if meter == "ph" else config.meters.ec


def _apply(dac, config, meter: str, x: float) -> tuple[int, int]:
    """Write one needle to a normalised deflection, leaving the other alone."""
    from pi.drivers.mcp4728 import differential_codes

    cc = _channel_config(config, meter)
    commanded = -x if cc.invert else x
    pos, neg = differential_codes(
        commanded, midpoint=cc.midpoint_code, span_counts=cc.span_counts
    )
    index = {"A": 0, "B": 1, "C": 2, "D": 3}
    codes = list(dac.codes)
    codes[index[cc.dac_positive]] = pos
    codes[index[cc.dac_negative]] = neg
    dac.write_all(tuple(codes))
    return pos, neg


@click.group("meter")
def meter_group() -> None:
    """Front-panel meter commands."""


@meter_group.command("centre")
@click.pass_context
def meter_centre(ctx: click.Context) -> None:
    """Drive both needles to mechanical centre and hold."""
    dac, _ = _open_dac(ctx)
    try:
        if dac.centre_all():
            click.echo("Both needles at centre (all channels at midpoint).")
        else:
            click.echo("Error: write failed")
            ctx.exit(1)
    finally:
        pass  # leave centred; do not close, which would rewrite


@meter_group.command("set")
@click.argument("meter", type=click.Choice(_METERS))
@click.argument("deflection", type=click.FloatRange(-1.0, 1.0))
@click.pass_context
def meter_set(ctx: click.Context, meter: str, deflection: float) -> None:
    """Hold one needle at a deflection: -1.0 left, 0 centre, +1.0 right."""
    dac, config = _open_dac(ctx)
    pos, neg = _apply(dac, config, meter, deflection)
    cc = _channel_config(config, meter)
    value = cc.centre + deflection * cc.span
    click.echo(
        f"{meter}: {deflection:+.3f} → {cc.dac_positive}={pos} {cc.dac_negative}={neg} "
        f"(reads {value:.3f})"
    )


@meter_group.command("sweep")
@click.argument("meter", type=click.Choice(_METERS))
@click.option("--dwell", type=click.FloatRange(0.2, 30.0), default=2.0,
              show_default=True, help="Seconds to hold each step.")
@click.pass_context
def meter_sweep(ctx: click.Context, meter: str, dwell: float) -> None:
    """Step a needle through the calibration points and back to centre.

    Read the dial at each step and record what the needle actually shows.
    Those readings are the (commanded, actual) pairs for `calibration`.
    """
    import time

    dac, config = _open_dac(ctx)
    steps = (-1.0, -0.5, 0.0, 0.5, 1.0)

    click.echo(f"Sweeping {meter}, {dwell:g}s per step. Ctrl-C to stop.")
    try:
        for x in steps:
            _apply(dac, config, meter, x)
            click.echo(f"  commanded {x:+.2f} — read the dial")
            time.sleep(dwell)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
    finally:
        _apply(dac, config, meter, 0.0)
        click.echo("Returned to centre.")


@meter_group.command("save-centre")
@click.confirmation_option(
    prompt="Write midpoint codes to the DAC's EEPROM power-on defaults?"
)
@click.pass_context
def meter_save_centre(ctx: click.Context) -> None:
    """Store centre as the power-on state, so needles never boot into a stop.

    One-time commissioning step. EEPROM endurance is finite — this is not for
    routine use.
    """
    from pi.drivers.mcp4728 import MIDPOINT_CODE

    dac, _ = _open_dac(ctx)
    if dac.write_eeprom_defaults((MIDPOINT_CODE,) * 4):
        click.echo(
            f"EEPROM defaults set to midpoint ({MIDPOINT_CODE}) on all four channels. "
            "Needles will centre at power-up."
        )
    else:
        click.echo("Error: EEPROM write failed")
        ctx.exit(1)


@meter_group.command("status")
@click.pass_context
def meter_status(ctx: click.Context) -> None:
    """Show meter config and where each needle would sit right now."""
    import asyncio

    from pi.data.repository import SensorRepository
    from pi.services.meters import normalise

    config = ctx.obj["config"]
    mc = config.meters

    click.echo(f"Enabled:  {mc.enabled}")
    click.echo(f"DAC:      0x{mc.i2c_address:02x} on i2c-{config.i2c.bus}")
    click.echo(f"Motion:   {mc.update_hz} Hz, tau {mc.time_constant_seconds:g}s")
    click.echo(f"Sampling: every {mc.sample_interval_seconds:g}s, "
               f"fault after {mc.fault_timeout_seconds:g}s")

    async def _latest(sensor_id: str):
        repo = SensorRepository(config.system.db_path)
        await repo.connect()
        try:
            return await repo.get_latest(sensor_id)
        finally:
            await repo.close()

    for meter in _METERS:
        cc = _channel_config(config, meter)
        click.echo(f"\n{meter.upper()}  {cc.dac_positive}/{cc.dac_negative}  "
                   f"centre {cc.centre:g} span ±{cc.span:g}")
        reading = asyncio.run(_latest(cc.sensor_id))
        if reading is None:
            click.echo(f"  no {cc.sensor_id} reading — needle would sit at centre")
            continue
        value = reading.value * cc.scale
        x = normalise(value, cc.centre, cc.span)
        click.echo(f"  {cc.sensor_id} = {value:.3f} → deflection {x:+.3f}")
