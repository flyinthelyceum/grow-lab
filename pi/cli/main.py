"""CLI entry point for the Living Light System.

Usage: growlab [OPTIONS] COMMAND [ARGS]
"""

from __future__ import annotations

import click

from pi.cli.camera_control import camera_group
from pi.cli.dashboard_cmd import dashboard_cmd
from pi.cli.db_tools import db_group
from pi.cli.display_cmd import display_group
from pi.cli.light_control import light_group
from pi.cli.pump_control import pump_group
from pi.cli.sensor_test import sensor_group


@click.group()
@click.option(
    "--config",
    "config_path",
    default=None,
    type=click.Path(exists=False),
    help="Path to config.toml (default: ./config.toml)",
)
@click.pass_context
def cli(ctx: click.Context, config_path: str | None) -> None:
    """Living Light System — grow lab control software."""
    from pathlib import Path

    from pi.config.loader import load_config

    path = Path(config_path) if config_path else None
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(path)


@cli.command()
@click.pass_context
def start(ctx: click.Context) -> None:
    """Start the Living Light System (polling + data logging)."""
    from pi.main import start as _start

    _start(config_path=None)  # Config already loaded but start() reloads for signal handling


cli.add_command(camera_group, name="camera")
cli.add_command(dashboard_cmd, name="dashboard")
cli.add_command(db_group, name="db")
cli.add_command(display_group, name="display")
cli.add_command(light_group, name="light")
cli.add_command(pump_group, name="pump")
cli.add_command(sensor_group, name="sensor")
