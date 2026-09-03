"""End-to-end: the dashboard and the orchestrator agree through the database.

Everything else about the control channel is tested against mocks on one side
or the other. This is the test that exercises the actual claim — that a click
in a process which cannot see the hardware reaches a process which can, with
nothing shared but the SQLite file.

The two halves here stand in for the two systemd units: `growlab-dashboard`
(the FastAPI app, holding no service objects) and `growlab` (the orchestrator,
holding the fan and meter services and no web server).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from pi.config.schema import ControlConfig, SecurityConfig
from pi.dashboard.app import create_app
from pi.data.repository import SensorRepository
from pi.services.control import ControlService

ADMIN_PASSWORD = "test-admin-password"


@pytest.fixture
def security_config():
    return SecurityConfig(
        admin_password_sha256=hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest(),
        session_secret_key="x" * 48,
        rate_limit_admin="1000/minute",
    )


@pytest.fixture
async def dashboard_repo(test_config):
    """The dashboard process's own connection to the shared database."""
    repo = SensorRepository(test_config.system.db_path)
    await repo.connect()
    yield repo
    await repo.close()


@pytest.fixture
async def orchestrator_repo(test_config):
    """The orchestrator's own connection — a genuinely separate handle."""
    repo = SensorRepository(test_config.system.db_path)
    await repo.connect()
    yield repo
    await repo.close()


@pytest.fixture
async def web(dashboard_repo, security_config):
    """An authenticated admin client against a dashboard with no services."""
    app = create_app(
        dashboard_repo,
        control_config=ControlConfig(override_ttl_seconds=600.0),
        security_config=security_config,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/admin/login", data={"password": ADMIN_PASSWORD})
        assert login.status_code == 303
        yield client


@pytest.fixture
def fan():
    return MagicMock()


@pytest.fixture
def meters():
    return MagicMock()


@pytest.fixture
def orchestrator(orchestrator_repo, fan, meters):
    return ControlService(
        orchestrator_repo,
        ControlConfig(),
        fan_service=fan,
        meter_service=meters,
    )


class TestFanOverrideReachesTheHardware:
    async def test_click_reaches_the_fan(self, web, orchestrator, fan):
        response = await web.post("/api/fan/override", json={"duty": 35})
        assert response.status_code == 200

        await orchestrator.reconcile_once()
        fan.set_override.assert_called_once_with(35)

    async def test_returning_to_auto_reaches_the_fan(self, web, orchestrator, fan):
        await web.post("/api/fan/override", json={"duty": 35})
        await orchestrator.reconcile_once()

        await web.post("/api/fan/override", json={"mode": "auto"})
        await orchestrator.reconcile_once()
        fan.clear_override.assert_called_once()

    async def test_override_lapses_without_a_second_click(
        self, web, orchestrator, fan
    ):
        """The safety property, end to end: nobody has to remember to undo it."""
        await web.post("/api/fan/override", json={"duty": 0})
        await orchestrator.reconcile_once()
        fan.set_override.assert_called_once_with(0)

        later = datetime.now(timezone.utc) + timedelta(seconds=3600)
        await orchestrator.reconcile_once(now=later)
        fan.clear_override.assert_called_once()

    async def test_repeated_polls_do_not_restamp(self, web, orchestrator, fan):
        await web.post("/api/fan/override", json={"duty": 35})
        for _ in range(5):
            await orchestrator.reconcile_once()
        fan.set_override.assert_called_once_with(35)


class TestMeterOverrideReachesTheHardware:
    async def test_pinning_a_needle(self, web, orchestrator, meters):
        response = await web.post(
            "/api/meters/override", json={"meter": "ph", "deflection": -0.75}
        )
        assert response.status_code == 200

        await orchestrator.reconcile_once()
        meters.set_override.assert_called_once_with("ph", -0.75)

    async def test_releasing_a_needle(self, web, orchestrator, meters):
        await web.post(
            "/api/meters/override", json={"meter": "ec", "deflection": 1.0}
        )
        await orchestrator.reconcile_once()

        # The first reconcile also cleared "ph", which was never set — bringing
        # every control to a known state on startup is the point of reconciling.
        meters.clear_override.reset_mock()

        await web.post("/api/meters/override", json={"meter": "ec", "mode": "auto"})
        await orchestrator.reconcile_once()
        meters.clear_override.assert_called_once_with("ec")


class TestStateIsVisibleFromTheWeb:
    async def test_control_endpoint_reflects_the_override(self, web):
        await web.post("/api/fan/override", json={"duty": 80})
        controls = (await web.get("/api/control")).json()["controls"]
        assert controls["fan.override_duty"]["mode"] == "manual"
        assert controls["fan.override_duty"]["value"] == "80"
        assert controls["fan.override_duty"]["updated_by"] == "admin"

    async def test_meters_status_reports_the_pinned_needle(self, web):
        """A pinned needle must not be reported as following its sensor."""
        await web.post(
            "/api/meters/override", json={"meter": "ph", "deflection": 0.6}
        )
        data = (await web.get("/api/meters/status")).json()
        assert data["meters"]["ph"]["override"] == 0.6
        assert data["meters"]["ph"]["deflection"] == 0.6
        assert data["meters"]["ec"]["override"] is None


class TestOrchestratorRestart:
    async def test_override_survives_an_orchestrator_restart(
        self, web, orchestrator_repo, fan, meters
    ):
        """A fresh ControlService picks up state it never saw set."""
        await web.post("/api/fan/override", json={"duty": 55})

        restarted = ControlService(
            orchestrator_repo,
            ControlConfig(),
            fan_service=fan,
            meter_service=meters,
        )
        await restarted.reconcile_once()
        fan.set_override.assert_called_once_with(55)
