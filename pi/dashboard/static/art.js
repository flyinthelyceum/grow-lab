/**
 * GROWLAB — Art Mode Controller
 *
 * Full-screen generative visualization driven by live sensor data.
 * Renders all environmental layers:
 *   - Pressure atmosphere (background)
 *   - Radial thermal ring (temperature)
 *   - Humidity breathing ring (outer)
 *   - Water pulse markers (irrigation events)
 *   - Ambient particles (living field)
 *
 * Data pipeline:
 *   1. Fetch 24h downsampled history on load (temp + humidity)
 *   2. Fetch irrigation events
 *   3. WebSocket for live value updates
 *   4. Re-fetch history every 5 minutes
 *
 * Center disc shows context-sensitive info:
 *   Priority: water event > humidity > temperature (default)
 */

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    // --- State ---
    var loop = null;
    var ring = null;
    var humRing = null;
    var waterPulses = null;
    var pressureField = null;
    var particles = null;
    var ws = null;
    var canvas = null;

    // Shared canvas state (getter functions for overlay layers)
    var sharedCtx = null;
    var sharedCx = 0, sharedCy = 0, sharedMaxR = 0;

    function getCx() { return sharedCx; }
    function getCy() { return sharedCy; }
    function getMaxR() { return sharedMaxR; }

    // --- Temperature conversion ---
    function cToF(c) { return c * 9 / 5 + 32; }

    function angleToTimeStr(angle) {
        var hours = ((angle + Math.PI / 2) / (Math.PI * 2)) * 24;
        if (hours < 0) hours += 24;
        if (hours >= 24) hours -= 24;
        var h = Math.floor(hours);
        var m = Math.floor((hours - h) * 60);
        var ampm = h >= 12 ? "PM" : "AM";
        var h12 = h % 12 || 12;
        return h12 + ":" + (m < 10 ? "0" : "") + m + " " + ampm;
    }

    function setReadout(id, text) {
        var el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    // --- API ---
    function fetchJSON(url) {
        return fetch(url).then(function (r) { return r.json(); });
    }

    function fetchTempHistory() {
        return fetchJSON("/api/readings/bme280_temperature/downsampled?window=24h");
    }

    function fetchHumHistory() {
        return fetchJSON("/api/readings/bme280_humidity/downsampled?window=24h");
    }

    function fetchIrrigationEvents() {
        return fetchJSON("/api/events?limit=50").then(function (events) {
            return events.filter(function (e) {
                return e.event_type === "irrigation";
            });
        });
    }

    // --- Load data into layers ---
    function loadAllData() {
        fetchTempHistory()
            .then(function (readings) {
                if (!readings || readings.length === 0) return;
                var converted = readings.map(function (d) {
                    return {
                        timestamp: d.timestamp,
                        value: (d.unit === "°F") ? d.value : cToF(d.value),
                        unit: "°F",
                    };
                });
                ring.update(converted);
                setReadout("art-live-temp", converted[converted.length - 1].value.toFixed(1) + " F");
            })
            .catch(function (err) {
                console.error("Art: failed to fetch temp history", err);
            });

        fetchHumHistory()
            .then(function (readings) {
                if (!readings || readings.length === 0) return;
                humRing.update(readings);
                setReadout("art-live-humidity", readings[readings.length - 1].value.toFixed(0) + " %");
            })
            .catch(function (err) {
                console.error("Art: failed to fetch humidity history", err);
            });

        fetchIrrigationEvents()
            .then(function (events) {
                waterPulses.update(events);
                if (events.length > 0) {
                    setReadout("art-live-water", new Date(events[0].timestamp).toLocaleTimeString("en-US", {
                        hour: "numeric",
                        minute: "2-digit"
                    }));
                }
            })
            .catch(function (err) {
                console.error("Art: failed to fetch irrigation events", err);
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
                            var tempF = cToF(r.value);
                            ring.setLiveValue(tempF);
                            setReadout("art-live-temp", tempF.toFixed(1) + " F");
                        }
                        if (r.sensor_id === "bme280_humidity") {
                            setReadout("art-live-humidity", r.value.toFixed(0) + " %");
                        }
                        if (r.sensor_id === "bme280_pressure") {
                            pressureField.setLiveValue(r.value);
                            setReadout("pressure-readout", "PRESSURE " + r.value.toFixed(0) + " HPA");
                        }
                    });
                }
                // Trigger water pulse on live irrigation event
                if (data.event && data.event.event_type === "irrigation") {
                    waterPulses.triggerPulse();
                    setReadout("art-live-water", "NOW");
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
        if (ring) ring.resize();
        var w = window.innerWidth;
        var h = window.innerHeight;
        sharedCx = w / 2;
        sharedCy = h / 2;
        sharedMaxR = Math.min(sharedCx, sharedCy) * 0.72;
    }

    // --- Init ---
    function init() {
        canvas = document.getElementById("art-canvas");
        if (!canvas) return;

        // Create radial ring (owns the canvas)
        ring = Art.createRadialRing(canvas);

        // Set up shared canvas context for overlay layers
        var setup = Art.setupCanvas(canvas);
        sharedCtx = setup.ctx;
        sharedCx = setup.width / 2;
        sharedCy = setup.height / 2;
        sharedMaxR = Math.min(sharedCx, sharedCy) * 0.72;

        // Re-init ring after shared setup
        ring.resize();

        // Create overlay layers with hover accessor functions
        humRing = Art.createHumidityRing(sharedCtx, getCx, getCy, getMaxR,
            ring.getHoverAngle, ring.getMouseDist);
        waterPulses = Art.createWaterPulses(sharedCtx, getCx, getCy, getMaxR,
            ring.getHoverAngle, ring.getMouseDist);
        pressureField = Art.createPressureField(sharedCtx, getCx, getCy, getMaxR);
        particles = Art.createAmbientParticles(sharedCtx, getCx, getCy, getMaxR);

        // Start animation loop
        loop = new Art.AnimationLoop();
        loop.register(function (dt, now) {
            // Route hover info to center disc — priority: water > humidity > temp
            var waterHover = waterPulses.getHoverEvent();
            var humHover = humRing.getHoverHum();

            if (waterHover) {
                ring.setCenterOverride({
                    value: angleToTimeStr(waterHover.angle),
                    unit: waterHover.ageMin + "m ago",
                    label: "IRRIGATION",
                    color: "rgba(30,210,255,0.9)",
                    labelColor: "rgba(30,210,255,0.3)"
                });
            } else if (humHover) {
                ring.setCenterOverride({
                    value: humHover.hum.toFixed(0),
                    unit: "%  RH",
                    label: humHover.time.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
                    color: "rgba(0,200,220,0.9)",
                    labelColor: "rgba(0,200,220,0.4)"
                });
            } else {
                ring.setCenterOverride(null);
            }

            // Render order: pressure → ring → humidity → water → particles
            pressureField.render(dt);
            ring.render(dt, now);
            humRing.render(dt);
            waterPulses.render(dt);
            particles.render(dt);
        });

        // Load initial data
        loadAllData();

        // Re-fetch history every 5 minutes
        setInterval(loadAllData, 300000);

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
