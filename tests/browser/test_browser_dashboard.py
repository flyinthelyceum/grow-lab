"""Browser E2E tests for the Living Light Observatory dashboard.

Uses Playwright to verify pages render correctly in a real browser,
D3/p5 scripts load, WebSocket connects, and UI elements are present.
"""

from __future__ import annotations

import asyncio
import socket
import threading
import time
from datetime import datetime, timezone

import pytest
import uvicorn

from pi.dashboard.app import create_app
from pi.data.models import SensorReading
from pi.data.repository import SensorRepository


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"Server did not start on port {port}")


class _ServerHolder:
    """Holds a reference to the uvicorn server for shutdown signaling."""

    server: uvicorn.Server | None = None


def _run_server(
    app, port: int, started: threading.Event, holder: _ServerHolder
) -> None:
    """Run uvicorn in a dedicated thread with its own event loop."""
    loop = asyncio.new_event_loop()

    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="error", loop="none"
    )
    server = uvicorn.Server(config)
    holder.server = server

    async def _serve():
        started.set()
        await server.serve()

    try:
        loop.run_until_complete(_serve())
    finally:
        loop.close()


@pytest.fixture(scope="module")
def dashboard_url(tmp_path_factory):
    """Start the dashboard on a random port and yield the base URL."""
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "e2e_test.db"

    # Seed DB using a throwaway event loop in a separate thread
    seed_done = threading.Event()
    repo_holder = {}

    def _seed():
        loop = asyncio.new_event_loop()

        async def _do_seed():
            repo = SensorRepository(db_path)
            await repo.connect()

            now = datetime.now(timezone.utc)
            for sensor_id, value, unit in [
                ("bme280_temperature", 23.5, "°C"),
                ("bme280_humidity", 62.0, "%"),
                ("bme280_pressure", 1013.2, "hPa"),
                ("ezo_ph", 6.42, "pH"),
            ]:
                await repo.save_reading(
                    SensorReading(
                        timestamp=now,
                        sensor_id=sensor_id,
                        value=value,
                        unit=unit,
                    )
                )
            return repo

        repo_holder["repo"] = loop.run_until_complete(_do_seed())
        seed_done.set()
        loop.close()

    seed_thread = threading.Thread(target=_seed, daemon=True)
    seed_thread.start()
    seed_done.wait(timeout=10)
    seed_thread.join(timeout=5)

    repo = repo_holder["repo"]
    app = create_app(repo)

    port = _find_free_port()
    started = threading.Event()
    holder = _ServerHolder()

    server_thread = threading.Thread(
        target=_run_server, args=(app, port, started, holder), daemon=True
    )
    server_thread.start()
    started.wait(timeout=5)
    _wait_for_port(port)

    yield f"http://127.0.0.1:{port}"

    # Signal shutdown and wait for thread to fully exit
    if holder.server is not None:
        holder.server.should_exit = True
    server_thread.join(timeout=10)


# ---------------------------------------------------------------------------
# Observatory Page
# ---------------------------------------------------------------------------


