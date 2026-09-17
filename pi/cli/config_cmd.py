"""CLI commands for inspecting the loaded configuration.

The targets this prints used to be written into three documents and a set of
module constants, and the four had drifted apart. They are computed from one
place now, which is only an improvement if there is a way to see what that
place currently says without opening the TOML and doing the arithmetic.
"""

from __future__ import annotations

import click


@click.group("config")
def config_group() -> None:
    """Configuration inspection commands."""


def _band(low: float, high: float, unit: str = "") -> str:
    return f"{low:g}{unit} to {high:g}{unit}"


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Print the targets the station is actually holding to."""
    config = ctx.obj["config"]
    path = ctx.obj.get("config_path")
    r = config.reservoir

    click.echo(f"config: {path or 'defaults (no file)'}")
    click.echo("")
    click.echo("reservoir")
    click.echo(f"  pH target      {r.ph_target:g}")
    click.echo(f"    warning      {_band(r.ph_warning_low, r.ph_warning_high)}")
    click.echo(f"    critical     {_band(r.ph_critical_low, r.ph_critical_high)}")
    click.echo(f"  EC target      {r.ec_target_us:g} uS/cm")
    click.echo(f"    warning      {_band(r.ec_warning_low_us, r.ec_warning_high_us, ' uS/cm')}")
    click.echo(f"    critical     {_band(r.ec_critical_low_us, r.ec_critical_high_us, ' uS/cm')}")
    if r.source_water_ec_us is None:
        click.echo("  source water   NOT MEASURED")
        click.echo("                 Recalibrate the EC probe in range first, then")
        click.echo("                 measure -- V1_GO_LIVE_RUNBOOK.md D.0. Until then")
        click.echo("                 nothing has checked the target is reachable.")
    else:
        headroom = r.ec_target_us - r.source_water_ec_us
        click.echo(f"  source water   {r.source_water_ec_us:g} uS/cm")
        click.echo(f"                 {headroom:g} uS/cm of headroom to the target")

    click.echo("")
    click.echo("meters (centres are derived from the targets above)")
    click.echo(f"  pH centre      {config.meters.ph.centre:g}  span +/-{config.meters.ph.span:g}")
    click.echo(
        f"  EC centre      {config.meters.ec.centre:g} mS/cm  "
        f"span +/-{config.meters.ec.span:g} mS/cm"
    )

    click.echo("")
    click.echo("lighting")
    lc = config.lighting
    click.echo(f"  photoperiod    {lc.on_hour:02d}:00 to {lc.off_hour:02d}:00")
    if lc.fixture_above_media_in is None:
        click.echo("  fixture height NOT RECORDED")
        click.echo("                 The AS7341 reads output and distance as one")
        click.echo("                 number, so its readings are not comparable")
        click.echo("                 across sessions until this is set.")
    else:
        click.echo(f"  fixture height {lc.fixture_above_media_in:g} in above media")
