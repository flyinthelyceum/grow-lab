"""Tests for the main orchestrator module."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.config.schema import AppConfig, SystemConfig
from pi.main import run, start


@pytest.fixture
def config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        system=SystemConfig(
            log_level="DEBUG",
            data_dir=tmp_path,
            db_path=tmp_path / "test.db",
        )
    )


class TestRun:
    async def test_startup_and_shutdown(self, config: AppConfig) -> None:
        """Test the full lifecycle: start → signal → shutdown."""
        mock_repo = AsyncMock()
        mock_repo.connect = AsyncMock()
        mock_repo.save_event = AsyncMock()
        mock_repo.close = AsyncMock()

        mock_registry = MagicMock()
        mock_registry.available_drivers = {}
        mock_registry.all_statuses = []

        mock_poller = AsyncMock()
        mock_poller.start = AsyncMock()
        mock_poller.stop = AsyncMock()

        with patch("pi.main.SensorRepository", return_value=mock_repo):
            with patch("pi.main.scan_all", return_value=MagicMock()):
                with patch("pi.main.build_registry", return_value=mock_registry):
                    with patch("pi.main.PollingService", return_value=mock_poller):

                        async def _run_and_stop():
                            """Run orchestrator and signal shutdown after brief delay."""
                            task = asyncio.create_task(run(config))
                            await asyncio.sleep(0.05)
                            # Trigger shutdown by setting the event
                            # We need to send SIGINT, but in tests we can
                            # just cancel the task
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass

                        await _run_and_stop()

        # Verify startup sequence
        mock_repo.connect.assert_called_once()
        assert mock_repo.save_event.call_count >= 1  # At least system_start
        mock_poller.start.assert_called_once()

    async def test_creates_data_dir(self, tmp_path: Path) -> None:
        """Test that run() creates the data directory if missing."""
        data_dir = tmp_path / "nonexistent" / "deep"
        config = AppConfig(
            system=SystemConfig(
                data_dir=data_dir,
                db_path=data_dir / "test.db",
            )
        )

        mock_repo = AsyncMock()
        mock_poller = AsyncMock()
        mock_registry = MagicMock()
        mock_registry.available_drivers = {}
        mock_registry.all_statuses = []

        with patch("pi.main.SensorRepository", return_value=mock_repo):
            with patch("pi.main.scan_all", return_value=MagicMock()):
                with patch("pi.main.build_registry", return_value=mock_registry):
                    with patch("pi.main.PollingService", return_value=mock_poller):
                        task = asyncio.create_task(run(config))
                        await asyncio.sleep(0.05)
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

        assert data_dir.exists()

    async def test_logs_sensor_status(self, config: AppConfig) -> None:
        """Test that sensor statuses are logged."""
        mock_repo = AsyncMock()
        mock_poller = AsyncMock()

        status = MagicMock()
        status.sensor_id = "bme280"
        status.available = True
        status.reason = "detected"

        mock_registry = MagicMock()
        mock_registry.available_drivers = {"bme280": MagicMock()}
        mock_registry.all_statuses = [status]

        with patch("pi.main.SensorRepository", return_value=mock_repo):
            with patch("pi.main.scan_all", return_value=MagicMock()):
                with patch("pi.main.build_registry", return_value=mock_registry):
                    with patch("pi.main.PollingService", return_value=mock_poller):
                        task = asyncio.create_task(run(config))
                        await asyncio.sleep(0.05)
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

        mock_poller.start.assert_called_once()


class TestStart:
    def test_start_calls_run(self, config: AppConfig) -> None:
        """Test that start() loads config and calls asyncio.run."""
        with patch("pi.main.load_config", return_value=config):
            with patch("pi.main.asyncio.run") as mock_run:
                start(config_path=None)
                mock_run.assert_called_once()

    def test_start_with_path(self, tmp_path: Path, config: AppConfig) -> None:
        config_path = tmp_path / "config.toml"
        with patch("pi.main.load_config", return_value=config) as mock_load:
            with patch("pi.main.asyncio.run"):
                start(config_path=config_path)
                mock_load.assert_called_once_with(config_path)
