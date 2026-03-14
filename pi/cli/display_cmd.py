"""CLI commands for the OLED display."""

from __future__ import annotations

import click


@click.group("display")
def display_group() -> None:
    """OLED display control commands."""


@display_group.command("test")
@click.pass_context
def display_test(ctx: click.Context) -> None:
    """Show a test pattern on the OLED display."""
    config = ctx.obj["config"]

    from pi.drivers.oled_ssd1306 import OLEDDriver

    oled = OLEDDriver(address=config.display.address, controller=config.display.controller)

    if not oled.is_available:
        click.echo("OLED display not detected")
        return

    oled.clear()
    oled.draw_text(0, 0, "LIVING LIGHT", size=12)
    oled.draw_text(0, 16, "Observatory", size=10)
    oled.draw_bar(0, 32, 120, 8, fill=0.75)
    oled.draw_sparkline(0, 46, 120, 16, [1, 3, 2, 5, 4, 6, 3, 7, 5, 8])
    oled.show()
    click.echo("Test pattern displayed")


@display_group.command("clear")
@click.pass_context
def display_clear(ctx: click.Context) -> None:
    """Clear the OLED display."""
    config = ctx.obj["config"]

    from pi.drivers.oled_ssd1306 import OLEDDriver

    oled = OLEDDriver(address=config.display.address, controller=config.display.controller)
    oled.clear()
    oled.show()
    click.echo("Display cleared")


@display_group.command("status")
@click.pass_context
def display_status(ctx: click.Context) -> None:
    """Show OLED display configuration and availability."""
    config = ctx.obj["config"]

    from pi.drivers.oled_ssd1306 import OLEDDriver

    click.echo(f"Enabled:  {config.display.enabled}")
    click.echo(f"Address:  0x{config.display.address:02X}")

    oled = OLEDDriver(address=config.display.address, controller=config.display.controller)
    click.echo(f"Available: {oled.is_available}")
    oled.close()
