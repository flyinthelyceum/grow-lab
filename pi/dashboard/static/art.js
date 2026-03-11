/**
 * Living Light — Art Mode
 *
 * Generative visualization driven by live sensor data.
 * Renders invisible biological processes as poetic visual forms:
 *
 *   - Light cycles → solar arc sweeping across the canvas
 *   - Humidity → breathing waveform amplitude
 *   - Temperature → color temperature shift (cool blue ↔ warm amber)
 *   - pH → tidal wave frequency
 *   - Irrigation events → pulse rings expanding from center
 *
 * Calm, slow, meditative. Frame rate locked at 30fps.
 * Update cadence: sensor data fetched every 5 seconds.
 */

(function () {
    "use strict";

    // --- Sensor State ---
    var state = {
        temperature: 22,
        humidity: 50,
        pressure: 1013,
        ph: 7.0,
        lightPwm: 0,
        lastUpdate: 0,
    };

    var particles = [];
    var waveOffset = 0;
    var pulseRings = [];

    // --- p5.js sketch ---
    new p5(function (p) {

        p.setup = function () {
            p.createCanvas(p.windowWidth, p.windowHeight);
            p.frameRate(30);
            p.colorMode(p.HSB, 360, 100, 100, 100);
            p.noStroke();

            // Initialize particles
            for (var i = 0; i < 80; i++) {
                particles.push({
                    x: p.random(p.width),
                    y: p.random(p.height),
                    vx: p.random(-0.3, 0.3),
                    vy: p.random(-0.2, 0.1),
                    size: p.random(1, 3),
                    alpha: p.random(5, 20),
                });
            }

            // Start data polling
            fetchSensorData();
            setInterval(fetchSensorData, 5000);
        };

        p.draw = function () {
            // Background: very slow fade (persistence of vision)
            p.background(0, 0, 0, 3);

            drawSolarArc(p);
            drawBreathingWave(p);
            drawParticles(p);
            drawPulseRings(p);
            drawDataOverlay(p);

            waveOffset += 0.005;
        };

        p.windowResized = function () {
            p.resizeCanvas(p.windowWidth, p.windowHeight);
        };

        // --- Solar Arc (Light) ---
        function drawSolarArc(p) {
            var intensity = state.lightPwm / 255;
            if (intensity < 0.01) return;

            var cx = p.width / 2;
            var cy = p.height * 0.7;
            var radius = p.width * 0.4;

            // Arc position based on time
            var t = (Date.now() / 60000) % 1; // Cycle every minute
            var angle = p.PI + t * p.PI;
            var sx = cx + p.cos(angle) * radius;
            var sy = cy + p.sin(angle) * radius;

            // Warm amber glow
            var hue = 40;
            var brightness = intensity * 60;

            for (var r = 60; r > 0; r -= 2) {
                p.fill(hue, 80, brightness, 1);
                p.ellipse(sx, sy, r, r);
            }
        }

        // --- Breathing Wave (Humidity) ---
        function drawBreathingWave(p) {
            var amplitude = p.map(state.humidity, 20, 90, 10, 80);
            var freq = p.map(state.ph, 4, 9, 0.02, 0.005);
            var tempHue = p.map(state.temperature, 15, 35, 200, 40);

            p.noFill();
            p.strokeWeight(1);

            for (var wave = 0; wave < 3; wave++) {
                p.stroke(tempHue, 40, 60, 8 - wave * 2);
                p.beginShape();
                for (var x = 0; x < p.width; x += 3) {
                    var y = p.height / 2 +
                        p.sin(x * freq + waveOffset + wave * 0.5) * amplitude +
                        p.sin(x * freq * 2.3 + waveOffset * 1.7) * amplitude * 0.3;
                    p.vertex(x, y);
                }
                p.endShape();
            }

            p.noStroke();
        }

        // --- Particles (Ambient) ---
        function drawParticles(p) {
            var tempHue = p.map(state.temperature, 15, 35, 200, 40);

            for (var i = 0; i < particles.length; i++) {
                var pt = particles[i];
                pt.x += pt.vx;
                pt.y += pt.vy;

                // Wrap around
                if (pt.x < 0) pt.x = p.width;
                if (pt.x > p.width) pt.x = 0;
                if (pt.y < 0) pt.y = p.height;
                if (pt.y > p.height) pt.y = 0;

                p.fill(tempHue, 30, 80, pt.alpha);
                p.ellipse(pt.x, pt.y, pt.size, pt.size);
            }
        }

        // --- Pulse Rings (Irrigation Events) ---
        function drawPulseRings(p) {
            for (var i = pulseRings.length - 1; i >= 0; i--) {
                var ring = pulseRings[i];
                ring.radius += 1.5;
                ring.alpha -= 0.5;

                if (ring.alpha <= 0) {
                    pulseRings.splice(i, 1);
                    continue;
                }

                p.noFill();
                p.stroke(190, 70, 70, ring.alpha); // Cyan
                p.strokeWeight(1);
                p.ellipse(p.width / 2, p.height / 2, ring.radius * 2, ring.radius * 2);
            }
            p.noStroke();
        }

        // --- Data Overlay ---
        function drawDataOverlay(p) {
            p.fill(0, 0, 100, 15);
            p.textFont("monospace");
            p.textSize(10);
            p.textAlign(p.RIGHT);

            var x = p.width - 20;
            var y = 30;

            p.text(state.temperature.toFixed(1) + "°C", x, y);
            p.text(state.humidity.toFixed(0) + "% RH", x, y + 14);
            p.text(state.pressure.toFixed(0) + " hPa", x, y + 28);
            p.text("pH " + state.ph.toFixed(2), x, y + 42);
        }
    });

    // --- Fetch sensor data ---
    function fetchSensorData() {
        fetch("/api/readings/latest")
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.bme280_temperature) state.temperature = data.bme280_temperature.value;
                if (data.bme280_humidity) state.humidity = data.bme280_humidity.value;
                if (data.bme280_pressure) state.pressure = data.bme280_pressure.value;
                if (data.ezo_ph) state.ph = data.ezo_ph.value;
                state.lastUpdate = Date.now();
            })
            .catch(function () {});

        // Check for recent irrigation events → trigger pulse ring
        fetch("/api/events?limit=1")
            .then(function (r) { return r.json(); })
            .then(function (events) {
                if (events.length > 0 && events[0].event_type === "irrigation") {
                    var eventTime = new Date(events[0].timestamp).getTime();
                    if (Date.now() - eventTime < 10000) {
                        pulseRings.push({ radius: 10, alpha: 40 });
                    }
                }
            })
            .catch(function () {});
    }
})();
