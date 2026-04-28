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
    let alertTimeline = null;

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
        light: ["as7341_lux", "light_pwm"],
        air_temp: ["bme280_temperature"],
        air_humidity: ["bme280_humidity"],
        air_pressure: ["bme280_pressure"],
        root_ph: ["ezo_ph"],
        root_ec: ["ezo_ec"],
        root_temp: ["ds18b20_temperature"],
        soil_moisture: ["soil_moisture"],
    };

    function isLightOn(value) {
        return value > 0;
    }

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
        return fetchJSON("/api/readings/" + sensorId + "/downsampled?window=" + (window || currentWindow));
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
                setText("water-value", irrigationEvents.length ? irrigationEvents.length : "--");
                setText("water-count", irrigationEvents.length + " pulses / " + currentWindow.toUpperCase());
                var el = document.getElementById("water-last");
                if (el && irrigationEvents.length > 0) {
                    var lastTime = new Date(irrigationEvents[0].timestamp);
                    el.textContent = "Last: " + formatTime(lastTime) + " (" + timeAgo(lastTime) + ")";
                    setText("water-note", "Recent irrigation cadence visible");
                } else {
                    setText("water-note", "No irrigation events in window");
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
            if (r.sensor_id === "as7341_lux") {
                var lux = Math.round(r.value);
                setText("light-value", lux);
                setText("light-unit", "lx");
                setText("light-mode", lux > 50 ? "Photoperiod active" : "Lights idle");
                setText("light-schedule", lux > 50 ? "Canopy receiving light" : "Awaiting next cycle");
                setText("light-note", lux > 50 ? "Active growth window" : "Dark interval in effect");
            } else if (r.sensor_id === "light_pwm") {
                var pwm = Math.round(r.value);
                // Only update if no lux sensor is providing data
                var unitEl = document.getElementById("light-unit");
                if (!unitEl || unitEl.textContent !== "lx") {
                    setText("light-value", pwm);
                    setText("light-unit", "PWM");
                    setText("light-mode", isLightOn(pwm) ? "Photoperiod active" : "Lights idle");
                    setText("light-schedule", isLightOn(pwm) ? "Driver command active" : "Awaiting next cycle");
                    setText("light-note", isLightOn(pwm) ? "Active growth window (no lux sensor)" : "Dark interval in effect");
                }
            }
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
                if (r.value < 40) {
                    setText("plant-moisture-band", "Lower moisture band — ready for the next watering window");
                } else if (r.value > 70) {
                    setText("plant-moisture-band", "Upper moisture band — media still holding water");
                } else {
                    setText("plant-moisture-band", "Mid moisture band — root zone looks balanced");
                }
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

    // Remove img and .camera-placeholder from #camera-feed, preserving
    // controls like the live-stream toggle button and LIVE badge.
    function clearCameraContent(container) {
        var nodes = Array.prototype.slice.call(container.childNodes);
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            if (node.nodeType !== 1) continue;
            if (node.tagName === "IMG" ||
                (node.classList && node.classList.contains("camera-placeholder"))) {
                container.removeChild(node);
            }
        }
    }

    function renderCameraPlaceholder(title, detail) {
        var container = document.getElementById("camera-feed");
        if (!container) return;

        clearCameraContent(container);

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

    // --- Alert banner ---
    function showAlert(alert) {
        var banner = document.getElementById("alert-banner");
        var text = document.getElementById("alert-text");
        if (!banner || !text) return;

        var level = alert.event_type === "alert_critical" ? "CRITICAL" : "WARNING";
        text.textContent = level + ": " + alert.description;
        banner.className = "alert-banner alert-" + (alert.event_type === "alert_critical" ? "critical" : "warning");
        banner.style.display = "flex";
    }

    // --- Fan status ---
    function refreshFanStatus() {
        fetchJSON("/api/fan/status").then(function (data) {
            if (!data || !data.enabled) {
                setText("air-fan", "Fan: off");
                return;
            }
            if (data.duty_percent !== null) {
                setText("air-fan", "Fan: " + data.duty_percent + "% @ " + data.temp_f + "°F");
            } else {
                setText("air-fan", "Fan: no temp data");
            }
        }).catch(function () {});
    }

    // --- Image gallery ---
    function refreshGallery() {
        fetchJSON("/api/images?limit=6").then(function (images) {
            var strip = document.getElementById("gallery-strip");
            if (!strip) return;

            while (strip.firstChild) strip.removeChild(strip.firstChild);

            var available = (images || []).filter(function (img) {
                return img.available && img.url;
            });

            if (available.length === 0) {
                var empty = document.createElement("div");
                empty.className = "gallery-empty";
                empty.textContent = "No captures yet";
                strip.appendChild(empty);
                return;
            }

            available.forEach(function (img) {
                var thumb = document.createElement("img");
                thumb.src = img.url;
                thumb.alt = img.filename;
                thumb.className = "gallery-thumb";
                thumb.title = formatDateTime(new Date(img.timestamp));
                thumb.addEventListener("click", function () {
                    openLightbox(img.url, img.filename, img.timestamp);
                });
                strip.appendChild(thumb);
            });
        }).catch(function () {});
    }

    // --- Lightbox ---
    function openLightbox(url, filename, timestamp) {
        // Remove existing lightbox if any
        var existing = document.getElementById("gallery-lightbox");
        if (existing) existing.remove();

        var overlay = document.createElement("div");
        overlay.id = "gallery-lightbox";
        overlay.className = "lightbox-overlay";
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) overlay.remove();
        });

        var wrap = document.createElement("div");
        wrap.className = "lightbox-wrap";

        var img = document.createElement("img");
        img.src = url;
        img.alt = filename;
        img.className = "lightbox-img";
        wrap.appendChild(img);

        var caption = document.createElement("div");
        caption.className = "lightbox-caption";
        caption.textContent = formatDateTime(new Date(timestamp));
        wrap.appendChild(caption);

        var close = document.createElement("button");
        close.className = "lightbox-close";
        close.textContent = "CLOSE";
        close.addEventListener("click", function () { overlay.remove(); });
        wrap.appendChild(close);

        overlay.appendChild(wrap);
        document.body.appendChild(overlay);
    }

    // --- Alert timeline ---
    function refreshAlertTimeline() {
        if (!alertTimeline) return;
        fetchJSON("/api/alerts?limit=100").then(function (alerts) {
            alertTimeline.update(alerts || []);
        }).catch(function () {});
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
                setText("camera-chip", "CAMERA STANDBY");
                setText("plant-capture-time", "No captures logged yet");
                return;
            }

            var captureTime = new Date(data.timestamp);
            setText("camera-chip", "LATEST CAPTURE");
            setText("plant-capture-time", formatDateTime(captureTime) + " (" + timeAgo(captureTime) + ")");

            if (!data.available || !data.url) {
                renderCameraPlaceholder("CAPTURE LOGGED", "Image metadata exists, but the file is not available from this dashboard host.");
                setText("camera-chip", "CAPTURE LOGGED");
                return;
            }

            var container = document.getElementById("camera-feed");
            if (container) {
                clearCameraContent(container);
                var img = document.createElement("img");
                img.src = data.url;
                img.alt = "Latest capture";
                img.title = "Click to enlarge";
                img.addEventListener("click", function () {
                    openLightbox(data.url, data.filename, data.timestamp);
                });
                // Insert image as the first child so toggle button + badge
                // (positioned: absolute) stay layered on top.
                container.insertBefore(img, container.firstChild);
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
                // Server-push alert (from ConnectionManager broadcast)
                if (data.type === "alert") {
                    showAlert(data.alert);
                    return;
                }
                // Standard poll response
                if (data.readings) {
                    updateValues(data.readings);
                }
                if (data.alerts && data.alerts.length > 0) {
                    showAlert(data.alerts[0]);
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
        setInterval(refreshFanStatus, 30000);
        setInterval(refreshGallery, 60000);
        setInterval(refreshAlertTimeline, 60000);

        // Request WS update every 3s
        setInterval(function () {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send("update");
            }
        }, 3000);
    }

    // --- Live webcam toggle (admin only) ---
    var liveState = {
        active: false,
        endsAt: null,
        countdownTimer: null,
        previousSrc: null,
    };

    function isAdminFlag() {
        return document.body && document.body.dataset.isAdmin === "true";
    }

    function initLiveToggle() {
        // Public visitors get this too — the endpoint is rate-limited and
        // single-concurrency (see /api/stream/live).
        var btn = document.getElementById("camera-live-toggle");
        if (!btn) return;
        btn.addEventListener("click", function () {
            if (liveState.active) {
                stopLive("user_stopped");
            } else {
                startLive();
            }
        });
    }

    function startLive() {
        if (liveState.active) return;
        var container = document.getElementById("camera-feed");
        if (!container) return;
        var img = container.querySelector("img");
        if (!img) {
            // No static image yet (camera standby); inject one for the stream.
            img = document.createElement("img");
            img.alt = "Live feed";
            container.appendChild(img);
        }
        liveState.previousSrc = img.src;
        // Cache-bust param so the browser opens a fresh streaming connection.
        img.src = "/api/stream/live?t=" + Date.now();
        liveState.active = true;
        liveState.endsAt = Date.now() + 30000;

        var btn = document.getElementById("camera-live-toggle");
        if (btn) {
            btn.classList.add("camera-live-toggle-active");
            btn.textContent = "STOP";
        }
        showLiveBadge();
        liveState.countdownTimer = setInterval(updateCountdown, 250);
    }

    function stopLive(reason) {
        if (!liveState.active) return;
        liveState.active = false;
        if (liveState.countdownTimer) {
            clearInterval(liveState.countdownTimer);
            liveState.countdownTimer = null;
        }
        var container = document.getElementById("camera-feed");
        if (container) {
            var img = container.querySelector("img");
            if (img && liveState.previousSrc) {
                img.src = liveState.previousSrc;
            }
        }
        liveState.previousSrc = null;
        var btn = document.getElementById("camera-live-toggle");
        if (btn) {
            btn.classList.remove("camera-live-toggle-active");
            btn.textContent = "GO LIVE";
        }
        hideLiveBadge();
        // After expiry, refresh latest capture (reason=="expired" or "user_stopped").
        if (reason !== "user_stopped") {
            setTimeout(refreshImage, 200);
        }
    }

    function showLiveBadge() {
        var badge = document.getElementById("camera-live-badge");
        if (!badge) return;
        badge.hidden = false;
        updateCountdown();
    }

    function hideLiveBadge() {
        var badge = document.getElementById("camera-live-badge");
        if (!badge) return;
        badge.hidden = true;
        badge.textContent = "";
    }

    function updateCountdown() {
        var remaining = Math.max(0, liveState.endsAt - Date.now());
        var seconds = Math.ceil(remaining / 1000);
        var badge = document.getElementById("camera-live-badge");
        if (badge) {
            badge.textContent = "● LIVE — " + seconds + "s";
        }
        if (remaining <= 0) {
            stopLive("expired");
        }
    }

    // --- Init ---
    document.addEventListener("DOMContentLoaded", function () {
        initCharts();

        // Initialize soil moisture gauge
        if (window.GrowLab && window.GrowLab.createSoilGauge) {
            soilGauge = window.GrowLab.createSoilGauge("soil-moisture-gauge");
        }

        // Initialize alert timeline
        if (window.GrowLab && window.GrowLab.createAlertTimeline) {
            alertTimeline = window.GrowLab.createAlertTimeline("chart-alert-timeline");
        }

        refreshAllCharts();
        refreshStatus();
        refreshImage();
        refreshFanStatus();
        refreshGallery();
        refreshAlertTimeline();
        connectWS();
        startPolling();
        initLiveToggle();

        // CSP-safe alert-dismiss binding (was an inline onclick attribute,
        // blocked by script-src 'self').
        var alertDismiss = document.getElementById("alert-dismiss");
        if (alertDismiss) {
            alertDismiss.addEventListener("click", function () {
                var banner = document.getElementById("alert-banner");
                if (banner) banner.style.display = "none";
            });
        }
    });
})();
