/**
 * Living Light Observatory — Frontend Controller
 *
 * Manages: WebSocket connection, D3.js waveform charts,
 * time window selection, and live value updates.
 *
 * Design: Calm, scientific. 1-5s update cadence. No jitter.
 */

(function () {
    "use strict";

    // --- State ---
    let currentWindow = "24h";
    let ws = null;
    let charts = {};

    // --- Sensor ID mapping ---
    const SENSOR_MAP = {
        light: ["bme280_light", "light_pwm"],
        air_temp: ["bme280_temperature"],
        air_humidity: ["bme280_humidity"],
        air_pressure: ["bme280_pressure"],
        root_ph: ["ezo_ph"],
        root_ec: ["ezo_ec"],
        root_temp: ["ds18b20_temperature"],
    };

    // --- Clock ---
    function updateClock() {
        const el = document.getElementById("system-clock");
        if (el) {
            const now = new Date();
            el.textContent = now.toISOString().replace("T", " ").slice(0, 19) + " UTC";
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

    function apiLatest() {
        return fetchJSON("/api/readings/latest");
    }

    function apiStatus() {
        return fetchJSON("/api/system/status");
    }

    function apiLatestImage() {
        return fetchJSON("/api/images/latest");
    }

    // --- D3 Waveform Chart ---
    function createWaveform(containerId, color) {
        var container = document.getElementById(containerId);
        if (!container) return null;

        var rect = container.getBoundingClientRect();
        var margin = { top: 8, right: 8, bottom: 20, left: 40 };
        var width = rect.width - margin.left - margin.right;
        var height = rect.height - margin.top - margin.bottom;

        if (width <= 0 || height <= 0) {
            width = 200;
            height = 60;
        }

        var svg = d3.select(container).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        var x = d3.scaleTime().range([0, width]);
        var y = d3.scaleLinear().range([height, 0]);

        // Grid
        svg.append("g")
            .attr("class", "grid")
            .attr("transform", "translate(0," + height + ")")
            .call(d3.axisBottom(x).ticks(4).tickSize(-height).tickFormat(""));

        // Area
        svg.append("path").attr("class", "area");

        // Line
        svg.append("path").attr("class", "line");

        // X axis
        svg.append("g")
            .attr("class", "axis x-axis")
            .attr("transform", "translate(0," + height + ")");

        // Y axis
        svg.append("g")
            .attr("class", "axis y-axis");

        return { svg: svg, x: x, y: y, width: width, height: height, color: color };
    }

    function updateWaveform(chart, data) {
        if (!chart || !data || data.length === 0) return;

        var parsed = data.map(function (d) {
            return { time: new Date(d.timestamp), value: d.value };
        });

        chart.x.domain(d3.extent(parsed, function (d) { return d.time; }));
        var yExtent = d3.extent(parsed, function (d) { return d.value; });
        var yPad = (yExtent[1] - yExtent[0]) * 0.1 || 1;
        chart.y.domain([yExtent[0] - yPad, yExtent[1] + yPad]);

        var line = d3.line()
            .x(function (d) { return chart.x(d.time); })
            .y(function (d) { return chart.y(d.value); })
            .curve(d3.curveBasis);

        var area = d3.area()
            .x(function (d) { return chart.x(d.time); })
            .y0(chart.height)
            .y1(function (d) { return chart.y(d.value); })
            .curve(d3.curveBasis);

        chart.svg.select(".line")
            .datum(parsed)
            .transition().duration(800)
            .attr("d", line);

        chart.svg.select(".area")
            .datum(parsed)
            .transition().duration(800)
            .attr("d", area);

        chart.svg.select(".x-axis")
            .transition().duration(400)
            .call(d3.axisBottom(chart.x).ticks(4).tickFormat(d3.timeFormat("%H:%M")));

        chart.svg.select(".y-axis")
            .transition().duration(400)
            .call(d3.axisLeft(chart.y).ticks(4));
    }

    // --- Initialize charts ---
    function initCharts() {
        charts.light = createWaveform("chart-light", "var(--color-light)");
        charts.water = createWaveform("chart-water", "var(--color-water)");
        charts.air = createWaveform("chart-air", "var(--text-secondary)");
        charts.root = createWaveform("chart-root", "var(--color-root)");
    }

    // --- Refresh chart data ---
    function refreshChart(chartKey, sensorIds) {
        if (!charts[chartKey]) return;

        // Try each sensor ID until one returns data
        var tryNext = function (ids, idx) {
            if (idx >= ids.length) return;
            apiReadings(ids[idx]).then(function (data) {
                if (data && data.length > 0) {
                    updateWaveform(charts[chartKey], data);
                } else {
                    tryNext(ids, idx + 1);
                }
            });
        };
        tryNext(sensorIds, 0);
    }

    function refreshAllCharts() {
        refreshChart("light", SENSOR_MAP.light);
        refreshChart("air", SENSOR_MAP.air_temp);
        refreshChart("root", SENSOR_MAP.root_ph);

        // Water panel: show irrigation events as pulse timeline
        fetchJSON("/api/events?limit=20").then(function (events) {
            var irrigationEvents = events.filter(function (e) {
                return e.event_type === "irrigation";
            });
            var el = document.getElementById("water-last");
            if (el && irrigationEvents.length > 0) {
                el.textContent = "Last: " + irrigationEvents[0].timestamp.slice(11, 19);
            }
        });
    }

    // --- Update live values from latest readings ---
    function updateValues(readings) {
        // readings is an array of {sensor_id, value, unit}
        readings.forEach(function (r) {
            if (r.sensor_id === "bme280_temperature" || r.sensor_id.includes("temperature")) {
                setText("air-temp", r.value.toFixed(1));
            }
            if (r.sensor_id === "bme280_humidity" || r.sensor_id.includes("humidity")) {
                setText("air-humidity", "Humidity: " + r.value.toFixed(0) + "%");
            }
            if (r.sensor_id === "bme280_pressure" || r.sensor_id.includes("pressure")) {
                setText("air-pressure", "Pressure: " + r.value.toFixed(0) + " hPa");
            }
            if (r.sensor_id.includes("ph")) {
                setText("root-ph", r.value.toFixed(2));
            }
            if (r.sensor_id.includes("ec")) {
                setText("root-ec", "EC: " + r.value.toFixed(0) + " µS/cm");
            }
        });
    }

    function setText(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    // --- System status ---
    function refreshStatus() {
        apiStatus().then(function (data) {
            setText("sensor-count", (data.sensors ? data.sensors.length : 0) + " sensors");
            setText("db-readings", (data.db ? data.db.sensor_readings || 0 : 0) + " readings");
        }).catch(function () {});
    }

    // --- Latest image ---
    function refreshImage() {
        apiLatestImage().then(function (data) {
            if (data && data.filename) {
                var container = document.getElementById("camera-feed");
                if (container) {
                    // Clear previous content safely
                    while (container.firstChild) {
                        container.removeChild(container.firstChild);
                    }
                    var img = document.createElement("img");
                    img.src = "/static/captures/" + encodeURIComponent(data.filename);
                    img.alt = "Latest capture";
                    container.appendChild(img);
                }
                setText("plant-capture-time", data.timestamp.slice(0, 19));
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
        refreshAllCharts();
        refreshStatus();
        refreshImage();
        connectWS();
        startPolling();
    });
})();
