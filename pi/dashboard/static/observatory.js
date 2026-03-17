/**
 * GROWLAB — Frontend Controller
 *
 * Manages: WebSocket connection, per-subsystem D3 chart renderers,
 * time window selection, and live value updates.
 *
 * Chart renderers loaded from /static/charts/*.js via window.GrowLab namespace.
 * Design: Calm, scientific. 1-5s update cadence. No jitter.
 */

(function () {
    "use strict";

    // --- State ---
    let currentWindow = "24h";
    let ws = null;
    let charts = {};
    let soilGauge = null;

    // --- Temperature conversion ---
    function cToF(c) { return c * 9 / 5 + 32; }

    // --- Time formatting (12h local, human-readable) ---
    function formatTime(date) {
        return date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    }

    function formatDateTime(date) {
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
            + " " + formatTime(date);
    }

    function timeAgo(date) {
        var diff = Math.floor((Date.now() - date.getTime()) / 1000);
        if (diff < 60) return "just now";
        if (diff < 3600) return Math.floor(diff / 60) + "m ago";
        if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
        return Math.floor(diff / 86400) + "d ago";
    }

    // --- Sensor ID mapping ---
    const SENSOR_MAP = {
        light: ["bme280_light", "light_pwm"],
        air_temp: ["bme280_temperature"],
        air_humidity: ["bme280_humidity"],
        air_pressure: ["bme280_pressure"],
        root_ph: ["ezo_ph"],
        root_ec: ["ezo_ec"],
        root_temp: ["ds18b20_temperature"],
        soil_moisture: ["soil_moisture"],
    };

    function hasSensor(sensorIds, expectedIds) {
        return expectedIds.some(function (expectedId) {
            return sensorIds.some(function (sensorId) {
                if (expectedId === "ds18b20_temperature") {
                    return sensorId === expectedId || sensorId.indexOf("ds18b20_") === 0;
                }
                return sensorId === expectedId;
            });
        });
    }

    // Sensor IDs that contain temperature values (stored as °C, display as °F)
    const TEMP_SENSORS = new Set([
        "bme280_temperature",
        "ds18b20_temperature",
    ]);

    // --- Optimal ranges ---
    // Each range: [criticalLow, warningLow, warningHigh, criticalHigh]
    // Values inside warningLow–warningHigh = normal
    // Values in warning zone = amber drift indicator
    // Values beyond critical = red alert
    const RANGES = {
        air_temp:       [60, 65, 80, 85],       // °F
        air_humidity:   [30, 40, 70, 80],        // %
        root_ph:        [5.0, 5.8, 6.5, 7.5],   // pH
        root_ec:        [400, 800, 1600, 2000],  // µS/cm
        root_temp:      [55, 60, 75, 80],        // °F
        soil_moisture:  [20, 40, 70, 85],        // %
    };

    // Returns "normal", "warning", or "critical"
    function classify(rangeKey, value) {
        var r = RANGES[rangeKey];
        if (!r) return "normal";
        if (value < r[0] || value > r[3]) return "critical";
        if (value < r[1] || value > r[2]) return "warning";
        return "normal";
    }

    // Apply range status to a DOM element
    function setRangeStatus(el, status) {
        if (!el) return;
        el.classList.remove("range-normal", "range-warning", "range-critical");
        el.classList.add("range-" + status);
    }

    // --- Clock ---
    function updateClock() {
        const el = document.getElementById("system-clock");
        if (el) {
            const now = new Date();
            el.textContent = now.toLocaleDateString("en-US", {
                weekday: "short", month: "short", day: "numeric"
            }) + "  " + formatTime(now);
        }
    }
    setInterval(updateClock, 1000);
    updateClock();

    // --- Time window ---
    document.querySelectorAll(".time-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            document.querySelectorAll(".time-btn").forEach(function (b) {
                b.classList.remove("active");
            });
            btn.classList.add("active");
            currentWindow = btn.dataset.window;
            refreshAllCharts();
        });
    });

    // --- API helpers ---
    function fetchJSON(url) {
        return fetch(url).then(function (r) { return r.json(); });
    }

    function apiReadings(sensorId, window) {
        return fetchJSON("/api/readings/" + sensorId + "?window=" + (window || currentWindow));
    }

    function apiStatus() {
        return fetchJSON("/api/system/status");
    }

    function apiLatestImage() {
        return fetchJSON("/api/images/latest");
    }

    // --- Initialize charts ---
    function initCharts() {
        // Per-subsystem renderers (each returns { update(...) })
        if (window.GrowLab.createLightChart) {
            charts.light = window.GrowLab.createLightChart("chart-light");
        }
        if (window.GrowLab.createWaterTimeline) {
            charts.water = window.GrowLab.createWaterTimeline("chart-water");
        }
        if (window.GrowLab.createAirChart) {
            charts.air = window.GrowLab.createAirChart("chart-air");
        }
        if (window.GrowLab.createRootChart) {
            charts.root = window.GrowLab.createRootChart("chart-root");
        }
    }

    // --- Refresh chart data ---
    function fetchSensorData(sensorIds) {
        // Try each sensor ID until one returns data
        return new Promise(function (resolve) {
            var tryNext = function (ids, idx) {
                if (idx >= ids.length) { resolve([]); return; }
                apiReadings(ids[idx]).then(function (data) {
                    if (data && data.length > 0) {
                        if (TEMP_SENSORS.has(ids[idx])) {
                            data = data.map(function (d) {
                                return { timestamp: d.timestamp, value: cToF(d.value), unit: "°F", sensor_id: d.sensor_id };
                            });
                        }
                        resolve(data);
                    } else {
                        tryNext(ids, idx + 1);
                    }
                }).catch(function () { tryNext(ids, idx + 1); });
            };
            tryNext(sensorIds, 0);
        });
    }

    function refreshAllCharts() {
        // LIGHT — single sensor, step area
        if (charts.light) {
            fetchSensorData(SENSOR_MAP.light).then(function (data) {
                charts.light.update(data);
            });
        }

        // WATER — irrigation events as pulse timeline
        if (charts.water) {
            fetchJSON("/api/events?limit=50").then(function (events) {
                var irrigationEvents = (events || []).filter(function (e) {
                    return e.event_type === "irrigation";
                });
                charts.water.update(irrigationEvents);
                var el = document.getElementById("water-last");
                if (el && irrigationEvents.length > 0) {
                    var lastTime = new Date(irrigationEvents[0].timestamp);
                    el.textContent = "Last: " + formatTime(lastTime) + " (" + timeAgo(lastTime) + ")";
                }
            }).catch(function () {});
        }

        // AIR — dual fetch: temperature + humidity
        if (charts.air) {
            Promise.all([
                fetchSensorData(SENSOR_MAP.air_temp),
                fetchSensorData(SENSOR_MAP.air_humidity)
            ]).then(function (results) {
                charts.air.update(results[0], results[1]);
            });
        }

        // ROOT — dual fetch: pH + EC
        if (charts.root) {
            Promise.all([
                fetchSensorData(SENSOR_MAP.root_ph),
                fetchSensorData(SENSOR_MAP.root_ec)
            ]).then(function (results) {
                charts.root.update(results[0], results[1]);
            });
        }
    }

    // --- Update live values from latest readings ---
    function updateValues(readings) {
        // readings is an array of {sensor_id, value, unit}
        readings.forEach(function (r) {
            if (r.sensor_id === "bme280_temperature") {
                var tempF = cToF(r.value);
                setText("air-temp", tempF.toFixed(1));
                setRangeStatus(document.getElementById("air-temp"), classify("air_temp", tempF));
            }
            if (r.sensor_id === "bme280_humidity") {
                setText("air-humidity", "Humidity: " + r.value.toFixed(0) + "%");
                setRangeStatus(document.getElementById("air-humidity"), classify("air_humidity", r.value));
            }
            if (r.sensor_id === "bme280_pressure") {
                setText("air-pressure", "Pressure: " + r.value.toFixed(0) + " hPa");
            }
            if (r.sensor_id === "ezo_ph") {
                setText("root-ph", r.value.toFixed(2));
                setRangeStatus(document.getElementById("root-ph"), classify("root_ph", r.value));
            }
            if (r.sensor_id === "ezo_ec") {
                setText("root-ec", "EC: " + r.value.toFixed(0) + " µS/cm");
                setRangeStatus(document.getElementById("root-ec"), classify("root_ec", r.value));
            }
            if (r.sensor_id === "ds18b20_temperature" || r.sensor_id.startsWith("ds18b20_")) {
                var rootTempF = cToF(r.value);
                setText("root-temp", "Temp: " + rootTempF.toFixed(1) + "°F");
                setRangeStatus(document.getElementById("root-temp"), classify("root_temp", rootTempF));
            }
            if (r.sensor_id === "soil_moisture") {
                setText("soil-moisture-value", r.value.toFixed(0));
                setRangeStatus(document.getElementById("soil-moisture-value"), classify("soil_moisture", r.value));
                if (soilGauge) soilGauge.update(r.value);
            }
        });
    }

    function setText(id, text) {
        var el = document.getElementById(id);
        if (!el) return;
        if (el.textContent === text) return;
        el.textContent = text;
        // Pulse animation for panel values
        if (el.classList.contains("panel-value")) {
            el.classList.add("updating");
            setTimeout(function () { el.classList.remove("updating"); }, 400);
        }
    }

    function renderCameraPlaceholder(title, detail) {
        var container = document.getElementById("camera-feed");
        if (!container) return;

        while (container.firstChild) {
            container.removeChild(container.firstChild);
        }

        var wrap = document.createElement("div");
        wrap.className = "camera-placeholder";

        var titleEl = document.createElement("div");
        titleEl.className = "camera-placeholder-title";
        titleEl.textContent = title;
        wrap.appendChild(titleEl);

        var detailEl = document.createElement("div");
        detailEl.className = "camera-placeholder-detail";
        detailEl.textContent = detail;
        wrap.appendChild(detailEl);

        container.appendChild(wrap);
    }

    function updateAvailabilityNotes(sensorIds, captureCount) {
        var rootStates = [];
        if (!hasSensor(sensorIds, SENSOR_MAP.root_ph)) rootStates.push("pH pending");
        if (!hasSensor(sensorIds, SENSOR_MAP.root_ec)) rootStates.push("EC pending");
        if (!hasSensor(sensorIds, SENSOR_MAP.root_temp)) rootStates.push("reservoir probe pending");
        setText("root-note", rootStates.length ? rootStates.join(" • ") : "All ROOT sensors live");

        if (!hasSensor(sensorIds, SENSOR_MAP.root_ec)) {
            setText("root-ec", "EC sensor pending");
        }
        if (!hasSensor(sensorIds, SENSOR_MAP.root_temp)) {
            setText("root-temp", "Reservoir probe pending");
        }

        var soilLive = hasSensor(sensorIds, SENSOR_MAP.soil_moisture);
        if (!soilLive) {
            setText("plant-note", captureCount > 0 ? "Camera live. Soil probe pending." : "Camera waiting. Soil probe pending.");
        } else {
            setText("plant-note", captureCount > 0 ? "Camera and soil telemetry live." : "Soil telemetry live. Camera waiting for first capture.");
        }
    }

    // --- System status ---
    function refreshStatus() {
        apiStatus().then(function (data) {
            var sensorIds = data.sensors || [];
            var db = data.db || {};
            var captureCount = db.camera_captures || 0;

            setText("sensor-count", sensorIds.length + " sensors");
            setText("db-readings", (db.sensor_readings || 0) + " readings");
            setText("plant-count", captureCount + " captures");
            updateAvailabilityNotes(sensorIds, captureCount);
        }).catch(function () {});
    }

    // --- Latest image ---
    function refreshImage() {
        apiLatestImage().then(function (data) {
            if (!data || !data.filename) {
                renderCameraPlaceholder("CAMERA STANDBY", "Waiting for the next logged capture.");
                setText("plant-capture-time", "No captures logged yet");
                return;
            }

            var captureTime = new Date(data.timestamp);
            setText("plant-capture-time", formatDateTime(captureTime) + " (" + timeAgo(captureTime) + ")");

            if (!data.available || !data.url) {
                renderCameraPlaceholder("CAPTURE LOGGED", "Image metadata exists, but the file is not available from this dashboard host.");
                return;
            }

            var container = document.getElementById("camera-feed");
            if (container) {
                while (container.firstChild) {
                    container.removeChild(container.firstChild);
                }
                var img = document.createElement("img");
                img.src = data.url;
                img.alt = "Latest capture";
                container.appendChild(img);
            }
        }).catch(function () {});
    }

    // --- WebSocket ---
    function connectWS() {
        var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        var url = protocol + "//" + window.location.host + "/ws/updates";

        ws = new WebSocket(url);

        ws.onopen = function () {
            setText("status-text", "Connected");
            var indicator = document.getElementById("ws-status");
            if (indicator) {
                indicator.classList.add("connected");
                indicator.classList.remove("disconnected");
            }
        };

        ws.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                if (data.readings) {
                    updateValues(data.readings);
                }
            } catch (e) {
                console.error("WS parse error:", e);
            }
        };

        ws.onclose = function () {
            setText("status-text", "Disconnected — reconnecting...");
            var indicator = document.getElementById("ws-status");
            if (indicator) {
                indicator.classList.remove("connected");
                indicator.classList.add("disconnected");
            }
            // Reconnect after 5s
            setTimeout(connectWS, 5000);
        };

        ws.onerror = function () {
            ws.close();
        };
    }

    // --- Periodic refresh ---
    function startPolling() {
        // Refresh charts every 30s, status every 10s, image every 60s
        setInterval(refreshAllCharts, 30000);
        setInterval(refreshStatus, 10000);
        setInterval(refreshImage, 60000);

        // Request WS update every 3s
        setInterval(function () {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send("update");
            }
        }, 3000);
    }

    // --- Init ---
    document.addEventListener("DOMContentLoaded", function () {
        initCharts();

        // Initialize soil moisture gauge
        if (window.GrowLab && window.GrowLab.createSoilGauge) {
            soilGauge = window.GrowLab.createSoilGauge("soil-moisture-gauge");
        }

        refreshAllCharts();
        refreshStatus();
        refreshImage();
        connectWS();
        startPolling();
    });
})();
