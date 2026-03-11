"""Database CLI commands — info, export, and query tools."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from pi.config.schema import AppConfig


def _run_async(coro):
    """Run an async function from a sync Click command."""
    return asyncio.run(coro)


@click.group()
def db_group() -> None:
    """Database tools — info, export, query."""
    pass


@db_group.command(name="info")
@click.pass_context
def db_info(ctx: click.Context) -> None:
    """Show database status and row counts."""
    config: AppConfig = ctx.obj["config"]

    async def _info():
        from pi.data.repository import SensorRepository

        db_path = config.system.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        repo = SensorRepository(db_path)
        await repo.connect()

        info = await repo.get_db_info()
        sensor_ids = await repo.get_sensor_ids()

        click.echo(f"Database: {db_path}")
        click.echo(f"  sensor_readings: {info['sensor_readings']} rows")
        click.echo(f"  system_events:   {info['system_events']} rows")
        click.echo(f"  camera_captures: {info['camera_captures']} rows")

        if sensor_ids:
            click.echo(f"\nSensors with data: {', '.join(sensor_ids)}")

            for sid in sensor_ids:
                count = await repo.count_readings(sid)
                latest = await repo.get_latest(sid)
                latest_str = (
                    f"{latest.value} {latest.unit} @ {latest.iso_timestamp}"
                    if latest
                    else "none"
                )
                click.echo(f"  {sid}: {count} readings, latest: {latest_str}")

        await repo.close()

    _run_async(_info())


@db_group.command(name="export")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json"]),
    default="csv",
    help="Export format",
)
@click.option("--sensor", "sensor_id", default=None, help="Filter by sensor ID")
@click.option("--limit", default=1000, help="Max rows to export")
@click.option("--output", "output_path", default=None, help="Output file path")
@click.option(
    "--type",
    "data_type",
    type=click.Choice(["readings", "events"]),
    default="readings",
    help="Data type to export",
)
@click.pass_context
def db_export(
    ctx: click.Context,
    fmt: str,
    sensor_id: str | None,
    limit: int,
    output_path: str | None,
    data_type: str,
) -> None:
    """Export sensor data to CSV or JSON."""
    config: AppConfig = ctx.obj["config"]

    async def _export():
        from pi.data.export import (
            events_to_csv,
            events_to_json,
            readings_to_csv,
            readings_to_json,
        )
        from pi.data.repository import SensorRepository

        repo = SensorRepository(config.system.db_path)
        await repo.connect()

        if data_type == "readings":
            readings = await repo.get_all_readings(limit=limit)
            if sensor_id:
                readings = [r for r in readings if r.sensor_id == sensor_id]
            content = readings_to_csv(readings) if fmt == "csv" else readings_to_json(readings)
        else:
            events = await repo.get_events(limit=limit)
            content = events_to_csv(events) if fmt == "csv" else events_to_json(events)

        if output_path:
            Path(output_path).write_text(content)
            click.echo(f"Exported to {output_path}")
        else:
            click.echo(content)

        await repo.close()

    _run_async(_export())


@db_group.command(name="init")
@click.pass_context
def db_init(ctx: click.Context) -> None:
    """Initialize the database (create tables)."""
    config: AppConfig = ctx.obj["config"]

    async def _init():
        from pi.data.repository import SensorRepository

        db_path = config.system.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        repo = SensorRepository(db_path)
        await repo.connect()
        await repo.close()
        click.echo(f"Database initialized at {db_path}")

    _run_async(_init())
