/**
 * Pressure Atmosphere — ambient barometric pressure visualization (v2)
 *
 * Barometric pressure rendered as a colored radial gradient that shifts
 * the entire canvas atmosphere. Low pressure = cool blue-purple tint.
 * High pressure = warmer, expanded field.
 *
 * Drifting isobar rings with wobble animation.
 * Pressure value shown in DOM readout element.
 *
 * Phoenix range: 990–1030 hPa.
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    function createPressureField(ctx, getCx, getCy, getMaxRadius) {
        var currentPressure = null;
        var animTime = 0;

        var PRESSURE_MIN = 990;
        var PRESSURE_MAX = 1030;

        function normalizedPressure() {
            if (currentPressure === null) return 0.5;
            return Math.max(0, Math.min(1,
                (currentPressure - PRESSURE_MIN) / (PRESSURE_MAX - PRESSURE_MIN)
            ));
        }

        function setLiveValue(pressureHpa) {
            currentPressure = pressureHpa;
        }

        function render(dt) {
            if (currentPressure === null) return;

            animTime += dt;
            var cx = getCx();
            var cy = getCy();
            var maxR = getMaxRadius();
            var p = normalizedPressure();
            var W = ctx.canvas.width / (window.devicePixelRatio || 1);
            var H = ctx.canvas.height / (window.devicePixelRatio || 1);

            ctx.save();

            // Colored radial gradient — blue-purple (low) → warm (high)
            var fieldRadius = maxR * (1.2 + p * 0.5);
            var gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, fieldRadius);

            var lr = Math.round(20 + p * 30);
            var lg = Math.round(25 + p * 20);
            var lb = Math.round(50 - p * 20);
            var baseAlpha = 0.03 + p * 0.04;

            gradient.addColorStop(0, "rgba(" + lr + "," + lg + "," + lb + "," + (baseAlpha * 2) + ")");
            gradient.addColorStop(0.4, "rgba(" + lr + "," + lg + "," + lb + "," + baseAlpha + ")");
            gradient.addColorStop(1, "rgba(" + lr + "," + lg + "," + lb + ",0)");
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, W, H);

            // Drifting isobar rings
            ctx.translate(cx, cy);
            for (var i = 0; i < 4; i++) {
                var phase = (i / 4 + animTime / 20000) % 1;
                var r = maxR * 0.2 + phase * maxR * 1.1;
                var al = 0.04 * (1 - phase);
                var wobbleX = Math.sin(animTime / 8000 + i * 2.1) * 5;
                var wobbleY = Math.cos(animTime / 9000 + i * 1.7) * 5;

                ctx.beginPath();
                ctx.arc(wobbleX, wobbleY, r, 0, Math.PI * 2);
                ctx.strokeStyle = "rgba(" + lr + "," + lg + "," + lb + "," + al + ")";
                ctx.lineWidth = 0.8;
                ctx.stroke();
            }

            ctx.restore();

            // Update pressure readout in DOM if element exists
            var readoutEl = document.getElementById("pressure-readout");
            if (readoutEl) {
                readoutEl.textContent = currentPressure.toFixed(0) + " hPa";
            }
        }

        return {
            setLiveValue: setLiveValue,
            render: render,
        };
    }

    window.GrowLab.ArtMode.createPressureField = createPressureField;

})();
