/**
 * Dream Controller — Main orchestrator for Dream Mode
 *
 * Initializes Three.js scene, particle system, flow field, and data
 * pipeline. Wires sensor updates to visual parameters. Manages
 * keyboard controls and HUD updates.
 *
 * Keyboard:
 *   Space  — pause / resume
 *   D      — toggle debug HUD
 *   F      — toggle fullscreen
 */

import {
    createDreamScene,
    createOrbitController,
    createAnimationLoop,
    tempToVec3,
} from "./dream-core.js";
import { createParticleSystem } from "./particle-system.js";
import { createFlowField } from "./flow-field.js";
import { createDreamData } from "./dream-data.js";

// -------------------------------------------------------
// Init
// -------------------------------------------------------

(function init() {
    var canvas = document.getElementById("dream-canvas");
    if (!canvas) return;

    // DOM refs
    var statusEl = document.getElementById("dream-status");
    var debugEl = document.getElementById("dream-debug");
    var tempEl = document.getElementById("dream-temp");
    var humidityEl = document.getElementById("dream-humidity");
    var pressureEl = document.getElementById("dream-pressure");
    var particlesEl = document.getElementById("dream-particles");
    var showDebug = false;

    // Create scene
    var dream = createDreamScene(canvas);
    var orbit = createOrbitController(dream.camera);
    var loop = createAnimationLoop(dream.composer);

    // Create particle system
    var particles = createParticleSystem(dream.scene, {
        count: 50000,
        spreadRadius: 200,
    });

    // Create flow field
    var flowField = createFlowField();

    // Update particle count display
    if (particlesEl) {
        particlesEl.textContent = (particles.getCount() / 1000).toFixed(0) + "K";
    }

    // Status
    function setStatus(text) {
        if (statusEl) statusEl.textContent = text;
    }
    setStatus("CONNECTING");

    // -------------------------------------------------------
    // Data pipeline
    // -------------------------------------------------------

    var data = createDreamData({
        onUpdate: function (state) {
            // Update flow field from sensor values
            flowField.applyTemperature(state.tempF);
            flowField.applyHumidity(state.humidity);
            flowField.applyPressure(state.pressure);

            // Update particle color from temperature
            particles.params.baseColor = tempToVec3(state.tempF);

            // Update particle density from humidity
            var h = Math.max(0, Math.min(1, (state.humidity - 20) / 70));
            particles.params.spawnRate = 0.5 + h * 1.0;

            // Update HUD
            if (tempEl) tempEl.textContent = state.tempF.toFixed(1) + "\u00B0F";
            if (humidityEl) humidityEl.textContent = state.humidity.toFixed(0) + "%";
            if (pressureEl) pressureEl.textContent = state.pressure.toFixed(0) + " hPa";
        },

        onIrrigation: function () {
            // Burst of cyan particles
            particles.triggerBurst(null, 3000);
        },

        onStatusChange: function (status) {
            setStatus(status);
        },
    });

    data.start();

    // -------------------------------------------------------
    // Animation loop
    // -------------------------------------------------------

    loop.register(function (dt, now) {
        // Update flow field time evolution
        flowField.update(dt);

        // Update particles with flow field
        particles.update(dt, flowField);

        // Orbit camera
        orbit.update(dt);

        // Debug HUD
        if (showDebug && debugEl) {
            var ff = flowField;
            debugEl.textContent =
                "FPS: " + loop.getFps() +
                "  |  Particles: " + particles.getCount() +
                "  |  Scale: " + ff.getScale().toFixed(4) +
                "  |  Amp: " + ff.getAmplitude().toFixed(2) +
                "  |  Speed: " + (ff.getSpeed() * 1000).toFixed(2);
        }
    });

    setStatus("LIVE");

    // -------------------------------------------------------
    // Keyboard controls
    // -------------------------------------------------------

    document.addEventListener("keydown", function (e) {
        // Ignore if typing in an input
        if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;

        switch (e.key) {
            case " ":
                e.preventDefault();
                if (loop.isRunning()) {
                    loop.pause();
                    setStatus("PAUSED");
                } else {
                    loop.resume();
                    setStatus("LIVE");
                }
                break;

            case "d":
            case "D":
                showDebug = !showDebug;
                if (debugEl) {
                    debugEl.style.display = showDebug ? "block" : "none";
                    if (!showDebug) debugEl.textContent = "";
                }
                break;

            case "f":
            case "F":
                if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen().catch(function () {});
                } else {
                    document.exitFullscreen().catch(function () {});
                }
                break;
        }
    });
})();