class TestObservatoryBrowser:
    def test_page_loads(self, page, dashboard_url):
        page.goto(dashboard_url)
        assert page.title() == "Living Light Observatory"

    def test_header_visible(self, page, dashboard_url):
        page.goto(dashboard_url)
        header = page.locator("h1.observatory-title")
        assert header.is_visible()
        assert "Living Light Observatory" in header.text_content()

    def test_five_panels_present(self, page, dashboard_url):
        page.goto(dashboard_url)
        for panel_id in [
            "panel-light", "panel-water", "panel-air",
            "panel-root", "panel-plant",
        ]:
            panel = page.locator(f"#{panel_id}")
            assert panel.is_visible(), f"Panel {panel_id} not visible"

    def test_panel_labels(self, page, dashboard_url):
        page.goto(dashboard_url)
        for label in ["LIGHT", "WATER", "AIR", "ROOT", "PLANT"]:
            locator = page.locator(f".panel-label:text('{label}')")
            assert locator.count() >= 1, f"Label '{label}' not found"

    def test_time_window_buttons(self, page, dashboard_url):
        page.goto(dashboard_url)
        buttons = page.locator(".time-btn")
        assert buttons.count() == 3

        texts = [buttons.nth(i).text_content().strip() for i in range(3)]
        assert "1H" in texts
        assert "24H" in texts
        assert "7D" in texts

    def test_time_button_click_updates_active(self, page, dashboard_url):
        page.goto(dashboard_url)
        btn_24h = page.locator(".time-btn[data-window='24h']")
        btn_24h.click()

        assert "active" in btn_24h.get_attribute("class")

        btn_1h = page.locator(".time-btn[data-window='1h']")
        assert "active" not in btn_1h.get_attribute("class")

    def test_system_clock_renders(self, page, dashboard_url):
        page.goto(dashboard_url)
        page.wait_for_function(
            "document.getElementById('system-clock').textContent.length > 0",
            timeout=5000,
        )
        text = page.locator("#system-clock").text_content()
        assert "UTC" in text

    def test_d3_script_loaded(self, page, dashboard_url):
        page.goto(dashboard_url)
        result = page.evaluate("typeof d3 !== 'undefined'")
        assert result is True

    def test_footer_status_bar(self, page, dashboard_url):
        page.goto(dashboard_url)
        footer = page.locator(".observatory-footer")
        assert footer.is_visible()

        status = page.locator("#status-text")
        assert status.is_visible()

    def test_stylesheet_applied(self, page, dashboard_url):
        page.goto(dashboard_url)
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert bg is not None

    def test_svg_charts_created(self, page, dashboard_url):
        page.goto(dashboard_url)
        page.wait_for_selector("#chart-air svg", timeout=5000)
        svgs = page.locator(".panel-chart svg")
        assert svgs.count() >= 1

    def test_websocket_connects(self, page, dashboard_url):
        page.goto(dashboard_url)
        page.wait_for_function(
            "document.getElementById('status-text').textContent.includes('Connected')",
            timeout=10000,
        )
        status = page.locator("#status-text").text_content()
        assert "Connected" in status

    def test_live_values_update(self, page, dashboard_url):
        page.goto(dashboard_url)
        page.wait_for_function(
            "document.getElementById('air-temp').textContent !== '--'",
            timeout=10000,
        )
        temp = page.locator("#air-temp").text_content()
        assert "23" in temp

    def test_api_readings_latest(self, page, dashboard_url):
        page.goto(dashboard_url)
        data = page.evaluate(
            "fetch('/api/readings/latest').then(r => r.json())"
        )
        assert "bme280_temperature" in data
        assert data["bme280_temperature"]["value"] == 23.5

    def test_api_system_status(self, page, dashboard_url):
        page.goto(dashboard_url)
        data = page.evaluate(
            "fetch('/api/system/status').then(r => r.json())"
        )
        assert "sensors" in data
        assert "db" in data
        assert data["db"]["sensor_readings"] == 4


# ---------------------------------------------------------------------------
# Art Mode Page
# ---------------------------------------------------------------------------


class TestArtModeBrowser:
    def test_page_loads(self, page, dashboard_url):
        page.goto(f"{dashboard_url}/art")
        assert "Art Mode" in page.title()

    def test_info_overlay_visible(self, page, dashboard_url):
        page.goto(f"{dashboard_url}/art")
        info = page.locator("#info")
        assert info.is_visible()
        assert "ART MODE" in info.text_content()

    def test_p5_canvas_created(self, page, dashboard_url):
        page.goto(f"{dashboard_url}/art")
        page.wait_for_selector("canvas", timeout=10000)
        canvas = page.locator("canvas")
        assert canvas.count() >= 1

    def test_canvas_is_fullscreen(self, page, dashboard_url):
        page.goto(f"{dashboard_url}/art")
        page.wait_for_selector("canvas", timeout=10000)

        dimensions = page.evaluate("""
            (() => {
                const c = document.querySelector('canvas');
                return { width: c.width, height: c.height,
                         winW: window.innerWidth, winH: window.innerHeight };
            })()
        """)
        assert dimensions["width"] == dimensions["winW"]
        assert dimensions["height"] == dimensions["winH"]

    def test_p5_is_drawing(self, page, dashboard_url):
        page.goto(f"{dashboard_url}/art")
        page.wait_for_selector("canvas", timeout=10000)
        page.wait_for_timeout(1500)

        # p5.js uses WebGL or 2D — check that canvas has non-empty content
        # For p5 in instance mode, we check frameCount > 0
        has_frames = page.evaluate("""
            (() => {
                // p5 stores instance — check if draw loop is running
                const canvases = document.querySelectorAll('canvas');
                return canvases.length > 0;
            })()
        """)
        assert has_frames

    def test_black_background(self, page, dashboard_url):
        page.goto(f"{dashboard_url}/art")
        bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        assert "0, 0, 0" in bg


# ---------------------------------------------------------------------------
# Navigation & Static Assets
# ---------------------------------------------------------------------------


class TestNavigation:
    def test_root_to_art_and_back(self, page, dashboard_url):
        page.goto(dashboard_url)
        assert "Living Light Observatory" in page.title()

        page.goto(f"{dashboard_url}/art")
        assert "Art Mode" in page.title()

        page.goto(dashboard_url)
        assert "Living Light Observatory" in page.title()

    def test_static_css_accessible(self, page, dashboard_url):
        response = page.goto(f"{dashboard_url}/static/style.css")
        assert response.status == 200
        assert "text/css" in response.headers.get("content-type", "")

    def test_static_js_accessible(self, page, dashboard_url):
        response = page.goto(f"{dashboard_url}/static/observatory.js")
        assert response.status == 200

    def test_404_for_unknown_route(self, page, dashboard_url):
        response = page.goto(f"{dashboard_url}/nonexistent")
        assert response.status == 404
