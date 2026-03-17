/**
 * GROWLAB — Art Mode Controller
 *
 * Full-screen generative visualization driven by live sensor data.
 * Currently renders: Radial Thermal Ring (AIR subsystem).
 *
 * Data pipeline:
 *   1. Fetch 24h downsampled history on load
 *   2. WebSocket for live value updates
 *   3. Re-fetch history every 5 minutes to keep ring current
 *
 * Uses Canvas 2D via art-core.js AnimationLoop (30fps, Visibility API).
 * D3 for math only — no SVG rendering.
 */

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    // --- State ---
    var loop = null;
    var ring = null;
    var ws = null;
    var canvas = null;

    // --- Temperature conversion ---
    function cToF(c) { return c * 9 / 5 + 32; }

    // --- API ---
    function fetchJSON(url) {
        return fetch(url).then(function (r) { return r.json(); });
    }

    function fetchHistory() {
        return fetchJSON("/api/readings/bme280_temperature/downsampled?window=24h");
    }

    // --- Load history into ring ---
    function loadHistory() {
        fetchHistory()
            .then(function (readings) {
                if (!readings || readings.length === 0) return;

                // Convert to Fahrenheit at display boundary
                var converted = readings.map(function (d) {
                    return {
                        timestamp: d.timestamp,
                        value: (d.unit === "°F") ? d.value : cToF(d.value),
                        unit: "°F",
                    };
                });

                ring.update(converted);
            })
            .catch(function (err) {
                console.error("Art: failed to fetch history", err);
            });
    }

    // --- WebSocket for live values ---
    function connectWS() {
        var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        var url = protocol + "//" + window.location.host + "/ws/updates";

        ws = new WebSocket(url);

        ws.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                if (data.readings) {
                    data.readings.forEach(function (r) {
                        if (r.sensor_id === "bme280_temperature") {
                            ring.setLiveValue(cToF(r.value));
                        }
                    });
                }
            } catch (e) {
                // Ignore parse errors
            }
        };

        ws.onclose = function () {
            setTimeout(connectWS, 5000);
        };

        ws.onerror = function () {
            ws.close();
        };

        // Request updates every 3s
        setInterval(function () {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send("update");
            }
        }, 3000);
    }

    // --- Resize handler ---
    function onResize() {
        if (ring) {
            ring.resize();
        }
    }

    // --- Init ---
    function init() {
        canvas = document.getElementById("art-canvas");
        if (!canvas) return;

        // Create radial ring renderer
        ring = Art.createRadialRing(canvas);

        // Start animation loop
        loop = new Art.AnimationLoop();
        loop.register(function (dt, now) {
            ring.render(dt, now);
        });

        // Load initial data
        loadHistory();

        // Re-fetch history every 5 minutes
        setInterval(loadHistory, 300000);

        // Connect WebSocket for live updates
        connectWS();

        // Handle window resize
        window.addEventListener("resize", onResize);
    }

    // Start when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }

})();
