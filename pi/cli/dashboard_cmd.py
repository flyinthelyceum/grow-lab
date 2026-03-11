"""CLI command for launching the Living Light Observatory dashboard."""

from __future__ import annotations

import click


@click.command("dashboard")
@click.option("--host", default="127.0.0.1", help="Bind address (use 0.0.0.0 for network access)")
@click.option("--port", default=8000, type=int, help="Port number")
@click.pass_context
def dashboard_cmd(ctx: click.Context, host: str, port: int) -> None:
    """Launch the Living Light Observatory dashboard."""
    import asyncio

    from pi.data.repository import SensorRepository
    from pi.dashboard.app import create_app

    config = ctx.obj["config"]

    async def _serve() -> None:
        import uvicorn

        repo = SensorRepository(config.system.db_path)
        await repo.connect()

        app = create_app(repo)

        server_config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(server_config)

        click.echo(f"Living Light Observatory → http://{host}:{port}")
        try:
            await server.serve()
        finally:
            await repo.close()

    asyncio.run(_serve())
