/**
 * Humidity Breathing Ring — AIR subsystem humidity visualization (v2)
 *
 * A concentric ring outside the temperature ring that "breathes":
 * radius = humidity %, opacity pulses slowly in and out.
 * Color: bright teal-cyan (0,200,220), complementing warm temperature ring.
 *
 * Hover: glowing dot + radial guide line; value shown in center disc
 * via the ring's setCenterOverride API.
 *
 * Design doc: "humidity as breathing waveforms"
 */

window.GrowLab = window.GrowLab || {};
window.GrowLab.ArtMode = window.GrowLab.ArtMode || {};

(function () {
    "use strict";

    var Art = window.GrowLab.ArtMode;

    function timeToAngle(date) {
        var hours = date.getHours() + date.getMinutes() / 60 + date.getSeconds() / 3600;
        return (hours / 24) * Math.PI * 2 - Math.PI / 2;
    }

    function normAngle(a) {
        while (a > Math.PI) a -= Math.PI * 2;
        while (a < -Math.PI) a += Math.PI * 2;
        return a;
    }

    function smoothArray(arr, windowSize) {
        var half = Math.floor(windowSize / 2);
        var result = [];
        for (var i = 0; i < arr.length; i++) {
            var sum = 0, count = 0;
            for (var j = i - half; j <= i + half; j++) {
                var idx = ((j % arr.length) + arr.length) % arr.length;
                sum += arr[idx];
                count++;
            }
            result.push(sum / count);
        }
        return result;
    }

    // Bright teal-cyan — saturated, distinct from temperature palette
    var HUM_COLOR = { r: 0, g: 200, b: 220 };

    function humColorRGBA(alpha) {
        return "rgba(" + HUM_COLOR.r + "," + HUM_COLOR.g + "," + HUM_COLOR.b + "," + alpha + ")";
    }

    function createHumidityRing(ctx, getCx, getCy, getMaxRadius, getHoverAngle, getMouseDist) {
        var data = null;
        var smoothedRadii = [];
        var animTime = 0;
        var hoverHum = null;

        var radiusScale = d3.scaleLinear().domain([0, 100]);

        function update(readings) {
            if (!readings || readings.length === 0) {
                data = null;
                smoothedRadii = [];
                return;
            }

            var parsed = readings.map(function (d) {
                var date = new Date(d.timestamp);
                return {
                    angle: timeToAngle(date),
                    hum: d.value,
                    time: date,
                };
            });

            parsed.sort(function (a, b) { return a.angle - b.angle; });
            data = parsed;
            recalcRadii();
        }

        function recalcRadii() {
            if (!data) return;
            var maxR = getMaxRadius();
            radiusScale.range([maxR * 0.82, maxR * 1.12]);
            var rawRadii = data.map(function (d) { return radiusScale(d.hum); });
            smoothedRadii = smoothArray(rawRadii, 7);
        }

        function setLiveValue(hum) {
            // not used yet but available for WebSocket updates
        }

        function render(dt) {
            if (!data || data.length < 2) return;

            animTime += dt;
            recalcRadii();

            var cx = getCx();
            var cy = getCy();
            var maxR = getMaxRadius();
            var ringMin = maxR * 0.82;

            // Breathing — strong, visible
            var breathe = 0.20 + 0.12 * Math.sin(animTime / 2500);
            var glowBreathe = 0.12 + 0.08 * Math.sin(animTime / 2500 + 0.5);

            // Check hover
            hoverHum = null;
            var hoverAngle = getHoverAngle ? getHoverAngle() : null;
            var mouseDist = getMouseDist ? getMouseDist() : Infinity;
            var hoverIdx = -1;

            if (hoverAngle !== null && mouseDist > maxR * 0.78 && mouseDist < maxR * 1.2) {
                var mNorm = normAngle(hoverAngle);
                var bestDist = Infinity;
                for (var i = 0; i < data.length; i++) {
                    var dNorm = normAngle(data[i].angle);
                    var diff = Math.abs(dNorm - mNorm);
                    if (diff > Math.PI) diff = Math.PI * 2 - diff;
                    if (diff < bestDist) { bestDist = diff; hoverIdx = i; }
                }
                if (bestDist < 0.05 && hoverIdx >= 0) {
                    hoverHum = data[hoverIdx];
                }
            }

            ctx.save();
            ctx.translate(cx, cy);

            // Filled area — radial gradient per wedge for depth
            for (var i = 0; i < data.length - 1; i++) {
                var d0 = data[i];
                var d1 = data[i + 1];
                if (Math.abs(d1.angle - d0.angle) > Math.PI / 6) continue;

                var r0 = smoothedRadii[i];
                var r1 = smoothedRadii[i + 1];

                ctx.beginPath();
                ctx.arc(0, 0, ringMin, d0.angle, d1.angle);
                ctx.lineTo(Math.cos(d1.angle) * r1, Math.sin(d1.angle) * r1);
                var midAngle = (d0.angle + d1.angle) / 2;
                var midR = (r0 + r1) / 2;
                ctx.quadraticCurveTo(
                    Math.cos(midAngle) * midR * 1.01,
                    Math.sin(midAngle) * midR * 1.01,
                    Math.cos(d0.angle) * r0,
                    Math.sin(d0.angle) * r0
                );
                ctx.closePath();

                var grad = ctx.createRadialGradient(0, 0, ringMin, 0, 0, midR);
                grad.addColorStop(0, humColorRGBA(breathe * 0.4));
                grad.addColorStop(1, humColorRGBA(breathe * 1.2));
                ctx.fillStyle = grad;
                ctx.fill();
            }

            // Outer edge — glow
            var points = [];
            for (var i = 0; i < data.length; i++) {
                points.push({
                    x: Math.cos(data[i].angle) * smoothedRadii[i],
                    y: Math.sin(data[i].angle) * smoothedRadii[i],
                });
            }

            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length; i++) {
                var prev = points[i - 1];
                var curr = points[i];
                ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
            }
            ctx.strokeStyle = humColorRGBA(glowBreathe);
            ctx.lineWidth = 6;
            ctx.stroke();

            // Main line — organic, not mechanical
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            for (var i = 1; i < points.length; i++) {
                var prev = points[i - 1];
                var curr = points[i];
                ctx.quadraticCurveTo(prev.x, prev.y, (prev.x + curr.x) / 2, (prev.y + curr.y) / 2);
            }
            ctx.strokeStyle = humColorRGBA(0.3 + breathe * 0.5);
            ctx.lineWidth = 1;
            ctx.stroke();

            // Hover highlight — dot + radial guide (info goes to center disc)
            if (hoverHum && hoverIdx >= 0) {
                var hr = smoothedRadii[hoverIdx];
                var hx = Math.cos(hoverHum.angle) * hr;
                var hy = Math.sin(hoverHum.angle) * hr;

                ctx.beginPath();
                ctx.arc(hx, hy, 14, 0, Math.PI * 2);
                ctx.fillStyle = humColorRGBA(0.2);
                ctx.fill();

                ctx.beginPath();
                ctx.arc(hx, hy, 5, 0, Math.PI * 2);
                ctx.fillStyle = humColorRGBA(0.8);
                ctx.fill();

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.lineTo(hx, hy);
                ctx.strokeStyle = humColorRGBA(0.12);
                ctx.lineWidth = 0.5;
                ctx.setLineDash([3, 5]);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            ctx.restore();
        }

        return {
            update: update,
            setLiveValue: setLiveValue,
            render: render,
            getHoverHum: function () { return hoverHum; },
        };
    }

    window.GrowLab.ArtMode.createHumidityRing = createHumidityRing;

})();
