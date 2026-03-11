"""CLI commands for camera control.

Provides manual capture, image listing, and timelapse assembly.
"""

from __future__ import annotations

import click


@click.group("camera")
def camera_group() -> None:
    """Camera capture commands."""


@camera_group.command("capture")
@click.pass_context
def camera_capture(ctx: click.Context) -> None:
    """Take a single image capture."""
    import asyncio

    from pi.data.repository import SensorRepository
    from pi.drivers.camera import CameraDriver
    from pi.services.camera_capture import CameraCaptureService

    config = ctx.obj["config"]

    camera = CameraDriver(resolution=config.camera.resolution)
    if not camera.is_available:
        click.echo("Error: No camera detected")
        ctx.exit(1)
        return

    async def _capture() -> None:
        repo = SensorRepository(config.system.db_path)
        await repo.connect()
        try:
            service = CameraCaptureService(camera, repo, config.camera)
            result = await service.capture_now()
            if result:
                click.echo(f"Captured: {result.filepath}")
                if result.filesize_bytes:
                    click.echo(f"Size: {result.filesize_bytes:,} bytes")
            else:
                click.echo("Capture failed")
        finally:
            await repo.close()
            camera.close()

    asyncio.run(_capture())


@camera_group.command("list")
@click.option("--limit", "-n", default=10, help="Number of recent captures to show")
@click.pass_context
def camera_list(ctx: click.Context, limit: int) -> None:
    """List recent camera captures from the database."""
    import asyncio

    from pi.data.repository import SensorRepository

    config = ctx.obj["config"]

    async def _list() -> None:
        repo = SensorRepository(config.system.db_path)
        await repo.connect()
        try:
            captures = await repo.get_captures(limit=limit)
            if not captures:
                click.echo("No captures found")
                return
            click.echo(f"Recent captures ({len(captures)}):")
            for c in captures:
                size = f"{c.filesize_bytes:,}B" if c.filesize_bytes else "?"
                click.echo(f"  {c.iso_timestamp}  {size}  {c.filepath}")
        finally:
            await repo.close()

    asyncio.run(_list())


@camera_group.command("status")
@click.pass_context
def camera_status(ctx: click.Context) -> None:
    """Show camera availability and configuration."""
    config = ctx.obj["config"]

    from pi.drivers.camera import CameraDriver

    click.echo(f"Enabled:    {config.camera.enabled}")
    click.echo(f"Interval:   {config.camera.interval_seconds}s")
    click.echo(f"Resolution: {config.camera.resolution[0]}x{config.camera.resolution[1]}")
    click.echo(f"Output dir: {config.camera.output_dir}")

    camera = CameraDriver(resolution=config.camera.resolution)
    available = camera.is_available
    click.echo(f"Available:  {available}")
    camera.close()
