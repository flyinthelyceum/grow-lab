/**
 * Dream Data — Sensor data pipeline for Dream Mode
 *
 * Connects to the existing GROWLAB WebSocket and REST API.
 * Smooths values with exponential moving average to prevent
 * visual jitter. Maps raw sensor values to particle system
 * and flow field parameters.
 */

function cToF(c) {
    return c * 9 / 5 + 32;
}

function createDreamData(callbacks) {
    var cb = callbacks || {};

    // Current smoothed values
    var state = {
        tempF: 72,
        humidity: 50,
        pressure: 1013,
        lastIrrigation: null,
        connected: false,
    };

    // EMA smoothing factor (0 = no smoothing, 1 = no memory)
    var ALPHA = 0.15;

    function ema(current, target) {
        return current + ALPHA * (target - current);
    }

    // -------------------------------------------------------
    // WebSocket connection
    // -------------------------------------------------------

    var ws = null;
    var wsIntervalId = null;
    var reconnectTimeout = null;

    function connectWS() {
        var protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        var url = protocol + "//" + window.location.host + "/ws/updates";

        try {
            ws = new WebSocket(url);
        } catch (e) {
            scheduleReconnect();
            return;
        }

        ws.onopen = function () {
            state.connected = true;
            if (cb.onStatusChange) cb.onStatusChange("LIVE");

            // Poll for updates every 3 seconds
            if (wsIntervalId !== null) clearInterval(wsIntervalId);
            wsIntervalId = setInterval(function () {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send("update");
                }
            }, 3000);
        };

        ws.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                processUpdate(data);
            } catch (e) {
                // ignore parse errors
            }
        };

        ws.onclose = function () {
            state.connected = false;
            if (cb.onStatusChange) cb.onStatusChange("RECONNECTING");
            if (wsIntervalId !== null) {
                clearInterval(wsIntervalId);
                wsIntervalId = null;
            }
            scheduleReconnect();
        };

        ws.onerror = function () {
            if (ws) ws.close();
        };
    }

    function scheduleReconnect() {
        if (reconnectTimeout !== null) return;
        reconnectTimeout = setTimeout(function () {
            reconnectTimeout = null;
            connectWS();
        }, 5000);
    }

    function processUpdate(data) {
        if (!data.readings) return;

        for (var i = 0; i < data.readings.length; i++) {
            var r = data.readings[i];
            var id = r.sensor_id || "";
            var val = r.value;

            if (id.indexOf("temperature") !== -1 && id.indexOf("bme280") !== -1) {
                var tempF = r.unit === "celsius" ? cToF(val) : val;
                state.tempF = ema(state.tempF, tempF);
            } else if (id.indexOf("humidity") !== -1) {
                state.humidity = ema(state.humidity, val);
            } else if (id.indexOf("pressure") !== -1) {
                state.pressure = ema(state.pressure, val);
            }
        }

        // Check for irrigation events in alerts
        if (data.alerts) {
            for (var j = 0; j < data.alerts.length; j++) {
                if (data.alerts[j].event_type === "irrigation") {
                    state.lastIrrigation = new Date();
                    if (cb.onIrrigation) cb.onIrrigation();
                }
            }
        }

        if (cb.onUpdate) cb.onUpdate(state);
    }

    // -------------------------------------------------------
    // REST fetch for initial state
    // -------------------------------------------------------

    function fetchInitialState() {
        // Fetch latest readings to seed smoothed state
        var sensors = ["bme280_temperature", "bme280_humidity", "bme280_pressure"];
        sensors.forEach(function (sensorId) {
            fetch("/api/readings/" + sensorId + "/downsampled?window=1h")
                .then(function (res) { return res.ok ? res.json() : null; })
                .then(function (data) {
                    if (!data || !data.length) return;
                    var latest = data[data.length - 1];
                    if (sensorId.indexOf("temperature") !== -1) {
                        state.tempF = latest.unit === "celsius" ? cToF(latest.value) : latest.value;
                    } else if (sensorId.indexOf("humidity") !== -1) {
                        state.humidity = latest.value;
                    } else if (sensorId.indexOf("pressure") !== -1) {
                        state.pressure = latest.value;
                    }
                })
                .catch(function () { /* ignore fetch errors */ });
        });
    }

    // -------------------------------------------------------
    // Lifecycle
    // -------------------------------------------------------

    function start() {
        fetchInitialState();
        connectWS();
    }

    function stop() {
        if (ws) {
            ws.onclose = null; // prevent reconnect
            ws.close();
        }
        if (wsIntervalId !== null) {
            clearInterval(wsIntervalId);
            wsIntervalId = null;
        }
        if (reconnectTimeout !== null) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }
    }

    return {
        start: start,
        stop: stop,
        getState: function () { return state; },
    };
}

export { createDreamData };
