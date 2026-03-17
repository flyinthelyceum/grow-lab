"""Database CLI commands — info, export, and query tools."""

from __future__ import annotations

import asyncio
import math
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


@db_group.command(name="seed-demo")
@click.option("--hours", default=24, type=int, help="History window to seed")
@click.option(
    "--reset/--no-reset",
    default=True,
    help="Clear existing readings/events/captures before seeding",
)
@click.pass_context
def db_seed_demo(ctx: click.Context, hours: int, reset: bool) -> None:
    """Seed the database with synthetic dashboard-friendly demo data."""
    config: AppConfig = ctx.obj["config"]

    async def _seed() -> None:
        from datetime import datetime, timedelta, timezone

        from PIL import Image, ImageDraw

        from pi.data.models import CameraCapture, SensorReading, SystemEvent
        from pi.data.repository import SensorRepository

        db_path = config.system.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        repo = SensorRepository(db_path)
        await repo.connect()

        if reset:
            await repo.db.execute("DELETE FROM sensor_readings")
            await repo.db.execute("DELETE FROM system_events")
            await repo.db.execute("DELETE FROM camera_captures")
            await repo.db.commit()

        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        start = now - timedelta(hours=max(hours, 1))
        steps = max(hours * 2, 2)  # 30 min cadence
        interval = (now - start) / (steps - 1)

        for idx in range(steps):
            timestamp = start + interval * idx
            phase = (idx / max(steps - 1, 1)) * math.pi * 2

            values = {
                "light_pwm": 0 if idx < steps * 0.18 or idx > steps * 0.84 else 200,
                "bme280_temperature": 22.0 + math.sin(phase - 0.3) * 2.4,
                "bme280_humidity": 49.0 + math.sin(phase + 0.8) * 9.0,
                "bme280_pressure": 976.0 + math.cos(phase * 0.7) * 5.5,
                "ezo_ph": 6.15 + math.sin(phase * 0.8) * 0.18,
                "ezo_ec": 1180.0 + math.cos(phase * 0.9) * 180.0,
                "soil_moisture": 58.0 + math.sin(phase * 1.3) * 11.0,
                "ds18b20_temperature": 20.2 + math.sin(phase * 0.6) * 0.8,
            }

            units = {
                "light_pwm": "PWM",
                "bme280_temperature": "°C",
                "bme280_humidity": "%",
                "bme280_pressure": "hPa",
                "ezo_ph": "pH",
                "ezo_ec": "µS/cm",
                "soil_moisture": "%",
                "ds18b20_temperature": "°C",
            }

            for sensor_id, value in values.items():
                await repo.save_reading(
                    SensorReading(
                        timestamp=timestamp,
                        sensor_id=sensor_id,
                        value=round(value, 3),
                        unit=units[sensor_id],
                    )
                )

        event_hours = (2, 8, 14, 20)
        for day_offset in range(2):
            base_day = (now - timedelta(days=1 - day_offset)).date()
            for hour in event_hours:
                event_time = datetime(
                    base_day.year,
                    base_day.month,
                    base_day.day,
                    hour,
                    0,
                    tzinfo=timezone.utc,
                )
                if start <= event_time <= now:
                    await repo.save_event(
                        SystemEvent(
                            timestamp=event_time,
                            event_type="irrigation",
                            description="Demo irrigation pulse",
                        )
                    )

        image_dir = config.camera.output_dir
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "demo-capture.jpg"
        image = Image.new("RGB", (1280, 720), color=(18, 28, 24))
        draw = ImageDraw.Draw(image)
        draw.rectangle((80, 80, 1200, 640), outline=(60, 180, 140), width=4)
        draw.ellipse((430, 160, 850, 580), fill=(52, 108, 74), outline=(122, 210, 168), width=5)
        draw.text((100, 100), "GROWLAB DEMO CAPTURE", fill=(210, 240, 230))
        draw.text((100, 132), now.strftime("%Y-%m-%d %H:%M UTC"), fill=(150, 190, 176))
        image.save(image_path, format="JPEG", quality=88)

        await repo.save_capture(
            CameraCapture(
                timestamp=now - timedelta(minutes=7),
                filepath=str(image_path),
                filesize_bytes=image_path.stat().st_size,
            )
        )

        await repo.close()
        click.echo(f"Seeded demo data into {db_path}")
        click.echo(f"History window: {hours}h")
        click.echo(f"Camera demo image: {image_path}")

    _run_async(_seed())
